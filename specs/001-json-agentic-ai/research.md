# Phase 0 Research: SRE Agentic AI Incident Prevention & Resolution Platform

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24 (re-derived for the
existing-warehouse premise rewrite of `spec.md`)

This document resolves every technology/approach decision needed before
Phase 1 design, **re-derived from scratch** against the rewritten
existing-warehouse `spec.md`. It supersedes the prior version of this file
in full — the prior version assumed a JSON-upload/ETL/GCS-landing
architecture that no longer exists in scope. Facts about Gemini model
availability, ADK API status, and BigQuery/BigQuery ML syntax were
re-verified on 2026-09-24 against live Google Cloud documentation (fetched
directly, not recalled from training data) and the `google/adk-python`
source, per the user's explicit instruction to ground the plan in current
reality rather than memory.

## 1. Gemini model family (Vertex AI)

- **Decision**: **`gemini-2.5-flash`** as the default reasoning/generation
  model for all six agents, with **`gemini-2.5-pro`** as an override for the
  Root Cause Analysis agent (the deepest multi-source reasoning task). The
  model ID per agent is an environment variable / Terraform variable, not
  hardcoded.
- **Rationale**: Vertex AI's GA Gemini lineup includes both the 2.5 family
  (Pro/Flash/Flash-Lite) and a newer 3.x Flash family — 2.5 is not
  legacy/deprecated, remains GA, and is the model used in essentially all
  current official ADK samples/docs (`model='gemini-2.5-flash'`). A stable,
  widely-documented GA model reduces quota/preview-availability risk for a
  timed hackathon demo. The model name stays externally configurable so a
  newer Flash release can be swapped in with a one-line config change.
- **Alternatives considered**: Newer 3.x Flash models — attractive
  ("long-horizon coding and autonomous agents") but carry higher
  regional/quota-rollout risk close to a demo date; kept as a configurable
  upgrade, not the default.

## 2. FR-039 platform-output boundary rule (foundational — governs every other decision below)

- **Decision**: Per FR-039, the platform's BigQuery writes are **exactly**
  four tables: `correlated_alerts` (new links), `incidents` (new/updated
  rows), `remediation_logs` (appended outcomes), and `incident_postmortems`
  (upserted). **No other new BigQuery table is created for platform
  output** — not for risk forecasts, executive metrics, audit logs,
  approval decisions, incident timelines, or the alert-replay clustering
  window. Every platform-computed artifact that isn't one of those four
  BigQuery outputs is homed instead in:
  - **Firestore** — live/ephemeral state that the UI reads in real time:
    `incidents/{incident_id}` (denormalized live projection + stage
    history/timeline), `approvals/{action_id}` (the pending→approved/
    rejected remediation queue — this *is* the Approval Decision and
    Remediation Action record, there is no separate BigQuery table for
    either), `predictions/{service_name}__{alert_type}` (latest risk
    forecast/anomaly snapshot), `executive_metrics/latest` (latest
    computed business-impact snapshot), `pending_alerts/{replay_event_id}`
    (short-TTL sliding window used only for live clustering — see §11).
  - **Cloud Logging** — the Audit Log Entry (FR-037/NFR-008): structured
    log entries (`jsonPayload: {actor, action, resource, timestamp}`),
    queryable via Cloud Logging's query language and exportable to BigQuery
    later for long-term compliance retention if ever required (Assumptions
    section already treats retention as "standard organizational practice",
    not a hard requirement of this feature).
- **Rationale**: This is a direct, literal reading of FR-039 ("all
  platform-generated output is confined to ...") combined with FR-001's
  "MUST NOT ... stand up any new warehouse". The **prior (stale) plan
  invented six new BigQuery tables** (`core.remediation_actions`,
  `core.approval_decisions`, `core.risk_forecasts`, `core.executive_metrics`,
  `core.audit_log`, `core.incident_timeline_events`) that would all violate
  this constraint under the rewritten spec — this rewrite removes every one
  of them and replaces them with Firestore/Cloud Logging homes. This also
  happens to align with the mandated-service list: Cloud Logging is
  explicitly mandated and otherwise had no clear required use in the prior
  plan.
- **Alternatives considered**: A new, clearly-separate "platform ops"
  BigQuery dataset (e.g. `sre_platform_ops`) for these artifacts — technically
  arguable as a "new supporting resource" rather than "the warehouse", but
  rejected as a needlessly literal-minded reading against FR-039's plain
  "confined to [these four tables]" language; Firestore/Cloud Logging are
  also a strictly better technical fit for low-latency live reads and
  immutable audit trails respectively.

## 3. BigQuery Vector Search — exact current syntax (live-verified 2026-09-24)

- **Decision**: Use the **batch `VECTOR_SEARCH` syntax** for runbook
  retrieval:

  ```sql
  SELECT
    base.runbook_id, base.title, base.risk_level, base.steps,
    base.rollback_steps, distance AS vector_distance
  FROM VECTOR_SEARCH(
    TABLE `sre_knowledge_base.runbooks`,
    'embedding',
    (SELECT ml_generate_embedding_result AS query_embedding
     FROM AI.GENERATE_EMBEDDING(
       MODEL `sre_knowledge_base.embedding_model`,
       (SELECT @query_text AS content),
       STRUCT('RETRIEVAL_QUERY' AS task_type))),
    query_column_to_search => 'query_embedding',
    top_k => 5,
    distance_type => 'COSINE'
  )
  ORDER BY vector_distance ASC;
  ```

  Confirmed-current signature (fetched from
  `docs.cloud.google.com/bigquery/docs/reference/standard-sql/search_functions`):
  `VECTOR_SEARCH({TABLE base_table|(base_table_query)}, column_to_search,
  {TABLE query_table|(query_table_query)} [, query_column_to_search =>][,
  top_k =>][, distance_type =>][, options =>])`, returning `base.*`,
  `query.*` (batch form only), and `distance`.
- **Rationale**: This is the real, currently-documented GA function
  signature (re-fetched live, not recalled) — the named
  `query_column_to_search` argument matters because the query subquery's
  output column is `ml_generate_embedding_result`, not `embedding`, and the
  function does not auto-match differently-named columns.
- **Alternatives considered**: The single-search syntax with
  `query_value => AI.EMBED(@query_text, endpoint => 'text-embedding-005').result`
  is simpler (no subquery) and confirmed to exist, but was **not** chosen as
  primary because `AI.EMBED`'s implicit connection/model resolution isn't
  guaranteed to reuse the exact same connection/model object
  (`sre_knowledge_base.embedding_model`) that produced the stored
  `runbooks.embedding` values — reusing the *same* model object
  deterministically avoids any risk of a dimensionality/model mismatch
  between query and stored embeddings. Documented as a viable simplification
  once the demo confirms `AI.EMBED`'s default connection is configured in
  the target project.

## 4. Query-time embedding generation only (no ingest-time embedding pipeline)

- **Decision**: The **only** embedding generated by this feature is the
  **query embedding**, computed at retrieval time from the incident's
  current evidence text (root cause reasoning + a sample of correlated
  alert `message` values, redacted, concatenated), via
  `AI.GENERATE_EMBEDDING` (recommended current function; the older
  `ML.GENERATE_EMBEDDING` — fully verified syntax, output column
  `ml_generate_embedding_result` — remains a documented fallback) against
  the **existing** `sre_knowledge_base.embedding_model` remote model. No
  embedding is ever written back to `runbooks` or any other existing table.
- **Rationale**: FR-003 explicitly forbids re-generating/maintaining a
  separate embedding pipeline for runbook content; the existing 768-dim
  `runbooks.embedding` values are assumed correct/current (Assumptions).
  The only genuinely new embedding need is turning the *incident's*
  free-text evidence into a comparable vector at the moment retrieval runs.
  `task_type => 'RETRIEVAL_QUERY'` (vs. `RETRIEVAL_DOCUMENT` used when the
  existing runbook embeddings were presumably generated) is the
  documented, correct task type for the query side of an asymmetric
  retrieval pair.
- **Note on function naming**: Google's current docs state *"the
  `AI.GENERATE_EMBEDDING` function offers the same functionality \[as
  `ML.GENERATE_EMBEDDING`\] with simplified column names in the output...
  For new queries, we recommend `AI.GENERATE_EMBEDDING`."* This plan
  defaults to `AI.GENERATE_EMBEDDING` for new code, but implementers MUST
  confirm `AI.GENERATE_EMBEDDING`'s exact output column name against
  current docs before relying on it literally — `ML.GENERATE_EMBEDDING`'s
  `ml_generate_embedding_result` output column is the one confirmed in
  detail in this research pass and is a safe fallback.

## 5. No new vector index

- **Decision**: Do **not** run `CREATE VECTOR INDEX` on `runbooks.embedding`.
  `VECTOR_SEARCH` is queried directly against the existing column with an
  explicit `distance_type => 'COSINE'`.
- **Rationale**: `runbooks` has ~20 rows. Vector indexes (`IVF`/`TREE_AH`)
  exist to approximate nearest-neighbor search over large corpora; at this
  scale BigQuery performs exact brute-force search regardless (fast, and
  more accurate than an approximate index). Creating an index would also be
  a DDL/metadata change against a table this feature is meant to treat as
  strictly read-only (FR-039) for no measurable benefit. If the runbook
  corpus grows substantially post-hackathon, revisit.

## 6. Predictive forecasting (BigQuery ML)

- **Decision**: A single **`ARIMA_PLUS`** time-series model,
  `sre_ml_ops.alert_trend_forecast_model` (a **new**, platform-owned
  dataset — not one of the four existing warehouse datasets), trained on
  `sre_telemetry.alert_stream(service_name, alert_type, timestamp,
  measured_value)` with `TIME_SERIES_ID_COL = ['service_name',
  'alert_type']`. `ML.FORECAST` produces the outage prediction (time-to-
  failure window + confidence interval), `ML.DETECT_ANOMALIES` on the same
  model produces the anomaly-trend flag (AC-3.2), and `ML.EXPLAIN_FORECAST`
  sources the plain-language rationale (NFR-010).

  ```sql
  CREATE OR REPLACE MODEL `sre_ml_ops.alert_trend_forecast_model`
  OPTIONS (
    MODEL_TYPE = 'ARIMA_PLUS',
    TIME_SERIES_TIMESTAMP_COL = 'timestamp',
    TIME_SERIES_DATA_COL = 'measured_value',
    TIME_SERIES_ID_COL = ['service_name', 'alert_type'],
    HORIZON = 60,
    AUTO_ARIMA = TRUE
  ) AS
  SELECT service_name, alert_type, timestamp, measured_value
  FROM `sre_telemetry.alert_stream`
  WHERE service_name IS NOT NULL;

  -- Forecast
  SELECT * FROM ML.FORECAST(
    MODEL `sre_ml_ops.alert_trend_forecast_model`,
    STRUCT(60 AS horizon, 0.95 AS confidence_level));

  -- Anomaly flag (independent of a full prediction, AC-3.2)
  SELECT * FROM ML.DETECT_ANOMALIES(
    MODEL `sre_ml_ops.alert_trend_forecast_model`,
    STRUCT(0.95 AS anomaly_prob_threshold));

  -- Plain-language rationale (NFR-010)
  SELECT * FROM ML.EXPLAIN_FORECAST(
    MODEL `sre_ml_ops.alert_trend_forecast_model`,
    STRUCT(60 AS horizon, 0.95 AS confidence_level));
  ```

  `ML.FORECAST` syntax re-confirmed live 2026-09-24 against
  `docs.cloud.google.com/.../bigqueryml-syntax-forecast`.
- **Rationale**: One trained model family serves both FR-022 (prediction)
  and FR-023 (anomaly, independent of a full prediction) without building
  two ML systems, and `ML.EXPLAIN_FORECAST` directly satisfies NFR-010's
  "human-readable rationale" requirement for every automated determination.
- **Alternatives considered**: `AI.FORECAST` with BigQuery ML's built-in
  TimesFM model — genuinely simpler (no `CREATE MODEL`/training step at
  all), confirmed to exist as of this research pass, but **rejected** as
  primary because it is a managed foundation model without a confirmed
  `ML.EXPLAIN_FORECAST`-equivalent rationale output, and NFR-010 is a hard
  requirement here. Worth revisiting if `AI.FORECAST` gains an
  explainability output. **Retrain cadence (fixed, T6)**: Cloud Scheduler
  retrains `sre_ml_ops.alert_trend_forecast_model` every 15 minutes
  (`*/15 * * * *`, `infra/environments/demo/terraform.tfvars`
  `bqml_retrain_schedule_cron`), and `predictions.tick` fires every 2
  minutes (`predictions_tick_schedule_cron`) — both comfortably inside a
  single demo replay run, so a forecast can reliably precede its
  corresponding replayed alert (AC-4.1). This resolves
  checklists/architecture.md CHK034 and design.md §11 risk #2.

## 7. Network topology "dependency" — flagged assumption (no explicit edge column)

- **Observation**: Per spec.md's Key Entities, `network_nodes` exposes only
  `node_id, node_name, node_type, region, ip_address, status` — **no
  explicit dependency/edge column**. FR-008/FR-009 nonetheless require a
  "dependency/blast-radius graph" and clustering must distinguish related
  vs. unrelated alert groups (FR-011).
- **Decision (flagged assumption, same discipline as spec.md's own
  `customer_accounts` column caveat)**: Infer topological relatedness from
  two **data-driven** signals rather than a hardcoded static graph: (a)
  same `node_type` + same `region` as a same-tier proximity signal, and (b)
  empirical co-occurrence — services/nodes that have previously appeared
  together in the same `incidents`/`correlated_alerts` cluster, or whose
  `alert_stream` rows co-occur within the current clustering time window,
  are treated as topologically adjacent for blast-radius purposes.
  Implementers MUST run `INFORMATION_SCHEMA.COLUMNS` against
  `sre_topology.network_nodes` before finalizing this approach, in case an
  edge/relationship column exists beyond the six documented in spec.md.
- **Rationale**: Avoids inventing a fictitious schema column, keeps
  clustering genuinely data-derived rather than a hardcoded static graph
  (consistent with NFR-011's spirit even though NFR-011 is literally scoped
  to resolution logic), and degrades gracefully — if no richer signal
  exists, same-`node_type`/`region` plus historical co-occurrence is still
  a defensible, explainable heuristic.

## 8. Schema verification discipline for non-enumerated existing tables

- **Decision**: `alert_stream`, `network_nodes`, `runbooks`/
  `embedding_model`, and `incident_postmortems` have their full column sets
  enumerated by spec.md and are used exactly as documented. `incidents` and
  `remediation_logs`, however, are only *partially* described by spec.md
  (purpose + key linkage columns, not an exhaustive field list) — column
  names used in this plan/data-model for these two tables beyond
  `incident_id`, `status`, `runbook_id` (e.g. `root_cause`,
  `root_cause_confidence`, `opened_at`, `resolved_at`, `outcome`,
  `executed_at`) are **illustrative placeholders**, consistent with the
  entity's documented purpose, and MUST be confirmed against
  `INFORMATION_SCHEMA.COLUMNS` at implementation time — exactly the same
  discipline spec.md already applies to `customer_accounts`.
- **Rationale**: Prevents the plan from silently asserting unverified
  schema detail as fact while still being concrete enough to design
  against.

## 9. ADK agent orchestration pattern

- **Decision (carried forward, re-confirmed)**: Each of the 6 agents is an
  ADK **`LlmAgent`** (structured `output_schema`, domain tools, per-agent
  model). They are composed by a **custom event-driven orchestrator**
  (`agent-orchestrator`, a FastAPI Cloud Run service using `Runner` +
  Pub/Sub + Firestore state), **not** ADK's `SequentialAgent`/
  `ParallelAgent`/`LoopAgent` wrapper classes.
- **Rationale**: Per the user's explicit instruction, this decision is kept
  unless it has since changed. Direct inspection of `google/adk-python`
  (source + tests) previously showed `SequentialAgent`, `ParallelAgent`, and
  `LoopAgent` explicitly `@deprecated` in favor of a new graph-based
  `Workflow` API not yet usable as an `LlmAgent` sub-agent. Independent of
  deprecation status, the architecture's own shape — agents reacting to
  asynchronous events (a replayed alert, a Cloud Scheduler tick, a human
  approval decision) with durable state between stages — is a fundamentally
  different shape than in-process `sub_agents=[...]` composition. A thin
  custom orchestrator calling `Runner.run_async(...)` per stage, keyed by
  `incident_id`, depends only on the stable `LlmAgent`/`Runner` surface and
  lets each stage scale/schedule independently via its own Pub/Sub
  subscription. Re-verify this specific ADK deprecation status before
  writing real orchestration code if significant time has passed.
- **Alternatives considered**: ADK `Workflow` graph API (too new/
  experimental for the hackathon timeline). `SequentialAgent`/
  `ParallelAgent`/`LoopAgent` (deprecated; don't naturally span independent
  Cloud Run services/Pub/Sub boundaries anyway).

## 10. Inter-agent communication & state

- **Decision**: Pub/Sub topics as the control-flow backbone (`alerts.replay`,
  `incidents.correlated`, `incidents.root_cause_identified`,
  `incidents.runbook_matched`, `remediation.proposed`,
  `remediation.approved`, `remediation.rejected`, `remediation.executed`,
  `incidents.resolved`, `predictions.tick`, `risk.forecast.created`,
  `executive.metrics.updated` — see `contracts/pubsub-events.md`). BigQuery
  holds the four FR-039 tables as durable system-of-record for outcomes;
  Firestore holds every live/ephemeral read model per §2. Writing
  BigQuery (when applicable) before Firestore before publishing the next
  event gives a consistent "durable-then-fast-path" ordering.
- **Rationale**: Matches the spec's implicit event-driven shape (alert
  bursts, human approval, scheduled prediction ticks) without inventing new
  ingestion-era topics (`ingestion.*` is removed entirely — there is no
  ingestion in this feature).
- **Alternatives considered**: Direct agent-to-agent HTTP calls — rejected,
  doesn't survive a subscriber being temporarily down (violates NFR-012).

## 11. Alert replay/streaming simulation mechanism

- **Decision**: A dedicated `alert-replay-service` Cloud Run service reads
  `sre_telemetry.alert_stream` (read-only, ordered by `timestamp`) and
  republishes each row, looping back to the start once exhausted, at a
  controlled rate to sustain ≥1,000 msgs/min (per FR-004/NFR-001). Every
  republished occurrence is wrapped in an envelope:

  ```json
  {
    "replay_event_id": "uuid-v4",
    "occurred_at": "RFC3339 (rewritten arrival timestamp, = now())",
    "source_alert": {
      "alert_id": "string (natural id, from alert_stream)",
      "node_id": "string", "service_name": "string", "severity": "string",
      "alert_type": "string", "message": "string (redacted before publish)",
      "measured_value": 0.0, "original_timestamp": "RFC3339 (alert_stream.timestamp)"
    }
  }
  ```

  The Alert Correlation Agent dedups/clusters on `replay_event_id`, never on
  the reused natural `alert_id` (Clarification #2 / FR-004). The service
  never inserts, mutates, or duplicates rows in `alert_stream` itself — it
  is a pure reader republishing to Pub/Sub.
- **Rationale**: Directly implements the spec's Clarification #2 and
  FR-004; looping over the finite ~3,000-row history is explicitly
  sanctioned by the Assumptions section as the mechanism to sustain the
  1,000+/min peak-burst target.
- **Note**: The short-lived clustering window this feeds
  (`pending_alerts/{replay_event_id}` in Firestore, TTL ~10 minutes) is
  *not* a "duplicated copy of alert_stream" in the FR-002 sense — it is the
  live replay event log itself, which exists nowhere else durably, not a
  cache substituting for querying the warehouse. Topology/precedent lookups
  the Alert Correlation Agent performs against `network_nodes` and
  historical `incidents`/`correlated_alerts` remain live BigQuery queries.

## 12. Human-in-the-loop approval gate

- **Decision (carried forward)**: The Remediation Agent's proposal tool and
  its execution tool are two physically separate functions; only the
  execution tool calls the real Cloud Run Admin API, and it is only
  reachable from the `remediation.approved` Pub/Sub event, which is only
  ever published by `api-gateway`'s authenticated
  `/approvals/{actionId}/decision` endpoint — never by the LLM's own
  judgement.
- **Rationale**: Satisfies NFR-009 structurally (the model has no code path
  to self-approve) rather than relying on a prompt instruction.

## 13. Sandbox remediation execution target

- **Decision (carried forward)**: A dedicated `demo-target-service` Cloud
  Run service (Terraform-deployed, isolated service account scoped only to
  that service via `roles/run.developer`) is the real execution target. The
  Remediation Agent's execution tool calls the actual Cloud Run Admin API
  against it and records the literal API response/exit status into
  `remediation_logs`.
- **Rationale**: Satisfies the spec's Clarification (remediation execution
  is real, not simulated) while keeping blast radius contained to a
  purpose-built, low-privilege service, never production infrastructure.

## 14. Authentication & RBAC

- **Decision (carried forward)**: Firebase Authentication / Google Identity
  Platform for all end-user sign-in, with custom claims (`role`) set at
  user-provisioning time for the 5 demo roles. `api-gateway` verifies the
  Firebase ID token on every request and authorizes based on the claim; GCP
  IAM is kept entirely separate and governs only service-to-service access
  to GCP resources (BigQuery, Pub/Sub, Cloud Run, Firestore, per service
  account) — least-privilege, one service account per Cloud Run service.
- **Rationale**: Matches the spec's Clarification exactly; keeps human RBAC
  and machine IAM independently auditable.

## 15. Secrets, PII/secret redaction, audit logging

- **Decision**: All credentials/connection strings live in Secret Manager,
  mounted as Cloud Run secret env vars (never baked into images or returned
  by any API). Because this feature has **no ingestion step**, redaction
  cannot happen "at write time" as the prior plan assumed — it now happens
  at **read/output time**, applied by the shared
  `agents/common/redaction.py` utility every time free-text warehouse
  content (`alert_stream.message`, runbook `steps`/`content`, `incidents`
  notes) is pulled into an agent prompt, a generated summary/script, a
  dashboard field, or a log line — before it ever leaves the service
  boundary. Every security-relevant action (incident access, approval
  decision, remediation execution) additionally writes a structured Cloud
  Logging entry (§2) per FR-037.
- **Alternatives considered**: Cloud DLP API `deidentify` for stronger
  redaction guarantees — documented optional post-hackathon hardening, not
  required for the mandatory-service list.

## 16. Postmortem write path

- **Decision**: A single `MERGE` upserts `incident_postmortems` by
  `incident_id`, incrementing `version` on an existing row instead of
  inserting a duplicate (FR-032):

  ```sql
  MERGE `sre_incident_mart.incident_postmortems` AS target
  USING (SELECT @incident_id AS incident_id) AS source
  ON target.incident_id = source.incident_id
  WHEN MATCHED THEN UPDATE SET
    generated_at = CURRENT_TIMESTAMP(),
    root_cause_summary = @root_cause_summary,
    timeline_summary = @timeline_summary,
    remediation_summary = @remediation_summary,
    business_impact_summary = @business_impact_summary,
    full_report_markdown = @full_report_markdown,
    version = target.version + 1
  WHEN NOT MATCHED THEN INSERT
    (incident_id, generated_at, root_cause_summary, timeline_summary,
     remediation_summary, business_impact_summary, full_report_markdown, version)
    VALUES (@incident_id, CURRENT_TIMESTAMP(), @root_cause_summary,
     @timeline_summary, @remediation_summary, @business_impact_summary,
     @full_report_markdown, 1);
  ```

- **Rationale**: `MERGE` is the standard, atomic way to express "update if
  exists, else insert" in BigQuery, directly satisfying FR-032's
  no-duplicate rule with an explicit version counter, using exactly the
  column set the spec's Clarification defined.

## 17. Cloud Run autoscaling configuration (quantified per stage)

- **Decision**: Each agent stage is its own Pub/Sub push subscription
  target with independently tuned autoscaling, since alert-arrival volume
  (Agent 1) and incident-granularity volume (Agents 2/3/5/6) differ by
  orders of magnitude:

  | Service / subscription | Concurrency | Min instances | Max instances | Notes |
  |---|---|---|---|---|
  | `alert-replay-service` | 1 | 1 | 3 | Rate-limited in-app (token bucket), not scale-driven |
  | `agent-orchestrator` → Alert Correlation (Agent 1) | 20 | 2 | 50 | Highest volume: ≥1,000 msgs/min raw alerts |
  | `agent-orchestrator` → Root Cause / Runbook / Remediation / Executive (Agents 2,3,5,6) | 4 | 0 | 20 | Incident-granularity, LLM-call-bound (bound concurrency to protect per-instance memory/LLM connections) |
  | `agent-orchestrator` → Predictive Risk (Agent 4) | 4 | 0 | 5 | Scheduler-triggered only, not alert-driven |
  | `api-gateway` | 40 | 1 | 20 | Human-facing, latency-sensitive |
  | `demo-target-service` | 10 | 0 | 3 | Sandbox target only, trivial load |

  Dead-letter topics (`<topic>-dlq`) after 5 delivery attempts on every
  subscription, so a stuck message never blocks the rest of the pipeline
  (NFR-012).
- **Rationale**: Directly answers NFR-001/002/FR-024/FR-025 with concrete,
  reviewable numbers instead of "autoscaling enabled" — 1,000 msgs/min ≈ 17
  msgs/sec; at concurrency 20 and even a pessimistic ~1s per message, 2
  warm instances alone clear the target, with headroom to 50 for burst
  smoothing.

## 18. BigQuery query parameterization (SQL injection prevention)

- **Decision**: Every BigQuery query issued by any agent/service that
  incorporates an event- or user-derived value (`incident_id`, `alert_id`,
  `service_name`, free-text search content, etc.) MUST use the BigQuery
  client library's named-parameter API (`@param` query parameters via
  `QueryJobConfig`/`QueryParameter`, per language). String-concatenating
  values into SQL text is prohibited. All SQL sketches in this plan and in
  `data-model.md` use `@param`-style placeholders precisely to make this
  requirement explicit and reviewable.
- **Rationale**: OWASP Top 10 (Injection) applies directly — several inputs
  here (alert `message`, runbook content, incident free text) are
  attacker-influenceable if the warehouse ever ingests untrusted data
  upstream of this feature. This was an unstated gap in the prior plan.

## 19. Frontend

- **Decision (carried forward)**: Next.js (App Router) + React + TypeScript,
  Tailwind CSS, Firebase JS SDK for auth + realtime Firestore reads
  (incidents, approvals, predictions, executive metrics all live in
  Firestore per §2, so the entire frontend can be realtime-first rather
  than split between realtime and polled REST reads as the prior plan
  assumed) with a typed REST client against `api-gateway` for on-demand
  BigQuery-backed drill-downs (e.g., the full correlated-alert list or
  dependency graph for one incident).
- **Rationale**: Because §2 moved every live-read artifact into Firestore,
  the frontend's realtime/polled split simplifies considerably versus the
  prior architecture.

## 20. Testing strategy summary

- **Decision**: pytest (services/agents, mocked GCP clients) + emulator-based
  integration tests (Firestore + Pub/Sub emulators; BigQuery has no local
  emulator, so tests run against a disposable dev dataset in the real
  project) + a load-test script publishing ≥1,000 msgs/min to
  `alerts.replay` to validate NFR-001/002 against the concrete autoscaling
  table in §17 + a redaction/secret-leakage scan (SC-008) + a
  parameterization lint/grep check in CI (§18) + a static check blocking
  literal alert/runbook/service identifiers inside agent source (outside
  test fixtures) plus an ADK agent-eval run against a held-out subset of
  `alert_stream`/`runbooks` rows never referenced in prompts, together
  verifying NFR-011 ("no hardcoded mappings") + Terraform validate/plan for
  every newly-created resource. Full detail in `quickstart.md` and the
  plan's Testing & Verification Strategy table.

All items above are resolved — no outstanding `NEEDS CLARIFICATION` markers
remain for Phase 1.
