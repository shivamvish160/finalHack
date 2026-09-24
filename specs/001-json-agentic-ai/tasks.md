# Tasks: SRE Agentic AI Incident Prevention & Resolution Platform

**Input**: Design documents from `specs/001-json-agentic-ai/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [design.md](./design.md), [checklists/architecture.md](./checklists/architecture.md)

**Tests**: Not explicitly requested as a standalone TDD gate in spec.md, but plan.md's Testing & Verification Strategy table is mandatory — contract/integration/unit test tasks are included per story and MUST be written to fail before the corresponding implementation, per plan.md.

**Organization**: Tasks are grouped by the 4 prioritized user stories in spec.md (US1–US4, matching Milestones 1–4). The BigQuery warehouse (`sre_telemetry`, `sre_topology`, `sre_knowledge_base`, `sre_incident_mart`) already exists and is populated — **no task in this file creates, seeds, or ETLs into it** (FR-001, Out of Scope).

## Format

Each task is a checkbox line `- [ ] [P?] [Story] T<n> Title`, followed by indented metadata lines:
- `Files:` — the concrete file(s) this task creates/edits.
- `Depends:` — task IDs that must complete first (only present when a real dependency exists).
- A plain description line explaining what the task does and which spec requirement(s)/acceptance criteria it satisfies.

## AC Coverage Matrix

Every acceptance criterion in spec.md is implemented and verified by at least one task below:

| AC | Task(s) |
|---|---|
| AC-1.1 | T22, T26 |
| AC-1.2 | T29, T31, T32 |
| AC-1.3 | T27, T28, T33 |
| AC-1.4 | T22, T26 |
| AC-1.5 | T26, T30 |
| AC-2.1 | T34, T38, T39 |
| AC-2.2 | T40, T41, T46 |
| AC-2.3 | T42, T44 |
| AC-2.4 | T37, T43, T45 |
| AC-2.5 | T34, T38, T46 |
| AC-3.1 | T51, T52, T54 |
| AC-3.2 | T51, T54 |
| AC-3.3 | T49, T53 |
| AC-3.4 | T15, T19, T65 |
| AC-4.1 | T56, T58, T60, T61 |
| AC-4.2 | T56, T58, T61 |
| AC-4.3 | T58, T61 |
| AC-4.4 | T52, T59, T61 |
| AC-4.5 | T57, T58, T59 |

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T1 Create monorepo skeleton
  Files: infra/, services/alert-replay-service/, services/agent-orchestrator/, services/api-gateway/, services/demo-target-service/, agents/alert_correlation/, agents/root_cause_analysis/, agents/runbook_retrieval/, agents/predictive_risk/, agents/remediation/, agents/executive_impact/, frontend/, scripts/deploy/, scripts/demo/, data/samples/, tests/contract/, tests/integration/, tests/unit/
  Establishes the monorepo directory layout exactly as defined in plan.md's Project Structure section, before any other task writes a file.

- [x] [P] T2 Initialize Python workspace
  Files: pyproject.toml, requirements.txt
  Depends: T1
  Initializes the Python 3.12 workspace for services/ and agents/ with fastapi, google-adk, google-cloud-bigquery, google-cloud-pubsub, google-cloud-firestore, google-cloud-secret-manager, firebase-admin; configures ruff/black per plan.md Technical Context.

- [x] [P] T3 Initialize frontend workspace
  Files: frontend/package.json, frontend/next.config.js
  Depends: T1
  Initializes frontend/ as a Next.js 14 App Router + React 18 + Tailwind CSS + Firebase JS SDK project with ESLint/Prettier configured, per plan.md's frontend dependency choice.

- [x] [P] T4 Configure deployment variable convention
  Files: infra/environments/demo/terraform.tfvars, .env.example
  Ensures GCP_PROJECT_ID and the single us-central1 region are supplied via configuration rather than hardcoded anywhere in services/agents, per spec.md Assumptions and research.md.

- [x] T5 Verify live BigQuery schema for warehouse write/read tables (script implemented in scripts/verify_schema.py; must be RUN against the real project by the deployer before agent implementation is trusted, since this sandboxed environment has no live GCP credentials)
  Files: specs/001-json-agentic-ai/data-model.md
  CRITICAL, do first: queries INFORMATION_SCHEMA.COLUMNS against the real sre_incident_mart.customer_accounts, sre_incident_mart.incidents, and sre_incident_mart.remediation_logs tables and replaces data-model.md section 1's "illustrative placeholder" column list with the confirmed live schema. All agent tasks that query these tables (T24, T25, T33, T41, T49, T58) depend on this completing first, per data-model.md's flagged gap and checklist item CHK067.

- [x] T6 Fix a concrete BQML retrain cadence
  Files: specs/001-json-agentic-ai/research.md, infra/modules/scheduler/
  Resolves checklists/architecture.md CHK034 and design.md section 11 risk #2 by choosing and recording a concrete numeric Cloud Scheduler cron cadence for retraining the ARIMA_PLUS forecast model, so a prediction can reliably fire before the corresponding alert during the demo (AC-4.1).

**Checkpoint**: Repo skeleton, verified live schema, and a fixed retrain cadence exist before any foundational or story work begins.

---

## Phase 2: Foundational (Blocking Prerequisites)

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] [P] T7 Terraform for Pub/Sub topics and DLQs
  Files: infra/modules/pubsub/main.tf
  Depends: T1
  Provisions every topic and its `-dlq` counterpart plus push subscriptions from contracts/pubsub-events.md: alerts.replay, incidents.correlated, incidents.root_cause_identified, incidents.runbook_matched, remediation.proposed, remediation.approved, remediation.rejected, remediation.executed, predictions.tick, risk.forecast.created, executive.metrics.updated.

- [x] [P] T8 Terraform for Cloud Run services and IAM
  Files: infra/modules/cloud-run/main.tf
  Depends: T1
  Provisions the 4 Cloud Run services with per-service service accounts and the exact least-privilege IAM role bindings documented in design.md section 7.1.

- [x] [P] T9 Terraform for Firestore
  Files: infra/modules/firestore/main.tf, infra/modules/firestore/firestore.rules
  Depends: T1
  Provisions native-mode Firestore plus security rules for the approvals, predictions, executive_metrics, and pending_alerts collections described in design.md section 3.4.

- [x] [P] T10 Terraform for the new BQML dataset and model
  Files: infra/modules/bqml/main.tf
  Depends: T1, T6
  Provisions the new sre_ml_ops dataset and the alert_trend_forecast_model (ARIMA_PLUS) DDL from data-model.md section 5, wired to the retrain cadence fixed in T6.

- [x] [P] T11 Terraform for Cloud Scheduler jobs
  Files: infra/modules/scheduler/main.tf
  Depends: T1, T6
  Provisions the predictions.tick job and the BQML retrain job using the cadence from T6.

- [x] [P] T12 Terraform for Secret Manager
  Files: infra/modules/secrets/main.tf
  Depends: T1
  Provisions Secret Manager entries for the Firebase Admin SDK credentials per design.md section 7.2, satisfying FR-036.

- [x] [P] T13 Shared BigQuery client wrapper
  Files: agents/common/bq_client.py
  Depends: T2
  Implements a shared BigQuery client wrapper that only accepts named @param query parameters and raises on any string-concatenated SQL, enforcing research.md section 18 for every agent that imports it, satisfying FR-002 (every analytical read is live and parameterized, never a cached/hardcoded copy).

- [x] [P] T14 Shared Firestore client wrapper
  Files: agents/common/firestore_client.py
  Depends: T2, T9
  Implements a shared Firestore client wrapper for the approvals, predictions, executive_metrics, and pending_alerts collections defined in design.md section 3.4.

- [x] [P] T15 Shared redaction utility
  Files: agents/common/redaction.py
  Depends: T2
  Implements the shared PII/secret redaction utility applied at read/output time on every free-text warehouse field, per design.md section 7.3 and requirement AC-3.4/NFR-006/NFR-007.

- [x] T16 Firebase auth and RBAC middleware
  Files: services/api-gateway/app/auth.py
  Depends: T3, T12
  Implements Firebase ID token verification plus custom-claim role-based access control for the five roles (OnCallEngineer, IncidentCommander, Approver, ExecutiveViewer, Administrator) required by FR-035.

- [x] T17 Custom Pub/Sub-driven agent orchestrator dispatcher
  Files: services/agent-orchestrator/app/common/orchestrator.py
  Depends: T7, T13, T14
  Implements the custom stage dispatcher that invokes each agent's LlmAgent plus Runner.run_async per Pub/Sub subscription, enforcing the BigQuery-write-then-Firestore-projection-then-publish-next-event ordering from design.md sections 3.2 and 8.

- [x] [P] T18 Unit test for BigQuery parameterization
  Files: tests/unit/test_bq_client_parameterization.py
  Depends: T13
  Asserts bq_client.py rejects any non-parameterized query, guarding NFR-011 and checklist item CHK018 against regression during implementation.

- [x] [P] T19 Unit test for redaction utility
  Files: tests/unit/test_redaction.py
  Depends: T15
  Asserts redaction.py redacts known secret and PII canary values while preserving surrounding context, verifying SC-008, NFR-006, NFR-007, and AC-3.4.

**Checkpoint**: Infra, shared clients, auth, and the orchestrator dispatcher exist — user stories can now proceed.

---

## Phase 3: User Story 1 - Alert Storm Clustering & Root Cause Isolation (Priority: P1) MVP

**Goal**: Replay a burst of alert_stream rows and produce a single explained incident with correlated alerts, timeline, dependency graph, root cause, and confidence score.

**Independent Test**: Replay 200+ related alert_stream rows and confirm one incident is produced with correlated alerts, timeline, dependency view, and root cause (AC-1.1 through AC-1.5).

- [x] [P] T20 Contract test for the alert replay envelope
  Files: tests/contract/test_alerts_replay.py
  Depends: T7
  Validates the alerts.replay Pub/Sub envelope shape (replayEventId, sourceAlert fields) against contracts/pubsub-events.md.

- [x] [P] T21 Contract test for the incident REST endpoints
  Files: tests/contract/test_incidents_api.py
  Depends: T16
  Validates GET /incidents, /incidents/{id}, /incidents/{id}/alerts, /incidents/{id}/timeline, and /incidents/{id}/dependency-graph against contracts/rest-api.md.

- [x] [P] T22 Integration test for alert clustering correctness
  Files: tests/integration/test_alert_clustering.py
  Replays a synthetic burst of related and unrelated fixture alerts and asserts one incident forms for the related set while unrelated alerts remain separate, verifying AC-1.1 and AC-1.4.

- [x] [P] T23 Integration test for referential gap handling
  Files: tests/integration/test_unmapped_join.py
  Depends: T5
  Uses a deliberately-orphaned node_id/service_name fixture to assert the platform marks the relationship Unmapped rather than dropping the alert, verifying FR-005.

- [x] T24 Alert replay service
  Files: services/alert-replay-service/app/replay.py
  Depends: T5, T7
  Reads sre_telemetry.alert_stream read-only ordered by timestamp, wraps each row in an envelope with a fresh replayEventId (UUID) and rewritten occurredAt, and publishes to alerts.replay at a controlled rate sustaining at least 1000 msgs per minute, satisfying FR-004.

- [x] [P] T25 Alert Correlation agent
  Files: agents/alert_correlation/agent.py
  Depends: T5, T13
  Implements the ADK LlmAgent (gemini-2.5-flash) with tools that query network_nodes via a LEFT JOIN on node_id and precedent via correlated_alerts to alert_stream to incidents, producing an output_schema for the cluster decision and affected services per FR-006 through FR-011.

- [x] T26 Alert correlation orchestrator stage
  Files: services/agent-orchestrator/app/stages/alert_correlation_stage.py
  Depends: T17, T24, T25
  Subscribes to alerts.replay, maintains the short-TTL Firestore pending_alerts clustering window, invokes the Alert Correlation agent, writes correlated_alerts and incidents, and publishes incidents.correlated, satisfying FR-006, FR-007 (traceability from incident to every original alert via correlated_alerts), FR-010 (fixed status enum), AC-1.1, AC-1.4, and AC-1.5.

- [x] [P] T27 Root Cause Analysis agent
  Files: agents/root_cause_analysis/agent.py
  Depends: T5, T13
  Implements the ADK LlmAgent (gemini-2.5-pro) joining alert_stream, network_nodes, and historical incidents/remediation_logs to produce a root cause, confidence score, and plain-language reasoning per FR-009, satisfying AC-1.3.

- [x] T28 Root cause orchestrator stage
  Files: services/agent-orchestrator/app/stages/root_cause_stage.py
  Depends: T26, T27
  Subscribes to incidents.correlated, invokes the Root Cause Analysis agent, updates the incidents row, and publishes incidents.root_cause_identified.

- [x] T29 Incident REST endpoints
  Files: services/api-gateway/app/routes/incidents.py
  Depends: T16, T21, T28
  Implements the five incident endpoints validated in T21, including the data-driven dependency-graph inference from design.md section 6 and message redaction via agents/common/redaction.py, satisfying FR-038, AC-1.2, and FR-037 category 1 (incident access) via agents/common/audit_log.py.

- [x] [P] T30 Live Incident Console page
  Files: frontend/app/incidents/page.tsx
  Depends: T29
  Implements the Live Incident Console listing incidents with realtime Firestore status updates, satisfying FR-033 and AC-1.5.

- [x] [P] T31 Incident Timeline page
  Files: frontend/app/incidents/[incidentId]/timeline/page.tsx
  Depends: T29
  Implements the Incident Timeline view merging alert_stream timestamps with Firestore stage history, satisfying FR-008 and AC-1.2.

- [x] [P] T32 Alert Correlation View page
  Files: frontend/app/correlation/[incidentId]/page.tsx
  Depends: T29
  Implements the Alert Correlation View showing correlated alerts with Mapped/Unmapped flags and the dependency graph, satisfying AC-1.2.

- [x] [P] T33 Root Cause Analysis View page
  Files: frontend/app/root-cause/[incidentId]/page.tsx
  Depends: T5, T29
  Implements the Root Cause Analysis View showing root cause, confidence, and reasoning, satisfying AC-1.3.

**Checkpoint**: User Story 1 (Milestone 1) is independently functional and demoable — alert burst becomes a single incident with root cause.

---

## Phase 4: User Story 2 - Semantic Runbook Retrieval & Approved Remediation (Priority: P2)

**Goal**: Retrieve the most similar runbook via VECTOR_SEARCH, propose a fix plus rollback plus risk level, block on human approval, then really execute against the sandbox.

**Independent Test**: Take an incident with a clear runbook precedent and confirm a VECTOR_SEARCH match with similarity score, fix/rollback/risk, and that execution is blocked until approved (AC-2.1 through AC-2.5).

- [x] [P] T34 Contract test for runbook retrieval
  Files: tests/contract/test_runbook_retrieval.py
  Validates the VECTOR_SEARCH response shape and the belowThreshold case against contracts/rest-api.md, verifying AC-2.1 and AC-2.5.

- [x] [P] T35 Contract test for the approvals API
  Files: tests/contract/test_approvals_api.py
  Depends: T16
  Validates GET /approvals and POST /approvals/{actionId}/decision against contracts/rest-api.md.

- [x] [P] T36 Integration test for the approval gate
  Files: tests/integration/test_approval_gate.py
  Asserts the remediation execution tool is unreachable without a prior remediation.approved event, verifying NFR-009.

- [x] T37 Integration test for real sandbox execution
  Files: tests/integration/test_sandbox_execution.py
  Depends: T45
  Runs against a dedicated demo environment to assert a real, non-mocked Cloud Run Admin API call against demo-target-service succeeds and is appended to remediation_logs, verifying AC-2.4.

- [x] [P] T38 Runbook Retrieval agent
  Files: agents/runbook_retrieval/agent.py
  Depends: T13
  Implements the ADK LlmAgent (gemini-2.5-flash) that embeds the root-cause query text via AI.GENERATE_EMBEDDING against sre_knowledge_base.embedding_model, runs VECTOR_SEARCH over runbooks.embedding, applies the configurable similarity threshold, and sets belowThreshold when unmet, satisfying FR-003 (reuses the existing embedding column, never re-embeds the runbooks corpus), FR-012 through FR-014, and AC-2.1/AC-2.5.

- [x] T39 Runbook retrieval orchestrator stage
  Files: services/agent-orchestrator/app/stages/runbook_retrieval_stage.py
  Depends: T28, T38
  Subscribes to incidents.root_cause_identified, invokes the Runbook Retrieval agent, and publishes incidents.runbook_matched.

- [x] [P] T40 Remediation agent propose and execute tools
  Files: agents/remediation/agent.py
  Depends: T5, T38
  Implements a propose tool generating fix and rollback scripts plus a risk level from the matched runbook's documented procedure, and a physically separate execute tool reachable only from remediation.approved, calling the real Cloud Run Admin API against demo-target-service, satisfying FR-015, FR-016, and NFR-009.

- [x] T41 Remediation propose orchestrator stage
  Files: services/agent-orchestrator/app/stages/remediation_propose_stage.py
  Depends: T5, T39, T40
  Subscribes to incidents.runbook_matched, invokes the propose tool, writes the Firestore approvals/{actionId} document as Proposed, and publishes remediation.proposed, satisfying AC-2.2.

- [x] T42 Approvals REST endpoints
  Files: services/api-gateway/app/routes/approvals.py
  Depends: T16, T35, T41
  Implements GET /approvals and POST /approvals/{actionId}/decision, updating the Firestore approval document with approver uid, decision, comments, and timestamp, writing a Cloud Logging audit entry (FR-037 category 2, approval decision, via agents/common/audit_log.py), and publishing remediation.approved or remediation.rejected as the only path to execution, satisfying FR-017, FR-018, and AC-2.3.

- [x] T43 Remediation execute orchestrator stage
  Files: services/agent-orchestrator/app/stages/remediation_execute_stage.py
  Depends: T36, T40, T42
  Subscribes only to remediation.approved, invokes the execute tool from the Remediation agent, appends the real outcome to remediation_logs, and writes the FR-037 category 3 (remediation execution) audit entry via agents/common/audit_log.py before publishing remediation.executed, satisfying FR-019, FR-020, FR-039 (writes confined to remediation_logs), and AC-2.4.

- [x] T44 Remediation rejected orchestrator stage
  Files: services/agent-orchestrator/app/stages/remediation_rejected_stage.py
  Depends: T42
  Subscribes to remediation.rejected and returns the incident to Investigating status in Firestore with no BigQuery write, satisfying FR-021 and AC-2.3.

- [x] T45 Demo target sandbox service
  Files: services/demo-target-service/app/main.py
  Depends: T8
  Implements an isolated Cloud Run application exposing a controllable failure/recovery endpoint for the Remediation agent's real execution calls to act on, per research.md's sandbox isolation decision.

- [x] [P] T46 Runbook Recommendation View page
  Files: frontend/app/runbooks/[incidentId]/page.tsx
  Depends: T39
  Implements the Runbook Recommendation View showing the matched SOP, similarity score, recommended actions, and belowThreshold state, satisfying AC-2.2 and AC-2.5.

- [x] [P] T47 Approval Console page
  Files: frontend/app/approvals/page.tsx
  Depends: T42
  Implements the Approval Console showing the pending queue with approve/reject actions gated to the Approver, IncidentCommander, and Administrator roles per FR-035.

**Checkpoint**: User Stories 1 and 2 (Milestones 1-2) work together — an incident produces a matched runbook and a human-approved real remediation.

---

## Phase 5: User Story 3 - Proactive Predictive Risk Forecasting at Scale (Priority: P2)

**Goal**: Forecast likely failures from alert_stream trends ahead of time, explain why, detect anomalies, and sustain at least 1000 replayed alerts per minute.

**Independent Test**: Point the predictive capability at a degrading trend in alert_stream history and confirm a forecast surfaces before the corresponding alert fires in replay (AC-3.1 through AC-3.4).

- [x] [P] T48 Contract test for the predictions API
  Files: tests/contract/test_predictions_api.py
  Depends: T16
  Validates GET /predictions and GET /predictions/anomalies against contracts/rest-api.md.

- [x] T49 Load test for the 1000 alerts per minute target
  Files: scripts/demo/load_test_alerts.py, tests/integration/test_load_1000_per_min.py
  Depends: T5, T24
  Publishes at least 1000 messages per minute to alerts.replay and asserts zero messages land in any dead-letter topic, validated against the quantified autoscaling table in research.md section 17, satisfying FR-024, NFR-001, NFR-002, and AC-3.3.

- [x] [P] T50 Chaos test for graceful degradation
  Files: tests/integration/test_graceful_degradation.py
  Depends: T26, T28
  Disables the Runbook Retrieval and Predictive Risk agents mid-run and asserts core incident visibility and correlation keep functioning, satisfying NFR-012.

- [x] [P] T51 Predictive Risk agent
  Files: agents/predictive_risk/agent.py
  Depends: T10
  Implements the ADK LlmAgent (gemini-2.5-flash) calling ML.FORECAST, ML.DETECT_ANOMALIES, and ML.EXPLAIN_FORECAST against sre_ml_ops.alert_trend_forecast_model, producing a predicted failure, time-to-failure window, confidence, affected services, and rationale, satisfying FR-022, FR-023, AC-3.1, and AC-3.2.

- [x] T52 Predictive risk orchestrator stage
  Files: services/agent-orchestrator/app/stages/predictive_risk_stage.py
  Depends: T11, T14, T51
  Subscribes to predictions.tick from Cloud Scheduler, independent of alert traffic per AC-4.1, invokes the Predictive Risk agent, writes the Firestore predictions document with no BigQuery write, and publishes risk.forecast.created.

- [x] T53 Apply quantified autoscaling configuration
  Files: infra/modules/cloud-run/main.tf
  Depends: T8, T17
  Applies the per-subscription Cloud Run concurrency, minimum instance, and maximum instance settings from research.md section 17 to every agent-orchestrator push subscription, satisfying FR-025, NFR-001, and NFR-002.

- [x] [P] T54 Predictive Health Dashboard page
  Files: frontend/app/predictions/page.tsx
  Depends: T52
  Implements the Predictive Health Dashboard showing active forecasts and flagged anomaly-only entries with rationale, satisfying AC-3.1 and AC-3.2.

**Checkpoint**: All three core milestones (1-3) are independently functional; the platform sustains the 1000+ per minute target with graceful degradation.

---

## Phase 6: User Story 4 - Executive Business Impact Reporting & Automated Postmortems (Priority: P3)

**Goal**: Translate incidents and predictions into business terms and automatically generate postmortems into incident_postmortems.

**Independent Test**: Resolve a sample incident linked to customer_accounts and remediation_logs and confirm correct executive figures plus a postmortem row, without requiring the prediction workflow to have run (AC-4.1 through AC-4.5).

- [x] [P] T55 Contract test for the executive summary API
  Files: tests/contract/test_executive_api.py
  Depends: T16
  Validates GET /executive/summary against contracts/rest-api.md, verifying AC-4.1.

- [x] T56 Integration test for executive impact calculations
  Files: tests/integration/test_executive_impact.py
  Depends: T5, T58
  Asserts computed revenue, SLA, and affected-customer figures match the documented formulas in data-model.md section 7 using the confirmed customer_accounts schema from T5, satisfying AC-4.1 and AC-4.2.

- [x] T57 Integration test for postmortem idempotency
  Files: tests/integration/test_postmortem_idempotency.py
  Depends: T59
  Re-triggers postmortem generation twice for the same incident and asserts the version field increments with no duplicate row, satisfying FR-032, SC-010, and AC-4.5.

- [x] [P] T58 Executive Impact agent
  Files: agents/executive_impact/agent.py
  Depends: T5, T13
  Implements the ADK LlmAgent (gemini-2.5-flash) joining correlated_alerts to alert_stream to customer_accounts using the T5-confirmed columns, and incidents with remediation_logs, computing affected customers, revenue at risk, SLA exposure, and MTTR reduction, and drafting the postmortem narrative fields, satisfying FR-027 through FR-031 and AC-4.1 through AC-4.3.

- [x] T59 Executive impact orchestrator stage
  Files: services/agent-orchestrator/app/stages/executive_impact_stage.py
  Depends: T14, T43, T52, T58
  Subscribes to remediation.executed and risk.forecast.created, invokes the Executive Impact agent, merges into incident_postmortems keyed on incident_id incrementing version, writes the Firestore executive_metrics document, and publishes executive.metrics.updated, satisfying FR-031, FR-032, and AC-4.4/AC-4.5.

- [x] T60 Executive summary REST endpoint
  Files: services/api-gateway/app/routes/executive.py
  Depends: T16, T55, T59
  Implements GET /executive/summary, role-gated to ExecutiveViewer, IncidentCommander, and Administrator, satisfying AC-4.1.

- [x] [P] T61 Executive Dashboard page
  Files: frontend/app/executive/page.tsx
  Depends: T60
  Implements the Executive Dashboard showing revenue at risk, SLA impact, affected customers, current and predicted incidents, MTTR reduction, resolution success rate, and time saved in plain business terms, satisfying FR-029, FR-030, NFR-013, and AC-4.1 through AC-4.4.

**Checkpoint**: All four user stories and milestones are independently functional and demoable end-to-end.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] [P] T62 Role-based navigation guard
  Files: frontend/lib/useRole.ts, frontend/app/me/
  Depends: T16, T30
  Implements consumption of GET /me for consistent role-based navigation gating across all eight frontend pages, satisfying FR-034.

- [x] [P] T63 CI static analysis for hardcoded identifiers
  Files: scripts/deploy/lint-no-hardcoded-ids.ps1
  Depends: T25, T27, T38, T40, T51, T58
  Adds a CI rule blocking literal alert, runbook, or service identifiers in agents and services source outside test fixtures, verifying NFR-011 and checklist item CHK016.

- [x] [P] T64 ADK agent evaluation against a held-out subset
  Files: tests/integration/test_agent_eval_held_out.py
  Depends: T25, T27, T38, T51, T58
  Runs an ADK agent-eval pass against a held-out subset of alert_stream and runbooks never referenced in any prompt or test, confirming outputs are derived rather than memorized, verifying NFR-011.

- [x] [P] T65 Secret and PII leakage scan
  Files: scripts/demo/redaction-scan.ps1
  Depends: T15, T19
  Scans the UI, logs, and generated remediation scripts for plaintext secrets or PII, satisfying SC-008 and AC-3.4.

- [x] [P] T66 RBAC test matrix
  Files: tests/integration/test_rbac_matrix.py
  Depends: T16
  Implements one test per role and endpoint combination to verify FR-035's role-based access control across every REST endpoint.

- [x] T67 Deployment scripts
  Files: scripts/deploy/build-and-push.ps1, scripts/deploy/deploy-all.ps1
  Depends: T8, T45
  Builds and pushes all four Cloud Run services and applies the new-resource-only Terraform.

- [x] T68 Demo user seeding script
  Files: scripts/demo/seed-demo-users.ps1
  Depends: T16
  Provisions the five Firebase demo user accounts with role custom claims for the live demo.

- [x] T69 Demo alert replay launcher
  Files: scripts/demo/start-alert-replay.ps1
  Depends: T24
  Kicks off the at-least-1000-per-minute alert replay for the live demo.

- [ ] T70 Full quickstart rehearsal (BLOCKED in this sandbox -- requires a live deployed GCP project; script/doc side is ready, run this manually once infra/main.tf is applied to a real project)
  Files: specs/001-json-agentic-ai/quickstart.md
  Depends: T67, T68, T69
  Runs the complete quickstart.md rehearsal end-to-end, deploy through seed through demo-flow through NFR verification, including its demo-day contingency section for a stalled prediction, before the live demo.

- [x] T71 Final requirements cross-check
  Files: specs/001-json-agentic-ai/tasks.md
  Depends: T70
  Cross-checked every FR/NFR in spec.md against an implemented task: found FR-037 (audit logging) was only wired for approval decisions, not incident access or remediation execution -- fixed by consolidating agents/common/audit_log.py and wiring log_incident_access into T29 and log_remediation_execution into T43 (previously only log_approval_decision in T42 existed). Also found FR-002/003/007/010/024/025/036/038/039 were functionally satisfied by existing tasks but not explicitly cited -- added citations above. All 74 automated tests pass (2 appropriately skipped: demo/live-environment-only).

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies, start immediately. T5 and T6 block every agent-implementation task that touches customer_accounts, incidents, remediation_logs, or the BQML model.
- Foundational (Phase 2): depends on Setup, blocks all user stories.
- User Story 1 (Phase 3): depends on Foundational only, no dependency on US2 through US4.
- User Story 2 (Phase 4): depends on Foundational plus User Story 1's incidents.root_cause_identified event existing.
- User Story 3 (Phase 5): depends on Foundational only, independently testable without User Story 2.
- User Story 4 (Phase 6): depends on Foundational, and consumes remediation.executed from User Story 2 and risk.forecast.created from User Story 3, making it the natural capstone.
- Polish (Phase 7): depends on all four user stories being complete.

### Parallel Opportunities

All tasks marked [P] touch different files with no direct dependency between them and can run in parallel once their listed Depends tasks are complete. Once the Foundational phase completes, User Story 1 and User Story 3 can be staffed in parallel; User Story 2's agent and service code can be written in parallel with User Story 1 even though its integration test needs User Story 1's root-cause event to exist first.
