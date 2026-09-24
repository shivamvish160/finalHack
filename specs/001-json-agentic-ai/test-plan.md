# Test Plan: SRE Agentic AI Incident Prevention & Resolution Platform

## 1. Scope

**In Scope**:
- All 4 user stories / milestones: Alert Storm Clustering & RCA (US1), Semantic Runbook Retrieval & Approved Remediation (US2), Proactive Predictive Risk Forecasting at Scale (US3), Executive Business Impact Reporting & Automated Postmortems (US4).
- All 6 ADK agents' live-query behavior against the existing BigQuery warehouse (`sre_telemetry`, `sre_topology`, `sre_knowledge_base`, `sre_incident_mart`).
- The human-approval gate, real sandbox remediation execution, and the automated postmortem write path.
- Security controls: RBAC, PII/secret redaction, BigQuery query parameterization, audit logging.
- Non-functional targets: ≥1,000 alerts/minute, graceful degradation, no-hardcoded-logic (NFR-011).
- All 8 frontend pages and the REST/Pub/Sub contracts.

**Out of Scope**:
- Provisioning, seeding, or ETL into the existing BigQuery warehouse (per spec.md Out of Scope — the warehouse is a fixed precondition, never a test subject for creation).
- Executing remediation against real production infrastructure (confined to `demo-target-service`).
- Load/soak testing beyond the ~1,000 alerts/minute demo-scale target (no long-duration production-scale reliability testing).

## 2. Test Strategy

- **Levels**: `contract` (REST/Pub/Sub payload shape), `integration` (multi-component, emulator- or demo-environment-backed), `unit` (single-function/module), `non-functional` (performance, security).
- **Risk priorities**:
  - **P0**: Human-approval gate integrity (NFR-009), BigQuery query parameterization (SQL injection), no-execution-without-approval, warehouse read/write boundary (FR-001/FR-039).
  - **P1**: Alert clustering correctness, root cause quality, runbook retrieval correctness, ≥1,000 alerts/minute sustained throughput, postmortem idempotency.
  - **P2**: Predictive forecasting accuracy/timing, executive impact calculation correctness, RBAC matrix.
  - **P3**: UI navigation/rendering, non-functional polish (redaction canary coverage, dashboard formatting).
- **Entry criteria**: Phase 6 (`tasks.md`) approved; Foundational phase (T1-T19) implemented; live warehouse schema verified (T5).
- **Exit criteria**: All P0/P1 test cases pass; zero remediation executes without a prior approval in any test run; zero SQL injection vector found; ≥1,000 msgs/min sustained with zero DLQ messages in the load test; all 19 ACs and 10 SCs have at least one passing test case.

## 3. Environment & Data

- **Environments**: `dev` (emulated Firestore/Pub/Sub, live read-only BigQuery against the existing warehouse), `demo` (real Cloud Run services, real Pub/Sub, real Cloud Run Admin API against `demo-target-service` — the only environment where T37/real-execution tests run).
- **Test data strategy**: Read-only fixtures derived from the existing warehouse's real rows (`alert_stream`, `network_nodes`, `runbooks`, `customer_accounts`, `incidents`, `remediation_logs`) — no synthetic warehouse seeding. Synthetic *replay* envelopes (fresh `replayEventId`s) are the only new "data" this platform ever produces during tests. A small held-out subset of `alert_stream`/`runbooks` rows is reserved and never referenced in any prompt or fixture, for the NFR-011 agent-eval test (T64).
- **Tooling** (from plan.md): `pytest` for services/agents (mocked GCP clients for unit tests, emulators for integration tests where available), Firestore and Pub/Sub emulators, no BigQuery emulator (a disposable dev dataset view is used instead), Jest/Playwright for the frontend, the ADK agent-eval harness, `terraform validate`/`plan` for infra.

## 4. Story Coverage

### User Story 1 — Alert Storm Clustering & Root Cause Isolation (P1, MVP)
Independently validated by replaying 200+ related `alert_stream` rows and confirming a single incident forms with correlated alerts, timeline, dependency graph, and a root cause with confidence score — without requiring US2/US3/US4 to be present.

### User Story 2 — Semantic Runbook Retrieval & Approved Remediation (P2)
Independently validated by taking an incident with a runbook precedent and confirming a `VECTOR_SEARCH` match, a proposed fix/rollback/risk, and that execution is impossible without an explicit approval — validated with US1 providing the input incident but not requiring US3/US4.

### User Story 3 — Proactive Predictive Risk Forecasting at Scale (P2)
Independently validated by pointing the forecast model at a degrading `alert_stream` trend and confirming a prediction with rationale surfaces before the corresponding alert, plus sustaining ≥1,000 msgs/min — independent of US2/US4.

### User Story 4 — Executive Business Impact Reporting & Automated Postmortems (P3)
Independently validated by resolving a sample incident linked to `customer_accounts`/`remediation_logs` and confirming correct executive figures and a postmortem row — consumes US2's `remediation.executed` and US3's `risk.forecast.created` events but has its own independently-testable calculation/write logic.

## 5. Test Cases

| TC ID | Priority | Level | Story | Requirement/AC Refs | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|---|---|
| TC-001 | P1 | contract | US1 | FR-004 | `alerts.replay` topic exists (T7) | Publish one `alerts.replay` message and inspect the schema | Envelope contains `replayEventId` (UUID), `sourceAlert.alertId`, `occurredAt` distinct from the source row's natural timestamp |
| TC-002 | P1 | integration | US1 | AC-1.1, AC-1.4 | Fixture set of 200+ related + unrelated alerts loaded | Replay the related set and the unrelated set within the same window | Exactly one incident forms for the related set; the unrelated set forms a separate incident (or none), never merged |
| TC-003 | P0 | integration | US1 | FR-005 | Fixture alert with orphaned `node_id` | Replay the fixture alert | The alert is still clustered; the topology relationship is marked `Unmapped`; the alert is never dropped |
| TC-004 | P1 | integration | US1 | AC-1.2 | Incident exists from TC-002 | `GET /incidents/{id}/alerts`, `/timeline`, `/dependency-graph` | Correlated alerts, ordered timeline, and dependency graph are all returned and consistent with the replayed fixture |
| TC-005 | P1 | integration | US1 | AC-1.3 | Incident exists from TC-002 | `GET /incidents/{id}` | Root cause, confidence score, and plain-language reasoning are present and reference supporting alert/topology evidence |
| TC-006 | P2 | integration | US1 | AC-1.5, FR-010 | Incident exists | Transition the incident through its lifecycle | Status is always one of Open/Investigating/Awaiting Approval/Remediating/Resolved/Closed; open vs. resolved are visibly distinguishable |
| TC-007 | P1 | contract | US2 | AC-2.1 | Incident with root cause exists | Trigger runbook retrieval | Response includes `runbookId`, `similarityScore`, `recommendedActions`, derived from `VECTOR_SEARCH`, never a keyword match |
| TC-008 | P2 | integration | US2 | AC-2.5 | Incident with no close runbook precedent | Trigger runbook retrieval | Response sets `belowThreshold=true` rather than presenting a low-confidence guess as authoritative |
| TC-009 | P0 | integration | US2 | NFR-009, AC-2.3 | Proposed remediation exists (Firestore `approvals` = Proposed) | Attempt to invoke the execute tool directly, bypassing `POST /approvals/{id}/decision` | Execution tool call fails/is unreachable; no Cloud Run Admin API call is made |
| TC-010 | P1 | integration | US2 | AC-2.3 | Proposed remediation exists | `POST /approvals/{id}/decision` with `decision=reject` | No execution occurs; incident returns to an actionable state (e.g., `Investigating`) |
| TC-011 | P0 | integration | US2 (demo env only) | AC-2.4, FR-019, FR-020 | Proposed remediation exists; `demo-target-service` deployed | `POST /approvals/{id}/decision` with `decision=approve` | A real (non-mocked) Cloud Run Admin API call executes against `demo-target-service`; outcome is appended to `remediation_logs` |
| TC-012 | P1 | unit | US2 | FR-018 | Approval decision made | Inspect the Firestore `approvals/{id}` document | Approver uid, decision, comments, and timestamp are all recorded |
| TC-013 | P1 | integration | US3 | AC-3.1 | `alert_stream` history contains a known degrading trend fixture | Run the Predictive Risk agent | A forecast is produced with predicted failure, time-to-failure window, confidence, affected services, and rationale, before the corresponding fixture alert is replayed |
| TC-014 | P2 | integration | US3 | AC-3.2 | `alert_stream` values deviate from historical norms | Run the Predictive Risk agent | An anomaly-only entry is flagged even when the full-prediction threshold isn't met |
| TC-015 | P0 | non-functional | US3 | AC-3.3, NFR-001, NFR-002 | `alert-replay-service` deployed with autoscaling config from research.md §17 | Run `scripts/demo/load_test_alerts.py` publishing ≥1,000 msgs/min for 5 minutes | Zero messages land in any `-dlq` topic; all published alerts are accounted for in resulting incident clusters (ties to SC-009) |
| TC-016 | P2 | integration | US3 | NFR-012 | Full pipeline running | Disable the Runbook Retrieval and Predictive Risk agents mid-run | Core alert visibility and correlation (US1) continue functioning uninterrupted |
| TC-017 | P0 | unit | US3/cross-cutting | AC-3.4, NFR-006, NFR-007, SC-008 | Redaction utility deployed (T15) | Feed known secret/PII canary strings through `redaction.py` | All canary values are redacted; surrounding context is preserved |
| TC-018 | P1 | integration | US4 | AC-4.1, AC-4.2 | Incident linked to `customer_accounts` via `service_name` exists | `GET /executive/summary` | Affected-customer count, revenue at risk, and SLA exposure match the documented formulas in data-model.md §7 |
| TC-019 | P1 | integration | US4 | AC-4.3 | One or more incidents resolved through the platform | `GET /executive/summary` | MTTR, resolution success rate, and estimated time saved are displayed, computed against the historical baseline |
| TC-020 | P2 | integration | US4 | AC-4.4 | A prediction exists alongside active incidents | `GET /executive/summary` | Predicted incidents are visually/structurally distinguished from currently active incidents |
| TC-021 | P1 | integration | US4 | AC-4.5, FR-031, FR-032, SC-010 | Incident reaches `Resolved` | Trigger the Executive Impact Agent's postmortem generation twice for the same incident | A postmortem row is written on the first run; the second run increments `version` on the SAME row (no duplicate row) |
| TC-022 | P0 | unit | Cross-cutting | NFR-011 | `bq_client.py` deployed | Attempt a query built via string concatenation/f-string instead of named `@param`s | The client wrapper rejects the call before it reaches BigQuery |
| TC-023 | P1 | integration | Cross-cutting | NFR-011 | Held-out `alert_stream`/`runbooks` subset never referenced in prompts/tests exists | Run the ADK agent-eval harness against the held-out subset | Agent outputs are demonstrably derived from the held-out data (not memorized from training/prompt examples) |
| TC-024 | P2 | integration | Cross-cutting | FR-035 | 5 Firebase roles seeded | Call every REST endpoint with each of the 5 roles | Each endpoint enforces its documented role restriction (403 for disallowed roles) |
| TC-025 | P2 | integration | Cross-cutting | FR-037 | Any security-relevant action performed (incident access, approval decision, execution) | Inspect Cloud Logging | A structured audit entry exists with actor, timestamp, and action |
| TC-026 | P3 | e2e | US1-US4 | FR-033, FR-034 | Full stack deployed | Navigate from the Live Incident Console through Timeline, Correlation, Root Cause, Runbook, Approval, Predictive, and Executive pages for one incident | Incident identity is preserved consistently across all 8 pages; no page errors |
| TC-027 | P1 | contract | US1/US2/US3/US4 | contracts/pubsub-events.md | All topics provisioned (T7) | Publish/consume one message per topic | Payload shape matches the documented schema for every topic in the chain |
| TC-028 | P2 | integration | Cross-cutting | FR-001, FR-039 | Full stack deployed | Run a Terraform plan diff against the existing warehouse's datasets | Zero changes are proposed to `sre_telemetry`, `sre_topology`, `sre_knowledge_base`, `sre_incident_mart`'s 5 read-only tables |

## 6. Regression Set

Minimum must-run suite before any release/demo rehearsal (all P0 + P1 cases): **TC-001 through TC-005, TC-007, TC-009 through TC-013, TC-015, TC-017 through TC-019, TC-021 through TC-023, TC-027, TC-028**. This set covers: the approval gate (P0), warehouse read/write boundaries (P0), SQL parameterization (P0), the ≥1,000/min throughput target (P0), and every user story's headline capability (P1).

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `VECTOR_SEARCH` ranking quality is unproven at the ~20-row `runbooks` corpus scale (design.md §11 risk #1) | TC-007/TC-008 explicitly validate both the match and below-threshold paths; tune the similarity threshold during quickstart rehearsal (T70) |
| BQML retrain cadence was unfixed as of the Tasks phase (checklist CHK034) | T6 fixes a concrete cadence before any agent code is written; TC-013 validates the prediction fires ahead of the fixture alert using that cadence |
| `customer_accounts`/`incidents`/`remediation_logs` columns are placeholders pending live-schema verification | T5 (blocking) resolves this before TC-018/TC-019/TC-021 can be considered valid; those test cases must be re-run if T5 changes the assumed column names |
| Real sandbox execution (TC-011) requires a live demo environment, not available in CI | TC-011 is scoped to the `demo` environment only; TC-009/TC-010 (the gate itself) run in `dev` with mocks |

## 8. Traceability Matrix

| Spec Item | Test Case(s) | Task(s) |
|---|---|---|
| US1 / AC-1.1–1.5 | TC-002 through TC-006 | T20-T23, T26, T28 |
| US2 / AC-2.1–2.5 | TC-007 through TC-012 | T34-T37, T39, T41-T44 |
| US3 / AC-3.1–3.4 | TC-013 through TC-017 | T48-T50, T52 |
| US4 / AC-4.1–4.5 | TC-018 through TC-021 | T55-T57, T59 |
| NFR-001/002 (scale) | TC-015 | T49, T53 |
| NFR-006/007 (PII/secrets) | TC-017 | T15, T19, T65 |
| NFR-009 (approval gate) | TC-009, TC-010 | T36, T42-T44 |
| NFR-011 (no hardcoded logic) | TC-022, TC-023 | T18, T63, T64 |
| NFR-012 (graceful degradation) | TC-016 | T50 |
| FR-001/FR-039 (warehouse boundary) | TC-028 | T5, T71 |
| FR-033/034 (UI) | TC-026 | T30-T33, T46, T47, T54, T61, T62 |
| FR-035 (RBAC) | TC-024 | T16, T66 |
| FR-037 (audit logging) | TC-025 | T29, T42 |
| SC-001–SC-010 | SC-001→TC-002; SC-002→TC-005; SC-003→TC-007; SC-004→TC-009/TC-011; SC-005→TC-013; SC-006→TC-018; SC-007→TC-019; SC-008→TC-017; SC-009→TC-015; SC-010→TC-021 | (see mapped tasks above) |

No unmapped user story, FR/NFR, or task phase remains — every task phase in tasks.md (Setup, Foundational, US1-US4, Polish) is represented in this test plan's coverage.
