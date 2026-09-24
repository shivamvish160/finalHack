# Design & Architecture Checklist: SRE Agentic AI Incident Prevention & Resolution Platform

**Purpose**: Validate the completeness, clarity, consistency, measurability, and coverage of this feature's design/architecture documentation (plan.md, design.md, data-model.md, contracts/) — covering mandatory GCP service usage, the no-hardcoded-logic constraint, the 6 ADK agents, the 4 hackathon milestones, the 8 UI pages, security controls, and the end-to-end demo scenario — before implementation (`/audi.tasks` / `/audi.implement`) begins.
**Created**: 2026-09-24 (regenerated for the existing-warehouse premise; supersedes the prior JSON-upload/ETL-era checklist)
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [design.md](../design.md) | [data-model.md](../data-model.md) | [contracts/rest-api.md](../contracts/rest-api.md) | [contracts/pubsub-events.md](../contracts/pubsub-events.md)

**Note**: Every item below has been evaluated against the CURRENT (existing-warehouse) artifacts and marked **PASS**, **FAIL**, or **N/A**. Several items that FAILed against the prior (ingestion-era) version of these artifacts have since been resolved by the regenerated plan.md/design.md; those are called out explicitly.

**Status Legend**:
- `[x]` + **PASS** — the current artifacts satisfy this requirement-quality bar.
- `[ ]` + **FAIL** — a gap, ambiguity, inconsistency, or unmeasurable requirement was found; needs a follow-up before/during implementation.
- `[x]` + **N/A** — out of scope for this checklist/phase; not a defect.

---

## Mandatory GCP Service Coverage

- [x] CHK001 Is BigQuery's role as the pre-existing, read-mostly system of record explicitly and consistently specified (not re-provisioned)? **PASS** — spec.md FR-001, plan.md Technical Context/Constraints, and design.md §1 all agree the warehouse already exists and is never re-provisioned.
- [x] CHK002 Is BigQuery Vector Search specified precisely enough to confirm retrieval is embeddings-only, reusing the EXISTING `runbooks.embedding` (not a new embedding pipeline)? **PASS** — data-model.md §4 and design.md §3.2/§8 specify `VECTOR_SEARCH` over the existing 768-dim column, with only query text embedded at retrieval time via `AI.GENERATE_EMBEDDING`.
- [x] CHK003 Is BigQuery ML's forecasting/anomaly responsibility (model, functions, dataset ownership) unambiguously documented? **PASS** — `sre_ml_ops.alert_trend_forecast_model` (`ARIMA_PLUS`) + `ML.FORECAST`/`ML.DETECT_ANOMALIES`/`ML.EXPLAIN_FORECAST`, documented in plan.md, data-model.md §5, design.md §3.2/§8.
- [x] CHK004 Is Cloud Storage correctly scoped OUT of this feature (no JSON landing/ingestion) rather than silently reintroduced? **PASS** — plan.md/design.md/spec.md Out of Scope all explicitly exclude Cloud Storage/ingestion; no artifact references a landing bucket.
- [x] CHK005 Are all four Cloud Run services (`alert-replay-service`, `agent-orchestrator`, `api-gateway`, `demo-target-service`) each given a distinct, non-overlapping responsibility? **PASS** — design.md §3.1 and plan.md Project Structure agree on 4 services with distinct responsibilities.
- [x] CHK006 Is the Gemini model choice (which model, per agent, rationale, configurability) documented rather than silently hardcoded? **PASS** — research.md/design.md §8 document `gemini-2.5-flash`/`gemini-2.5-pro`, rationale, and note the model ID is env/Terraform-configurable.
- [x] CHK007 Is ADK usage specified at the concrete API-surface level (`LlmAgent`/`Runner`) rather than only named as a checkbox technology? **PASS** — design.md §3.2, plan.md Summary/Primary Dependencies specify `LlmAgent` + `Runner.run_async`, with sourced rationale against deprecated `SequentialAgent`/`ParallelAgent`/`LoopAgent`.
- [x] CHK008 Are all Pub/Sub topics, producers/consumers, and DLQ behavior fully enumerated in one authoritative contract? **PASS** — contracts/pubsub-events.md enumerates every topic + envelope schema; design.md §3.3 summarizes consistently.
- [x] CHK009 Is Cloud Scheduler's role (which jobs, why independent of alert traffic) clearly distinguished from the Pub/Sub alert-replay path? **PASS** — design.md §2/§3.2 and plan.md explicitly state `predictions.tick`/retrain jobs are Scheduler-driven, independent of alert arrival (AC-4.1).
- [x] CHK010 Is Cloud Logging's scope kept distinct from Cloud Audit Logs, so "audit" and "operational logging" aren't conflated? **PASS** — design.md §7.4 names and separates operational Cloud Logging vs. GCP-native Cloud Audit Logs; no separate BigQuery audit table is invented (per FR-039 constraint).
- [x] CHK011 Is Secret Manager's actual secret inventory specified precisely (what is/isn't a secret)? **PASS** — design.md §7.2 lists concrete items and explicitly excludes the public Firebase Web client config.
- [x] CHK012 Is IAM specified at the least-privilege, per-service-account, resource-scoped level rather than a single broad project role? **PASS** — design.md §7.1 table gives per-service SAs with dataset/resource-scoped roles (e.g., `run.developer` scoped only to `demo-target-service`).
- [x] CHK013 Is every mandatory service (BigQuery, Vector Search, BQML, Cloud Run, Vertex AI/Gemini, ADK, Pub/Sub, Cloud Scheduler, Cloud Logging, Secret Manager, IAM) traceable to at least one FR/NFR and one design section? **PASS** — cross-checked design.md §2 table and plan.md Technical Context against spec.md FR-001–FR-039; all 11 services trace to at least one requirement.
- [x] CHK014 Is it explicit that this feature writes to exactly 4 BigQuery tables and never invents new ones for platform-internal state? **PASS** — FR-039 + plan.md "Key architectural call" + design.md §8 all state writes are confined to `correlated_alerts`/`incidents`/`remediation_logs`/`incident_postmortems`; all other state lives in Firestore/Cloud Logging.

## No-Hardcoded-Logic Requirement (NFR-011)

- [x] CHK015 Is "no hardcoded mappings/static logic" stated as a testable requirement, not just aspirational prose? **PASS** — NFR-011 in spec.md is a discrete, numbered requirement.
- [x] CHK016 Does a verification/test method exist for NFR-011, distinct from generic code review? **PASS (previously FAIL)** — plan.md's Testing & Verification Strategy table now has an explicit NFR-011 row: CI static check blocking literal alert/runbook/service identifiers in agent source, plus an ADK agent-eval run against a held-out warehouse subset never referenced in any prompt/test.
- [x] CHK017 Are all 6 agents' outputs traced to a live query rather than a static table/dict in code? **PASS** — plan.md's "Agent-to-Warehouse Query Patterns" table and data-model.md §2–§7 show every agent's output derived from a live, parameterized BigQuery/BQML/Vector-Search call.
- [x] CHK018 Is SQL injection risk (string-concatenated queries) explicitly ruled out? **PASS (previously FAIL)** — research.md §18 + plan.md Constraints + Testing table mandate named `@param`s everywhere and a CI lint rule rejecting f-string/`.format()`/`+`-concatenated SQL.
- [x] CHK019 Is there a fallback behavior defined for low-confidence/no-match cases so the system doesn't fabricate an answer? **PASS** — FR-014/AC-2.5 (`belowThreshold`) and AC-3.x cold-start handling in spec.md Edge Cases.

## 6 ADK Agents — Responsibilities & Outputs (against real existing tables)

- [x] CHK020 Agent 1 (Alert Correlation): output (single incident from many alerts) and warehouse writes (`correlated_alerts`, `incidents`) explicitly specified? **PASS** — FR-006/FR-007, design.md §3.2 row 1.
- [x] CHK021 Agent 2 (Root Cause Analysis): output (root cause, confidence, reasoning) and read join path specified? **PASS** — FR-009, design.md §3.2 row 2.
- [x] CHK022 Agent 3 (Runbook Retrieval): output (matched SOP, similarity score, recommended actions) and embeddings-only constraint specified? **PASS** — FR-012/FR-013/FR-014, design.md §3.2 row 3.
- [x] CHK023 Agent 4 (Predictive Risk): output (predicted outage, time-to-failure, confidence, affected services) and BQML model specified? **PASS** — FR-022, design.md §3.2 row 4.
- [x] CHK024 Agent 5 (Remediation): output (safe fix, rollback, risk assessment) and approval-gated execution specified? **PASS** — FR-015–FR-021, design.md §3.2 row 5 + §3.4/§8 (physically separate propose/execute tools).
- [x] CHK025 Agent 6 (Executive Impact): output (users impacted, revenue at risk, SLA credits, MTTR reduction) AND postmortem generation specified? **PASS** — FR-027–FR-032, design.md §3.2 row 6.
- [x] CHK026 Is the orchestration pattern across all 6 agents (sequencing, hand-off events) fully specified rather than left to the LLM's discretion? **PASS** — design.md §3.2/§3.3, contracts/pubsub-events.md topic chain.
- [x] CHK027 Is each agent's model choice justified individually (not a single blanket model for all 6)? **PASS** — design.md §3.2 table specifies `gemini-2.5-pro` for RCA vs. `gemini-2.5-flash` elsewhere, with rationale in research.md.
- [x] CHK028 Is it explicit which agents are READ-ONLY against the warehouse vs. which WRITE, and to which exact tables? **PASS** — design.md §3.2 "Writes" column + FR-039.

## 4 Milestones

- [x] CHK029 Milestone 1 (Alert Clustering & RCA): root cause, correlated alerts, timeline, related services, dependency graph, confidence score all present in requirements/contracts? **PASS** — FR-006–FR-011, AC-1.x, contracts/rest-api.md incident endpoints.
- [x] CHK030 Milestone 2 (Runbook Retrieval & Safe Remediation): semantic retrieval, step-by-step fix, rollback, risk level, human approval gate all present? **PASS** — FR-012–FR-021, AC-2.x.
- [x] CHK031 Milestone 3 (Resilience & Predictive Forecasting): ≥1,000 alerts/min via Pub/Sub + Cloud Run autoscaling, WHY-explained predictions, anomaly detection, secret/PII redaction all present? **PASS** — FR-022–FR-026, NFR-001/002, AC-3.x.
- [x] CHK032 Is the ≥1,000 alerts/minute target backed by a QUANTIFIED autoscaling configuration (not just "autoscaling enabled")? **PASS (previously FAIL)** — research.md §17 gives a concrete per-subscription concurrency/min/max-instance table with throughput math.
- [x] CHK033 Milestone 4 (Executive Dashboard): revenue at risk, SLA impact, affected customers, current/predicted incidents, MTTR reduction, resolution success rate, time saved, business impact all present? **PASS** — FR-027–FR-030, AC-4.x, contracts/rest-api.md `/executive/summary`.
- [x] CHK034 Is the BQML retrain cadence for the Predictive Risk milestone fixed to a concrete numeric value (so a prediction can reliably fire before the demo's corresponding alert per AC-4.1)? **PASS (previously FAIL, fixed during Implement/T6)** — research.md §6 and `infra/environments/demo/terraform.tfvars` now fix a concrete `*/15 * * * *` retrain cadence and a `*/2 * * * *` `predictions.tick` cadence, both inside a single demo replay window.
- [x] CHK035 Is there a demo-day contingency if a live prediction doesn't fire in time (e.g., a pre-validated fixture window)? **PASS** — quickstart.md is documented (per plan.md summary) to include an explicit demo-day contingency section for exactly this risk.

## 8 UI Pages

- [x] CHK036 Live Incident Console specified with a concrete data source (contract endpoint / Firestore listener)? **PASS** — contracts/rest-api.md `/incidents`, design.md §6, Firestore realtime note.
- [x] CHK037 Incident Timeline specified (merged alert + stage-history source)? **PASS** — contracts/rest-api.md `/incidents/{id}/timeline`.
- [x] CHK038 Alert Correlation View specified (correlated alerts + Mapped/Unmapped flag)? **PASS** — contracts/rest-api.md `/incidents/{id}/alerts`.
- [x] CHK039 Root Cause Analysis View specified (root cause, confidence, reasoning)? **PASS** — `/incidents/{id}` full detail.
- [x] CHK040 Runbook Recommendation View specified (similarity score, belowThreshold handling)? **PASS** — `/incidents/{id}/runbook-matches`.
- [x] CHK041 Approval Console specified (pending queue + decision endpoint, RBAC-scoped)? **PASS** — `/approvals?status=pending`, `/approvals/{id}/decision`.
- [x] CHK042 Predictive Health Dashboard specified (active forecasts + anomaly-only entries)? **PASS** — `/predictions`, `/predictions/anomalies`.
- [x] CHK043 Executive Dashboard specified (business-impact snapshot, role-gated)? **PASS** — `/executive/summary`.
- [x] CHK044 Is consistent incident identity preserved across all 8 pages (single ID threaded through navigation)? **PASS** — FR-034, contracts/rest-api.md uses `incidentId` uniformly.
- [x] CHK045 Is the frontend framework/stack choice (Next.js, Firebase JS SDK) documented with rationale? **PASS** — design.md §8 Technology Decisions.
- [x] CHK046 Is realtime vs. on-demand data-fetch strategy per page explicitly decided (not left ambiguous)? **PASS** — contracts/rest-api.md intro: Firestore realtime listener for live state, REST for BQ-backed drill-downs.
- [x] CHK047 Is role-based navigation gating (which roles see which pages) specified? **PASS** — FR-035, `/me` endpoint, per-endpoint Roles column in contracts/rest-api.md.

## Security Controls

- [x] CHK048 IAM least-privilege table present and resource-scoped (not project-wide roles)? **PASS** — design.md §7.1.
- [x] CHK049 RBAC roles (5 named roles) and their claims-based enforcement mechanism specified? **PASS** — FR-035, design.md §7.1.
- [x] CHK050 Secret Manager inventory and mounting mechanism (secret volume, no baked-in secrets) specified? **PASS** — design.md §7.2.
- [x] CHK051 Data masking / PII redaction: enforcement POINT(S) in the pipeline explicitly located? **PASS** — design.md §7.3 (read/output time on every free-text field).
- [x] CHK052 Credential filtering: explicit rule that no secret ever appears in a generated remediation/rollback script? **PASS** — NFR-006, design.md §7.3.
- [x] CHK053 Audit logging: 3-layer model (Cloud Logging security events / operational logs / Cloud Audit Logs) explicitly separated? **PASS** — design.md §7.4.
- [x] CHK054 Is every security-relevant action (incident access, approval decision, remediation execution) traced to a specific logging call? **PASS** — FR-037, design.md §7.4 item 1.
- [x] CHK055 Is the human-approval gate structurally enforced (separate propose/execute code paths), not just a prompt instruction? **PASS** — NFR-009, design.md §3.1/§8 ("physically separate propose vs. execute tools").
- [x] CHK056 Is the sandbox execution target's isolation (no prod access, restricted SA) explicit? **PASS** — design.md §7.1 (`demo-target-service` row, invocable only by orchestrator SA).
- [x] CHK057 Is BigQuery query parameterization (anti-SQL-injection) an explicit, testable requirement? **PASS (previously FAIL)** — research.md §18, plan.md Testing table.

## Demo Scenario End-to-End

- [x] CHK058 Is the ~1,000 alerts/minute arrival mechanism concretely specified as a REPLAY of existing `alert_stream` (not new external data)? **PASS** — FR-004, design.md §3.1/§4, replay envelope with fresh `replayEventId`.
- [x] CHK059 Does the demo flow show clustering → RCA → SOP retrieval → prediction → fix generation → approval → sandbox execution → dashboard update, in one authoritative sequence? **PASS** — design.md §4 sequence diagram; spec.md "Primary Demonstration Flow".
- [x] CHK060 Is postmortem generation included as the closing step of the demo flow? **PASS** — design.md §4 (MERGE into `incident_postmortems`), spec.md AC-4.5/Primary Demonstration Flow step 9.
- [x] CHK061 Is the approval step demonstrably blocking (execution cannot proceed without it) in the demo's own described flow, not just in the requirements? **PASS** — design.md §4 sequence diagram shows execution strictly gated behind `remediation.approved`.
- [x] CHK062 Is there a rehearsal/validation step (quickstart) that exercises the full flow before the live demo? **PASS** — quickstart.md per plan.md summary (deploy → seed → demo-flow → NFR-verification walkthrough).
- [x] CHK063 Does the demo scenario avoid any manual data-loading step (consistent with the existing-warehouse premise)? **PASS** — no upload/ETL step anywhere in spec.md Primary Demonstration Flow or design.md §4.
- [x] CHK064 Is graceful degradation demonstrated/tested if one agent (e.g., Predictive Risk) is unavailable mid-demo? **PASS** — NFR-012, plan.md Testing table "chaos test disabling Agent 3/4 mid-demo".
- [x] CHK065 Is the redaction requirement (secrets/PII) exercised somewhere in the demo/test flow, not just stated as a requirement? **PASS** — plan.md Testing table "redaction unit tests with known secret/PII canaries", NFR-007/AC-3.4.

## Cross-Cutting Traceability & Governance

- [x] CHK066 Does every FR/NFR in spec.md trace to at least one plan.md/design.md section? **PASS** — spot-checked FR-001–FR-039 and NFR-001–NFR-013 against plan.md's Agent-to-Warehouse table, Testing table, and design.md §3/§7/§10; no orphaned requirement found.
- [x] CHK067 Are all "assumed pending live-schema verification" fields (e.g., `customer_accounts`, `incidents`, `remediation_logs` columns) flagged consistently across spec/data-model rather than silently treated as confirmed? **PASS** — spec.md Assumptions + data-model.md §1 both explicitly flag these as illustrative/pending `INFORMATION_SCHEMA.COLUMNS` verification.
- [x] CHK068 Is the Firestore-vs-"optional" contradiction between the original source brief and the actual architecture resolved? **PASS (previously FAIL, fixed this pass)** — spec.md Assumptions now explicitly states Firestore is required by this feature's architecture (Looker Studio remains the only truly optional service).
- [x] CHK069 Is there a ratified constitution to check design decisions against? **N/A** — `.audi/memory/constitution.md` is unratified; plan.md/design.md both correctly record this as N/A, not a gate failure.
- [x] CHK070 Is the "no new BigQuery tables for platform-internal state" rule consistently applied across data-model.md, design.md, and contracts (no accidental extra table introduced anywhere)? **PASS** — cross-checked; all non-FR-039 state (approvals, predictions, executive metrics, pending-alerts window) is Firestore-only in every artifact.
- [x] CHK071 Are Terraform/infra scope boundaries explicit (new resources only, never the existing warehouse's datasets/tables)? **PASS** — plan.md Project Structure `infra/` section and Constraints line state this explicitly.
- [x] CHK072 Is a concrete owner/next-step assigned to every still-open risk (§11 of design.md)? **PASS** — all 4 open risks in design.md §11 have an explicit Resolution and Owner column.

---

## Summary

**72 items evaluated** (CHK001–CHK072): **71 PASS**, **0 FAIL**, **1 N/A** (CHK069, constitution unratified).

Compared to the prior (ingestion-era) checklist's 53 PASS / 18 FAIL / 1 N/A, regenerating plan.md/design.md against the existing-warehouse premise resolved 17 of the 18 previously-flagged gaps outright (verification path for NFR-011, quantified autoscaling, BigQuery parameterization, and all ingestion/ETL/GCS-specific items that no longer apply), this pass additionally fixed the Firestore-optional contradiction (CHK068) directly in spec.md, and the Implement phase (T6) fixed the final remaining gap (CHK034, BQML retrain cadence).
