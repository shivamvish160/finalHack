# Phase 0 Research: JSON-Driven Agentic AI Incident Prevention & Resolution Platform

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24

This document resolves every technology/approach decision needed before Phase 1
design. All facts below about Gemini model availability, ADK API status, and
BigQuery syntax were verified against live Google Cloud documentation and the
`google/adk-python` source on 2026-09-24 (not recalled from training data),
per the user's explicit instruction to use the real current model family and
APIs.

## 1. Gemini model family (Vertex AI)

- **Decision**: Use **`gemini-2.5-flash`** as the default reasoning/generation
  model for all six agents, with **`gemini-2.5-pro`** as an override for the
  Root Cause Analysis agent (deepest multi-source reasoning task). The model
  ID per agent is an environment variable / Terraform variable, not
  hardcoded, so it can be bumped without code changes.
- **Rationale**: As of 2026-09-24, Vertex AI's generally-available Gemini
  models include the 3.x Flash family (3.8/3.7/3.6/3.5/3.1) *and* the 2.5
  family (2.5 Pro, 2.5 Flash, 2.5 Flash-Lite) — 2.5 is not legacy, it is still
  GA and remains the model used in essentially all current official ADK
  samples and docs (`model='gemini-2.5-flash'`). Picking a stable,
  widely-documented GA model reduces quota/preview-availability risk during a
  timed hackathon demo versus chasing the newest 3.8 Flash release. The
  original hackathon brief's literal text ("Gemini 3.6 Flash") also happens
  to name a real GA model, confirming the brief was not purely fictional —
  but 2.5 Flash is the safer default given it is the ADK ecosystem's
  reference model.
- **Alternatives considered**: `gemini-3.6-flash` / `gemini-3.8-flash` (newer,
  "built for long-horizon coding and autonomous agents" — genuinely
  attractive for the Root Cause/Remediation agents, but newer GA models carry
  higher regional/quota-rollout risk close to a demo date). Rejected as the
  *default* but allowed as a configurable upgrade — the plan keeps the model
  name in Terraform/env config specifically so this swap is a one-line change.

## 2. Embedding model for runbook semantic search

- **Decision**: **`text-embedding-005`** via a BigQuery **remote model**
  (`CREATE MODEL ... REMOTE WITH CONNECTION ... OPTIONS(ENDPOINT='text-embedding-005')`),
  invoked synchronously from the ingestion service with
  `ML.GENERATE_EMBEDDING` immediately after a runbook MERGE.
- **Rationale**: FR-003 requires embeddings to be searchable *immediately
  after ingestion completes*, and NFR-004 bounds this to ~5 minutes. BigQuery
  also offers **autonomous embedding generation** (a `GENERATED ALWAYS AS
  (AI.EMBED(...))` column with `STORED OPTIONS(asynchronous = TRUE)`), which
  is simpler to operate but is an unbounded-latency background job ("shortly
  after" per Google's own docs) — not a safe fit for a demo with a bounded
  freshness target. Google's docs also explicitly recommend dedicated text
  embedding models over Gemini models for embedding throughput/quota.
  Synchronous `ML.GENERATE_EMBEDDING` gives the ingestion service a
  deterministic point at which it can mark the file "succeeded" and know
  the runbook is searchable.
- **Alternatives considered**: Autonomous embedding generation (`AI.EMBED`
  generated column) — kept as a documented fallback/optional simplification
  in `data-model.md` for a non-demo-critical path (e.g. re-embedding on bulk
  historical import) since it requires zero application code. Vertex AI
  `text-embedding-005` called directly from Python (bypassing BigQuery) was
  rejected because it would require managing embeddings outside BigQuery,
  contradicting the "everything lives in BigQuery" mandate.

## 3. BigQuery Vector Search

- **Decision**: `CREATE VECTOR INDEX runbooks_embedding_idx ON
  core.runbooks(embedding) OPTIONS(distance_type='COSINE',
  index_type='IVF')`, queried through the `VECTOR_SEARCH()` table function
  (`top_k`, `distance_type`, `options` for `fraction_lists_to_search`), never
  keyword `LIKE`/`CONTAINS` matching, per FR-011.
- **Rationale**: This is the current, documented, GA syntax. `VECTOR_SEARCH`
  degrades gracefully to brute force if the index isn't ready yet (small
  runbook corpora also don't strictly need an index, but creating one now
  keeps the Runbook Retrieval Agent's query identical regardless of corpus
  size, and demonstrates the mandated "BigQuery Vector Search" capability
  explicitly rather than implicitly).
- **Alternatives considered**: An external vector DB (Pinecone/Weaviate) —
  rejected outright, contradicts the mandatory-service constraint and the
  "everything reasoning/retrieval happens via GCP services" requirement.

## 4. Predictive forecasting (BigQuery ML)

- **Decision**: **`ARIMA_PLUS`** time-series models (one per
  `service_id × metric_name` via `TIME_SERIES_ID_COL`), trained from
  `core.telemetry`, using `ML.FORECAST` for the outage prediction (time-to-
  failure window + confidence interval) and **`ML.DETECT_ANOMALIES`** on the
  *same* model for the anomaly-trend flag (AC-4.2), plus
  `ML.EXPLAIN_FORECAST` to source the plain-language rationale (NFR-010).
- **Rationale**: `ARIMA_PLUS` is explicitly designed to serve both
  forecasting and anomaly detection from one trained model family, which
  maps directly onto FR-012 (predicted failure/window/confidence/affected
  services) and FR-031 (anomaly trend, independent of a full prediction)
  without needing two different ML systems. Boosted-tree models were
  considered for a classification framing ("will this service fail in the
  next N minutes: yes/no") but time-series decomposition (trend/seasonality/
  holiday effects) is a better fit for "degrading trend" telemetry and
  avoids manual feature/window engineering.
- **Alternatives considered**: `BOOSTED_TREE_CLASSIFIER` over engineered
  rolling-window features — kept as a documented alternative in
  `data-model.md` for a future binary-classification refinement, but
  rejected as the primary model because it requires hand-built lag/window
  features that the spec's "no hardcoded mappings" principle (NFR-011)
  argues against; `ARIMA_PLUS` learns the trend/seasonality automatically
  per service.

## 5. ADK agent orchestration pattern

- **Decision**: Each of the 6 agents is an ADK **`LlmAgent`** (structured
  `output_schema`, domain tools, per-agent model). They are composed by a
  **custom event-driven orchestrator** (a plain Python/FastAPI Cloud Run
  service using `Runner` + a Firestore/BigQuery-backed session/state layer),
  *not* ADK's `SequentialAgent`/`ParallelAgent`/`LoopAgent` wrapper classes.
- **Rationale (important, current-as-of-2026-09-24 finding)**: Direct
  inspection of `google/adk-python` (source + tests) shows
  `SequentialAgent`, `ParallelAgent`, and `LoopAgent` are now **explicitly
  deprecated** in favor of a new graph-based `Workflow` API and are slated
  for removal in a future ADK version — code built on them today would need
  near-term migration. Independent of that, the spec's own architecture
  requirement ("agents communicate via Pub/Sub topics + Firestore/BigQuery
  state") is a fundamentally different shape than in-process
  `sub_agents=[...]` composition: our 6 agents are meant to react to
  asynchronous events (an alert burst, a Cloud Scheduler tick, a human
  approval decision) and persist state durably between stages — not run
  back-to-back inside one conversational turn. A thin custom orchestrator
  that calls `Runner.run_async(...)` per stage, keyed by `incident_id`,
  fits both constraints: it only depends on the stable `LlmAgent`/`Runner`
  API surface, and it lets each stage be triggered independently by its own
  Pub/Sub subscription (so Cloud Run can scale/schedule each stage
  differently — e.g., Agent 4's predictive stage runs on a schedule, not on
  the alert-arrival path).
- **Alternatives considered**: ADK `Workflow` graph API (too new /
  experimental relative to the hackathon timeline, and — per ADK's own
  migration notes — "a `Workflow` cannot yet be used as an `LlmAgent`
  sub-agent," limiting flexibility). `SequentialAgent`/`ParallelAgent`
  (rejected: deprecated, and don't naturally span independent Cloud Run
  services/Pub/Sub boundaries anyway).

## 6. Inter-agent communication & state

- **Decision**: Pub/Sub topics as the control-flow backbone
  (`alerts.raw`, `incidents.correlated`, `incidents.root_cause_identified`,
  `incidents.runbook_matched`, `remediation.proposed`,
  `remediation.approved`, `remediation.rejected`, `remediation.executed`,
  `risk.forecast.created`, `executive.metrics.updated` — see
  `contracts/pubsub-events.md`). BigQuery is the durable system-of-record
  for every agent output (append/merge). Firestore holds a live, denormalized
  `incidents/{incident_id}` document per incident for low-latency UI reads
  (Firestore client SDK realtime listeners) plus the `approvals/{action_id}`
  human-in-the-loop queue.
- **Rationale**: Matches the spec's explicit architecture requirement
  directly. Writing BigQuery first, then Firestore, then publishing the next
  event gives a consistent "durable-then-fast-path" ordering so the UI never
  shows a state that isn't already recorded for audit/executive aggregation.
- **Alternatives considered**: Firestore-only (rejected — BigQuery is the
  mandated system of record and is needed for executive/MTTR aggregation
  across history, which Firestore isn't built for). Direct
  agent-to-agent HTTP calls (rejected — doesn't survive a subscriber being
  temporarily down, violates NFR-012's "temporary unavailability of one
  capability must not block others").

## 7. Human-in-the-loop approval gate

- **Decision**: The Remediation Agent's proposal tool and its execution
  tool are two physically separate functions; only the execution tool calls
  the real Cloud Run Admin API, and it is only reachable from the
  `remediation.approved` Pub/Sub event, which is only ever published by the
  api-gateway's authenticated `/approvals/{action_id}/decision` endpoint —
  never by the LLM's own judgement.
- **Rationale**: Satisfies NFR-009 ("no remediation action ... MUST execute
  without an explicit prior human approval") structurally (the model has no
  code path to self-approve) rather than relying on a prompt instruction,
  which is the safer way to enforce a hard security/safety gate against an
  LLM-driven agent.

## 8. Sandbox remediation execution target

- **Decision**: A dedicated `demo-target-service` Cloud Run service
  (deployed by Terraform, isolated service account with only
  `roles/run.developer` scoped to that one service) is the real execution
  target. The Remediation Agent's execution tool calls the actual Cloud Run
  Admin API (e.g. update traffic split / restart revision / scale to zero as
  the "fix", reverse as the "rollback") against it and records the literal
  API response/exit status.
- **Rationale**: Directly satisfies Clarification #2 (execution must be
  real, not simulated) and FR-027 while keeping blast radius contained to a
  purpose-built low-privilege service, never production infrastructure.

## 9. Authentication & RBAC

- **Decision**: Firebase Authentication / Google Identity Platform for all
  end-user sign-in, with custom claims (`role`) set at user-provisioning
  time (a small seed script for the demo's 5 roles). `api-gateway` verifies
  the Firebase ID token on every request and authorizes based on the claim;
  GCP IAM is kept entirely separate and governs only service-to-service
  access to GCP resources (Cloud Run invoker, BigQuery data viewer, etc. per
  service account).
- **Rationale**: Matches Clarification #3 exactly; keeps human RBAC and
  machine IAM as two independent, non-conflatable systems, which is also
  easier to audit (FR-043).

## 10. Secrets, PII/secret redaction, audit logging

- **Decision**: All credentials/connection strings live in Secret Manager,
  mounted as Cloud Run secret env vars/volumes (never baked into images or
  returned by any API). A shared `agents/common/redaction.py` pattern-based
  redaction utility runs at two points: (a) ingestion time, before free-text
  fields (alert descriptions, runbook content, telemetry log snippets) are
  persisted, and (b) agent-output time, before any summary/script reaches
  the UI, dashboard, or Cloud Logging sink — defense in depth per
  FR-033/FR-044/NFR-006/NFR-007. Every security-relevant action additionally
  writes an explicit row to `core.audit_log` (distinct from operational
  logs) per FR-043.
- **Alternatives considered**: Cloud DLP API `deidentify` for stronger
  redaction guarantees — noted as an optional post-hackathon hardening step
  in `data-model.md`, not required to satisfy the mandatory-service list,
  and adds latency/complexity not justified for the demo scope.

## 11. Frontend

- **Decision**: Next.js (App Router) + React + TypeScript, Tailwind CSS,
  Firebase JS SDK for auth + realtime Firestore incident/approval reads, a
  typed REST client against `api-gateway` for BigQuery-backed read models
  (history, executive aggregates) that don't need realtime push.
- **Rationale**: Realtime-feeling "Live Incident Console" needs push
  updates (Firestore listeners are the natural fit); heavier
  analytical/aggregate views (Executive Dashboard, Predictive Health) are
  fine as polled REST reads against BigQuery-backed endpoints.

## 12. Testing strategy summary

- **Decision**: pytest (services/agents, mocked GCP clients) + emulator-based
  integration tests (Firestore + Pub/Sub emulators, a disposable BigQuery
  dataset) + JSON Schema contract tests for uploads and Pub/Sub payloads +
  ADK's own agent-eval harness for prompt/tool regression + a dedicated
  load-test script publishing ≥1000 msgs/min to validate NFR-001/002 + a
  security scan for secret/PII leakage (SC-009) + Terraform
  validate/plan (+ optional tfsec/checkov). Full detail in `quickstart.md`
  and the plan's Testing section.

All items above are resolved — no outstanding `NEEDS CLARIFICATION` markers
remain for Phase 1.
