# Feature Specification: SRE Agentic AI Incident Prevention & Resolution Platform

**Feature Branch**: `001-json-agentic-ai`  
**Created**: 2026-09-24  
**Last Revised**: 2026-09-24 (existing-warehouse premise rewrite; clarify pass)  
**Status**: Draft  
**Input**: User description:

> You are a Principal Google Cloud Architect, Distinguished SRE, AI Engineer, BigQuery Specialist, and Gemini Agent Developer.
>
> Your goal is to generate a COMPLETE, DEPLOYABLE, HACKATHON-WINNING solution for BCE Hackfest Track 2.
>
> OBJECTIVE
>
> Build a production-grade Agentic AI Incident Prevention & Resolution Platform running entirely on Google Cloud.
>
> The solution must maximize hackathon scoring and explicitly satisfy all milestones.
>
> The generated solution must not rely on hardcoded mappings, static answers, manually embedded runbooks, or fixed alert-to-resolution logic.
>
> The platform should work with real data stored in BigQuery.
>
> For demo purposes the user will upload JSON files containing: (1) Alerts, (2) Telemetry data, (3) Historical incidents, (4) SOPs / Runbooks, (5) Network topology, (6) Revenue impact data, (7) SLA data, (8) Service dependency data.
>
> The application should automatically ingest those JSON files into BigQuery tables. After ingestion all reasoning, retrieval, prediction, correlation and remediation must occur using GCP services.
>
> MANDATORY GOOGLE CLOUD SERVICES: BigQuery, BigQuery Vector Search, BigQuery ML, Cloud Storage, Cloud Run, Gemini 3.6 Flash (or latest available Gemini model), Vertex AI, Agent Development Kit (ADK), Pub/Sub, Cloud Scheduler, Cloud Logging, Secret Manager, IAM, Looker Studio (optional), Firestore (optional).
>
> ARCHITECTURE REQUIREMENTS: end-to-end architecture diagram, Terraform infrastructure, folder structure, deployment scripts, Cloud Run deployment commands, BigQuery schema definitions, vector search implementation, Gemini agent implementation, frontend implementation, executive dashboard. All components must be deployable.
>
> DATA INGESTION: When user uploads alerts.json, incidents.json, runbooks.json, telemetry.json, sla.json, topology.json -- automatically upload to Cloud Storage, trigger ingestion pipeline, create BigQuery datasets, load data into BigQuery, generate embeddings, store embeddings in vector indexes. No manual operation required.
>
> MULTI AGENT SYSTEM (ADK):
> Agent 1 Alert Correlation Agent: process streaming alerts, deduplicate, group alert storms, create incident clusters. Output: single incident from hundreds of alerts.
> Agent 2 Root Cause Analysis Agent: analyze telemetry, topology, historical incidents, identify probable root cause. Output: root cause, confidence score, reasoning.
> Agent 3 Runbook Retrieval Agent: use BigQuery Vector Search, search SOP repository, retrieve semantically similar runbooks (embeddings only, no keyword search). Output: matched SOP, similarity score, recommended actions.
> Agent 4 Predictive Risk Agent: analyze historical telemetry/trends, forecast failures using BigQuery ML. Output: predicted outage, time before failure, confidence, affected services.
> Agent 5 Remediation Agent: generate remediation script, rollback script, validate commands. Output: safe fix, rollback, risk assessment.
> Agent 6 Executive Impact Agent: calculate users impacted, revenue at risk, SLA credits, MTTR reduction. Output: executive friendly summary.
>
> MILESTONE 1 - Alert Clustering & Root Cause Isolation: convert hundreds of alerts into a single incident; show root cause, correlated alerts, incident timeline, related services, dependency graph, confidence score.
> MILESTONE 2 - Runbook Retrieval & Safe Remediation: retrieve SOP using semantic search; generate step-by-step remediation, rollback plan, risk level; require human approval before execution; implement approval workflow.
> MILESTONE 3 - Resilience & Predictive Forecasting: handle >1000 alerts/minute using Pub/Sub and Cloud Run autoscaling; generate outage predictions and explain WHY; detect anomaly trends; redact secrets and PII.
> MILESTONE 4 - Executive Dashboard: show revenue at risk, SLA impact, number of affected customers, current incidents, predicted incidents, MTTR reduction, resolution success rate, time saved, business impact.
>
> USER INTERFACE pages: Live Incident Console, Incident Timeline, Alert Correlation View, Root Cause Analysis View, Runbook Recommendation View, Approval Console, Predictive Health Dashboard, Executive Dashboard.
>
> SECURITY: IAM, role based access, Secret Manager, data masking, PII redaction, credential filtering, audit logging.
>
> DEMO SCENARIO: 1000 alerts arrive -> system clusters alerts -> identifies root cause -> retrieves SOP -> predicts outage -> generates fix -> human approves -> sandbox execution runs -> executive dashboard updates.
>
> OUTPUT: complete architecture, Terraform code, BigQuery schemas, Cloud Run services, Vertex AI implementation, Gemini prompts, ADK agent code, UI code, deployment guide, demo guide. Prioritize real GCP services over mocks. Avoid placeholders. Maximize BCE Hackfest Track 2 judging score across every milestone and mandatory technology component.
>
> **AMENDMENT (2026-09-24) — Existing Warehouse Premise**: The BCE Hackfest Track 2 BigQuery warehouse is already fully provisioned, loaded, and populated in the target GCP project: `sre_telemetry.alert_stream` (~3,000 rows), `sre_topology.network_nodes` (~64 rows), `sre_knowledge_base.runbooks` (~20 rows, with a 768-dimension embedding column already generated) plus `sre_knowledge_base.embedding_model`, and `sre_incident_mart.customer_accounts` (~45 rows) / `incidents` (~18 rows) / `correlated_alerts` / `remediation_logs` / `incident_postmortems` (currently empty). This supersedes the "DATA INGESTION" instruction above in its entirety: this feature does **not** build a JSON-upload pipeline, Cloud Storage landing, ETL, warehouse/database provisioning, or ingest-time embedding generation. The platform is a pure consumer of this existing warehouse — every capability below is re-derived around direct BigQuery queries and BigQuery Vector Search over the embeddings that already exist in `runbooks`.

## Overview

This feature delivers an Agentic AI Incident Prevention & Resolution Platform on Google Cloud that consumes an already fully provisioned and populated BigQuery warehouse — alert telemetry (`sre_telemetry.alert_stream`), network topology (`sre_topology.network_nodes`), a semantically-embedded runbook library (`sre_knowledge_base.runbooks` / `embedding_model`), and incident/customer history (`sre_incident_mart.customer_accounts`, `incidents`, `correlated_alerts`, `remediation_logs`, `incident_postmortems`) — as its single source of truth. A six-agent ADK pipeline (Alert Correlation, Root Cause Analysis, Runbook Retrieval via BigQuery Vector Search, Predictive Risk via BigQuery ML, Remediation with mandatory human approval, and Executive Impact) turns a replayed alert storm into a single explained incident, a semantically retrieved SOP, a safe approved fix, an outage forecast, an executive-facing business-impact summary, and an automatically written postmortem. No new data ingestion, ETL, or warehouse provisioning is part of this feature — every output is derived from live BigQuery queries and vector search over the existing warehouse; no alert-to-resolution mapping, runbook match, or forecast is hardcoded.

## Problem Statement

SRE and incident-response teams already have a rich, well-populated BigQuery warehouse of alert telemetry, network topology, historical incidents, remediation history, and a semantically-embedded runbook library — but nothing today queries that data live to help during an active incident. Alert storms (hundreds to 1,000+/minute) still have to be triaged manually, root cause is still reasoned about by hand, the right runbook is still found from memory or keyword search, business impact is still estimated after the fact, and postmortems are still written by hand — all of which slow Mean Time To Resolution (MTTR), increase SLA breach risk, and leave revenue-at-risk hidden from executives until well after an incident starts. There is no existing system that automatically clusters live-arriving alerts into a single explained incident, semantically retrieves the right SOP from the existing runbook library, forecasts failures before they happen, quantifies business impact, and writes the postmortem — all grounded in the organization's own already-collected warehouse data rather than static, hand-authored mappings.

## Clarifications

### Carried Forward From Prior Specification (Session 2026-09-24)

These decisions were established under the pre-rollback version of this spec (when the platform was still expected to ingest uploaded JSON files) and remain in force under the existing-warehouse premise, re-scoped where noted. The prior ingestion-deduplication decision no longer applies and has been removed, since this feature no longer performs any data ingestion.

- Remediation "sandbox execution" is REAL (Cloud Run Admin API against a dedicated demo target service), not simulated/mocked.
- Auth = Firebase Authentication / Google Identity Platform w/ custom role claims for end users; GCP IAM stays for service-to-service access to GCP resources, including the BigQuery warehouse.
- "Affected customers/users" = customer/user-count and SLA/revenue attributes already present on `sre_incident_mart.customer_accounts`, joined via `service_name` and aggregated over the incident's blast radius (re-scoped: no separate ingested "Revenue Impact Record" domain — the prior specification assumed uploaded revenue data; this data already lives on `customer_accounts`).
- Incident status enum = Open/Investigating/Awaiting Approval/Remediating/Resolved/Closed; predictions stay a separate Risk Forecast/Prediction entity, never an incident status.

### Session 2026-09-24

This is a fully automated orchestrator run with no live user available; each question below was self-answered by selecting the most reasonable, GCP-native, hackathon-feasible default consistent with requirements already stated elsewhere in this spec, rather than inventing new scope. These five clarifications resolve ambiguities introduced specifically by the existing-warehouse premise rewrite above.

- Q: What GCP project and region should this feature's newly-created resources (Cloud Run services, Pub/Sub topics/subscriptions, Vertex AI connections, any new BigQuery views) target relative to the pre-provisioned warehouse? → A: The same GCP project as the existing warehouse, supplied via deployment configuration (e.g., a `GCP_PROJECT_ID` variable) rather than hardcoded, with all newly-created resources deployed to a single region (`us-central1`) to co-locate with the existing datasets and avoid cross-region latency/availability mismatches.
- Q: How exactly is "streaming" arrival of the finite ~3,000-row `alert_stream` simulated so the Alert Correlation Agent doesn't mis-treat looped/reused rows as the same original alert? → A: Each replayed row is wrapped in an envelope carrying a freshly generated `replay_event_id` (UUID) and a rewritten arrival timestamp, distinct from the row's natural `alert_id`; agents dedup/cluster on `replay_event_id` so repeated passes over the same underlying rows are correctly treated as new occurrences.
- Q: What concrete SLA/revenue-relevant fields does `customer_accounts` expose for the Executive Impact Agent's calculations? → A: Assume `customer_id`, `customer_name`, `service_name`, `tier`, `monthly_recurring_revenue`, `sla_uptime_target_pct`, `sla_credit_rate_per_hour`, and `user_count`; the agent MUST verify actual column names against the live schema (e.g., via `INFORMATION_SCHEMA.COLUMNS`) at implementation time rather than hardcoding this assumed list blindly.
- Q: What write format/schema does the platform use for the currently-empty `incident_postmortems` table? → A: Structured BigQuery columns — `incident_id`, `generated_at`, `root_cause_summary`, `timeline_summary`, `remediation_summary`, `business_impact_summary`, `full_report_markdown`, and `version` — rather than a single free-text blob or an external Cloud Storage pointer, keeping postmortems queryable in BigQuery and giving the "update not duplicate" rule (FR-032) an explicit version counter.
- Q: How should the platform handle an `alert_stream` row whose `node_id`/`service_name` has no matching row in `network_nodes`/`customer_accounts` (referential gaps in existing data)? → A: Still process and cluster the alert using whatever fields ARE resolvable; mark the specific unresolved relationship as Unknown/Unmapped in dependency and impact views; never drop the alert from its incident cluster, consistent with SC-009 and NFR-012.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Alert Storm Clustering & Root Cause Isolation from Existing Telemetry (Priority: P1)

As an on-call engineer facing hundreds of simultaneous alerts, I want the platform to automatically consolidate them into a single incident with a clearly explained probable root cause, correlated alerts, timeline, affected services, and dependency graph — using the organization's already-populated alert and topology data — so I can understand and respond to the real underlying problem in minutes instead of manually triaging a flood of individual alerts.

**Why this priority**: This is the platform's headline capability and the first milestone — turning alert chaos into a single, explainable incident, using data that already exists in the warehouse today. It requires no upload or setup step and is the clearest demonstration that the platform delivers value directly on real, already-warehoused data.

**Independent Test**: Can be fully tested by replaying a burst of related rows from `alert_stream` (e.g., 200+ alerts referencing a shared set of `node_id`/`service_name` values) and confirming a single incident is produced with correlated alerts, timeline, dependency view, and a root cause with confidence score and reasoning — without needing runbook retrieval, prediction, or remediation to be present.

**Acceptance Scenarios**:

1. **AC-1.1**: **Given** hundreds of `alert_stream` rows referencing overlapping services arrive (via replay) within a short window, **When** the platform processes them, **Then** they are consolidated into one incident record rather than shown as hundreds of separate items.
2. **AC-1.2**: **Given** an incident has been formed, **When** a user opens it, **Then** the user can see every original alert correlated into it (via `correlated_alerts`), an ordered timeline of events, the related/affected services (via `network_nodes`), and a dependency graph.
3. **AC-1.3**: **Given** an incident has been formed, **When** the user views the root cause, **Then** the platform shows a probable root cause, a confidence score, and a plain-language explanation referencing the supporting alert/topology evidence and, where relevant, similar historical incidents or remediations.
4. **AC-1.4**: **Given** two unrelated alert groups affecting entirely different, non-dependent services arrive at the same time, **When** the platform clusters them, **Then** they are kept as separate incidents rather than incorrectly merged.
5. **AC-1.5**: **Given** an incident has been formed, **When** a user views its status, **Then** it reflects one of the fixed enum values (Open, Investigating, Awaiting Approval, Remediating, Resolved, Closed) and open incidents are visibly distinguishable from resolved/historical ones.

---

### User Story 2 - Semantic Runbook Retrieval & Approved Remediation (Priority: P2)

As an on-call engineer or incident commander handling an open incident, I want the platform to find the most relevant remediation procedure from the organization's existing runbook library using BigQuery Vector Search over its already-generated embeddings (not keyword search), propose a concrete fix with an explicit rollback plan and risk level, and require my explicit approval before anything is executed, so resolution is fast, safe, and never happens without human sign-off.

**Why this priority**: This delivers the second milestone and the core "safe remediation" value proposition. It depends on an incident already existing (from User Story 1) but does not require prediction or executive reporting to demonstrate value.

**Independent Test**: Can be fully tested by taking a known incident whose root cause has a clear precedent among the existing ~20 runbooks and confirming the platform surfaces a semantically matched runbook (via `VECTOR_SEARCH` over `runbooks.embedding`) with a similarity score, a step-by-step fix, a rollback plan, a risk rating, and that no action executes until an approver explicitly approves it.

**Acceptance Scenarios**:

1. **AC-2.1**: **Given** an open incident and the existing `runbooks` table, **When** the platform searches for a remediation, **Then** it returns the most semantically similar runbook(s) via BigQuery Vector Search over `runbooks.embedding`, with a similarity score and recommended actions, without relying on exact keyword matches.
2. **AC-2.2**: **Given** a matched runbook, **When** the platform proposes a fix, **Then** it presents a step-by-step remediation plan, a corresponding rollback plan, and an assessed risk level before any action is taken.
3. **AC-2.3**: **Given** a proposed remediation is awaiting review, **When** an authorized approver rejects it, **Then** no action is executed and the incident remains open for further action.
4. **AC-2.4**: **Given** a proposed remediation is approved, **When** execution proceeds, **Then** it runs as a real action (via a GCP API call, e.g., Cloud Run Admin API) against the designated sandbox/demo target service — not a simulated response — and the outcome (success/failure) is recorded both against the incident and as a new entry in `remediation_logs`.
5. **AC-2.5**: **Given** no runbook in the existing `runbooks` table meets the minimum similarity/confidence threshold for an incident, **When** retrieval completes, **Then** the platform clearly indicates no confident match was found instead of presenting a low-quality guess as authoritative.

---

### User Story 3 - Proactive Predictive Risk Forecasting at Scale (Priority: P2)

As a reliability engineer, I want the platform to continuously analyze trends across the existing alert history and warn me of a likely future outage — including what will fail, roughly when, how confident the prediction is, and why — so my team can act before customers are impacted, even while the platform is absorbing a high-volume replayed alert burst.

**Why this priority**: This delivers the predictive half of the third milestone and represents the platform's most forward-looking value: preventing incidents rather than only reacting to them. It builds on the existing `alert_stream` history but does not require the runbook/remediation workflow to demonstrate value on its own.

**Independent Test**: Can be fully tested by pointing the predictive capability at a degrading trend already present in `alert_stream` history for a service and confirming the platform surfaces a prediction (predicted failure, time window, confidence, affected services, and rationale) before any alert for that failure has actually fired in the replay.

**Acceptance Scenarios**:

1. **AC-3.1**: **Given** `alert_stream` history shows a degrading trend for a service consistent with a past pre-outage pattern, **When** the predictive capability evaluates current data, **Then** it surfaces a forecast identifying the likely failure, an estimated time-to-failure window, a confidence level, the affected services, and the reasoning behind the forecast.
2. **AC-3.2**: **Given** replayed alert values deviate from established historical norms in `alert_stream`, **When** the platform evaluates it, **Then** the deviation is surfaced as a flagged anomaly trend, whether or not it yet meets the threshold for a full outage prediction.
3. **AC-3.3**: **Given** a replayed alert burst of 1,000+ alerts arrives within one minute, **When** the platform is processing this load, **Then** it continues to accept and cluster incoming alerts without dropping alerts or becoming unresponsive.
4. **AC-3.4**: **Given** alert or runbook content contains secrets or personally identifiable information, **When** that content is surfaced in any prediction, dashboard, or log, **Then** the sensitive values are redacted while preserving enough context to remain useful.

---

### User Story 4 - Executive Business Impact Reporting & Automated Postmortems (Priority: P3)

As an executive or business stakeholder, I want a single dashboard that translates active and predicted incidents into business terms — revenue at risk, SLA exposure, affected customers, resolution success rate, and time/MTTR saved — and I want every resolved incident to automatically produce a written postmortem, so I can understand operational risk and platform value, and my team retains a durable record of what happened, without needing engineering support to interpret raw technical data or write reports by hand.

**Why this priority**: This delivers the fourth milestone and demonstrates business value, but is meaningful only once incidents (User Story 1) and, ideally, predictions (User Story 3) already exist to report on — making it a natural capstone rather than a foundational capability.

**Independent Test**: Can be fully tested by resolving a sample incident already linked to `customer_accounts`/`remediation_logs` data and confirming the executive dashboard displays correctly computed revenue-at-risk, SLA exposure, affected-customer count, and MTTR figures, and that a corresponding row is written into `incident_postmortems`, independent of whether prediction workflows have run.

**Acceptance Scenarios**:

1. **AC-4.1**: **Given** an active incident linked to `customer_accounts` via `service_name`, **When** the executive dashboard loads, **Then** it displays the estimated number of affected customers and the estimated revenue at risk for that incident.
2. **AC-4.2**: **Given** an incident affects a service with SLA-relevant attributes on `customer_accounts`, **When** the dashboard evaluates impact, **Then** it displays the applicable SLA exposure/credit risk in business terms.
3. **AC-4.3**: **Given** one or more incidents have been resolved through the platform, **When** the dashboard is viewed, **Then** it displays MTTR, resolution success rate, and estimated time saved compared to the historical baseline reflected in existing incident/remediation data.
4. **AC-4.4**: **Given** a predicted (not yet occurred) outage exists, **When** the dashboard is viewed, **Then** the predicted incident is distinguished from currently active incidents while still contributing to the platform's forward-looking risk view.
5. **AC-4.5**: **Given** an incident reaches Resolved status, **When** the Executive Impact Agent runs, **Then** a postmortem summarizing the incident, root cause, remediation outcome, and business impact is written into `incident_postmortems`, and re-running it for the same incident updates rather than duplicates that record.

---

### Primary Demonstration Flow (End-to-End)

This flow illustrates how User Stories 1-4 work together in the platform's flagship demonstration and is the definitive test of the feature as a whole:

1. **Given** the BigQuery warehouse (`alert_stream`, `network_nodes`, `runbooks` with embeddings, `customer_accounts`, historical `incidents`/`remediation_logs`) is already populated, **When** approximately 1,000 alerts are replayed from `alert_stream` within about one minute, **Then** the platform accepts all of them without loss and begins clustering them in real time.
2. **Given** the alert burst is clustering, **When** clustering completes, **Then** the platform presents a single incident (written to `incidents`/`correlated_alerts`) with its correlated alerts, timeline, affected services, and dependency graph.
3. **Given** the incident exists, **When** root cause analysis runs, **Then** the platform presents a probable root cause with a confidence score and supporting reasoning drawn from `alert_stream`, `network_nodes`, and historical `incidents`/`remediation_logs`.
4. **Given** a root cause has been identified, **When** runbook retrieval runs, **Then** the platform presents a semantically matched runbook (via `VECTOR_SEARCH` over `runbooks.embedding`) with a similarity score and recommended actions.
5. **Given** `alert_stream` trends are evaluated in parallel, **When** a degrading pattern is detected, **Then** the platform surfaces a predicted outage with a time-to-failure window, confidence, and rationale.
6. **Given** a remediation and rollback plan have been generated from the matched runbook, **When** the plan is presented to an approver, **Then** execution is blocked until the approver explicitly approves it.
7. **Given** the approver approves the remediation, **When** execution proceeds, **Then** it runs in the sandbox environment, the result is recorded against the incident, and a new entry is appended to `remediation_logs`.
8. **Given** the incident, prediction, and remediation outcome are known, **When** the executive dashboard refreshes, **Then** it reflects updated revenue at risk, SLA exposure, affected customers, and MTTR/time-saved figures.
9. **Given** the incident reaches Resolved status, **When** the Executive Impact Agent completes its cycle, **Then** an automated postmortem is written into `incident_postmortems`.

### Edge Cases

- **Resolved (Clarifications, 2026-09-24)**: When an `alert_stream` row references a `node_id` with no matching row in `network_nodes`, or a `service_name` with no matching row in `customer_accounts` (referential gaps in existing data), the platform still processes and clusters the alert using whatever fields ARE resolvable, marking the unresolved relationship as Unknown/Unmapped in dependency and impact views (see FR-005) rather than dropping the alert or failing the join.
- **Resolved (Clarifications, 2026-09-24)**: The replay mechanism sustains a 1,000+ alerts/minute target from the finite ~3,000-row `alert_stream` by looping/reusing rows wrapped in a per-occurrence envelope with a fresh `replay_event_id` and rewritten timestamp (see FR-004); the Alert Correlation Agent dedups/clusters on `replay_event_id` rather than the reused natural `alert_id`, so repeated passes are correctly treated as new occurrences instead of being silently collapsed.
- What happens when no historical precedent exists in the existing ~18 `incidents` / ~20 `runbooks` for a genuinely novel failure pattern (cold start), leaving root cause confidence very low?
- What happens when two independent incidents share a coincidentally overlapping node or service but are not actually related?
- What happens when a proposed remediation's rollback plan itself fails or cannot be validated?
- What happens when a designated approver is unavailable and a proposed remediation sits pending for an extended period?
- How does the system handle secrets/PII embedded inside the `alert_stream.message` field or free-text runbook content rather than in clearly labeled fields?
- What happens when SLA/revenue attributes are missing or incomplete on `customer_accounts` for a service involved in an incident — can the executive dashboard still show a partial view?
- What happens when a predictive forecast turns out to be wrong (predicted outage does not occur) — how is that tracked?
- What happens when postmortem generation is triggered more than once for the same resolved incident — does `incident_postmortems` end up with duplicate rows?
- What happens when BigQuery Vector Search over the ~20-row `runbooks` table returns multiple runbooks with very close similarity scores — how is the top match chosen and presented?

## Requirements *(mandatory)*

### Functional Requirements

#### Warehouse Access & Data Grounding

- **FR-001**: System MUST treat the existing BigQuery warehouse (`sre_telemetry.alert_stream`, `sre_topology.network_nodes`, `sre_knowledge_base.runbooks` / `embedding_model`, `sre_incident_mart.customer_accounts` / `incidents` / `correlated_alerts` / `remediation_logs` / `incident_postmortems`) as the platform's single source of truth. The platform MUST NOT deploy, provision, ingest into, or otherwise stand up any new warehouse, database, or upload/ETL pipeline as part of this feature.
- **FR-002**: System MUST query `alert_stream`, `network_nodes`, `runbooks`, `customer_accounts`, `incidents`, `correlated_alerts`, and `remediation_logs` directly and live for every analytical operation (clustering, root cause analysis, runbook retrieval, prediction, remediation, executive impact); no agent MAY read from a locally cached, duplicated, or hardcoded copy of this data.
- **FR-003**: System MUST use the existing 768-dimension embedding column already present on `runbooks` (generated via Vertex AI `text-embedding-005`, per `embedding_model`) for semantic runbook retrieval; the platform MUST NOT re-generate, re-embed, or maintain a separate embedding pipeline for runbook content.
- **FR-004**: System MUST simulate real-time alert arrival for demonstration purposes by replaying/streaming existing `alert_stream` rows at a controlled rate, without inserting, mutating, or duplicating rows in `alert_stream` itself. Each replayed occurrence MUST be wrapped in an envelope carrying a freshly generated `replay_event_id` and a rewritten arrival timestamp, distinct from the row's natural `alert_id`, so that looping over the finite existing row set to sustain the target replay rate produces distinguishable occurrences rather than being collapsed as repeats of the same original alert.
- **FR-005**: System MUST correctly traverse the documented relationships across warehouse tables (`alert_stream.node_id`→`network_nodes.node_id`; `alert_stream.service_name`→`customer_accounts.service_name`; `correlated_alerts.incident_id`→`incidents.incident_id`; `correlated_alerts.alert_id`→`alert_stream.alert_id`; `remediation_logs.incident_id`→`incidents.incident_id`; `remediation_logs.runbook_id`→`runbooks.runbook_id`; `incident_postmortems.incident_id`→`incidents.incident_id`) when joining data for any correlation, root-cause, impact, or postmortem output. When a referenced row is missing (e.g., an `alert_stream` row's `node_id` has no matching `network_nodes` row, or its `service_name` has no matching `customer_accounts` row), the system MUST still process the alert using whatever fields ARE resolvable, marking the unresolved relationship as Unknown/Unmapped in dependency and impact views rather than dropping the alert or failing the join.

#### Alert Clustering & Root Cause Isolation (Milestone 1)

- **FR-006**: The Alert Correlation Agent MUST query `alert_stream` to detect storms/duplicates within a short time window and cluster related alerts into a single incident, writing the correlated alert-to-incident links into `correlated_alerts` and creating or updating the corresponding row in `incidents`.
- **FR-007**: System MUST preserve traceability from every incident back to each original `alert_stream` row correlated into it, via `correlated_alerts`.
- **FR-008**: System MUST present, for every incident, a chronological timeline, the related/affected services (via `network_nodes`), and a visual service dependency/blast-radius graph.
- **FR-009**: The Root Cause Analysis Agent MUST join `alert_stream`, `network_nodes`, and historical `incidents`/`remediation_logs` data to produce a probable root cause, a confidence score, and a plain-language explanation, persisted against the corresponding incident.
- **FR-010**: System MUST track every incident against a fixed status enum — Open, Investigating, Awaiting Approval, Remediating, Resolved, Closed — and allow users to distinguish currently open incidents (any pre-Resolved status) from resolved/historical ones within the same interface.
- **FR-011**: System MUST keep unrelated alert groups (no shared node, service, or dependency relationship) as separate incidents rather than merging them.

#### Runbook Retrieval & Safe Remediation (Milestone 2)

- **FR-012**: The Runbook Retrieval Agent MUST identify candidate remediation procedures using BigQuery Vector Search (`VECTOR_SEARCH`) over the existing `runbooks.embedding` column only (no keyword-based matching), and MUST output the matched runbook, its similarity score, and recommended actions.
- **FR-013**: System MUST present, for an open incident, the matched runbook(s) together with the similarity score and recommended actions.
- **FR-014**: System MUST clearly indicate when no runbook meets the minimum similarity/confidence threshold for an incident, rather than presenting a low-confidence guess as authoritative.
- **FR-015**: The Remediation Agent MUST generate a step-by-step remediation script and a corresponding rollback script derived from the matched runbook's documented procedure, and MUST validate the generated commands before they are presented for approval.
- **FR-016**: System MUST present an assessed risk level for every proposed remediation action.
- **FR-017**: System MUST require a designated human approver to explicitly review and approve a proposed remediation before any execution occurs; execution MUST NOT proceed if the remediation is rejected.
- **FR-018**: System MUST record the approver's identity, decision (approve/reject), timestamp, and any comments for every remediation decision.
- **FR-019**: System MUST restrict remediation execution to a controlled sandbox/demonstration environment — a dedicated, isolated demo target service that the Remediation Agent operates on via real GCP API calls (e.g., Cloud Run Admin API) rather than a simulated/mocked response — and MUST make the rollback plan available if the executed fix does not resolve the issue.
- **FR-020**: System MUST record the outcome of every executed remediation (success/failure, from the real execution result) as a new entry in the existing `remediation_logs` history, linked by `incident_id` and `runbook_id`, so future root-cause and effectiveness analysis can learn from it.
- **FR-021**: System MUST allow a rejected remediation to return the incident to an actionable state (e.g., select a different runbook, escalate) rather than leaving it stuck.

#### Predictive Risk & Resilience at Scale (Milestone 3)

- **FR-022**: The Predictive Risk Agent MUST use BigQuery ML over `alert_stream` trend data to output a predicted failure, an estimated time-to-failure window, a confidence level, and the affected services.
- **FR-023**: System MUST detect and surface anomalous alert trends in `alert_stream` that deviate from established historical patterns, independent of whether a full outage prediction is triggered.
- **FR-024**: System MUST continue accepting and clustering the replayed alert stream during bursts of at least 1,000 alerts per minute without dropping alerts, using a streaming path (Pub/Sub) feeding autoscaling compute (Cloud Run).
- **FR-025**: System MUST automatically scale its alert-processing capacity up and down with incoming replay load rather than requiring manual capacity changes.
- **FR-026**: System MUST redact secrets and personally identifiable information from alert (`message`), runbook, and log content before that content is displayed, stored for retrieval, or included in any generated summary or remediation script.

#### Executive Business Impact & Automated Postmortems (Milestone 4)

- **FR-027**: The Executive Impact Agent MUST join `customer_accounts`, `incidents`, and any SLA-relevant attributes present on `customer_accounts` to calculate, for each incident, the estimated number of affected users/customers, revenue at risk, and applicable SLA credit/penalty exposure, using the `alert_stream.service_name → customer_accounts.service_name` linkage to scope the incident's blast radius. The specific `customer_accounts` column names backing these figures MUST be confirmed against the live schema at implementation time (assumed field set in Key Entities → Customer Account) rather than hardcoded from an unverified guess.
- **FR-028**: System MUST track mean-time-to-resolution (MTTR) for incidents handled through the platform and report the estimated MTTR reduction versus the historical baseline reflected in existing `incidents`/`remediation_logs` data.
- **FR-029**: System MUST present, in one consolidated view, current incidents, predicted incidents, resolution success rate, and estimated time saved for business stakeholders.
- **FR-030**: System MUST express all business-impact figures (revenue, customers, SLA exposure) in plain business terms rather than technical/system terms.
- **FR-031**: The Executive Impact Agent MUST automatically generate a postmortem for each resolved incident — summarizing the incident, root cause, correlated alerts, retrieved runbook, remediation outcome, and business impact — and MUST write it into the currently-empty `incident_postmortems` table, linked by `incident_id`, populating the structured field set defined in Key Entities → Incident Postmortem (including a `version` counter) rather than a single unstructured text blob.
- **FR-032**: System MUST NOT create a duplicate postmortem for an incident that already has one recorded in `incident_postmortems`; regenerating a postmortem for the same incident MUST update the existing record instead.

#### User Interface

- **FR-033**: System MUST provide the following distinct views: Live Incident Console, Incident Timeline, Alert Correlation View, Root Cause Analysis View, Runbook Recommendation View, Approval Console, Predictive Health Dashboard, and Executive Dashboard.
- **FR-034**: System MUST let an authorized user navigate from an incident in the Live Incident Console to its correlation, root cause, runbook, and approval detail views while keeping a consistent incident identity across all views.

#### Security & Governance

- **FR-035**: System MUST authenticate every end user via Firebase Authentication / Google Identity Platform sign-in issuing per-user identity and custom role claims (On-Call Engineer, Incident Commander, Approver, Executive Viewer, Administrator), and MUST enforce role-based access control derived from those claims — separate from the GCP IAM roles governing service-to-service access to the BigQuery warehouse and other GCP resources — so only authorized users can view sensitive incident data or approve/execute remediations.
- **FR-036**: System MUST store all credentials and secrets in a managed secret store (Secret Manager) and MUST NOT expose them in plaintext in the UI, logs, or generated scripts.
- **FR-037**: System MUST record every security-relevant action (incident access, approval decision, remediation execution) in an auditable log capturing the actor, timestamp, and action taken.
- **FR-038**: System MUST mask sensitive fields (e.g., customer identifiers, credentials embedded in free text) within existing warehouse content (alert messages, runbook text, historical incident notes) so they are never exposed via agent outputs or dashboards.
- **FR-039**: System MUST treat `alert_stream`, `network_nodes`, `runbooks`, `embedding_model`, and `customer_accounts` as read-only source-of-truth tables — the platform MUST NOT modify, delete, or overwrite rows in these tables; all platform-generated output is confined to `correlated_alerts`, `incidents` (new/updated rows), `remediation_logs` (appended outcomes), and `incident_postmortems`.

### Non-Functional Requirements

#### Performance & Scalability

- **NFR-001**: System MUST sustain a replayed alert rate of at least 1,000 alerts per minute without alert loss or unacceptable processing delay.
- **NFR-002**: Alert-processing and analysis capacity MUST scale automatically with incoming replay load, without manual operator intervention, and scale back down when load subsides.
- **NFR-003**: System SHOULD produce a consolidated incident (root cause, correlated alerts, timeline) within a bounded time (target: within 5 minutes) of an alert storm beginning, so responders are not left waiting during an active incident.
- **NFR-004**: Runbook retrieval via BigQuery Vector Search MUST return matched runbooks within a bounded time (target: within a few seconds) of an incident's root cause being identified, so retrieval feels immediate to a responder.

#### Security & Data Protection

- **NFR-005**: All access to incident data, approval actions, and dashboards MUST be authenticated (via Firebase Authentication / Google Identity Platform, per FR-035) and authorized; there MUST be no anonymous access to incident or business-impact data.
- **NFR-006**: No secret or credential value MUST ever appear in plaintext in any UI, log, exported report, or generated remediation/rollback script.
- **NFR-007**: Personally identifiable information present in existing warehouse content MUST be redacted before being surfaced in any agent output, dashboard, or audit trail entry, while preserving enough surrounding context to remain useful for diagnosis.

#### Trust, Safety & Governance

- **NFR-008**: Every approval/rejection decision and every executed remediation or rollback action MUST be individually attributable to an actor and timestamp and retained for subsequent compliance review.
- **NFR-009**: No remediation action capable of altering a system MUST execute without an explicit prior human approval, regardless of alert volume or perceived urgency.
- **NFR-010**: Every automated determination shown to a user (root cause, runbook match, prediction, risk level) MUST include a human-readable rationale and a confidence or similarity indicator rather than a bare conclusion.
- **NFR-011**: All correlation, root-cause, retrieval, prediction, and remediation outputs MUST be derived solely from live queries against the existing warehouse; the system MUST NOT ship with, or fall back to, pre-baked example mappings, static runbook logic, or hardcoded alert-to-resolution answers.

#### Reliability & Usability

- **NFR-012**: Temporary unavailability of any single analysis capability (e.g., prediction) MUST NOT prevent core incident visibility and alert correlation from continuing to function.
- **NFR-013**: Business-impact figures MUST be presented in terms a non-technical stakeholder can interpret without engineering assistance (currency amounts, customer counts, percentages, plain-language summaries).

### Key Entities *(include if feature involves data)*

- **Alert** (`sre_telemetry.alert_stream`, ~3,000 existing rows): A raw monitoring signal carrying `alert_id`, `node_id`, `service_name`, `severity`, `alert_type`, `message`, `measured_value`, and `timestamp`. Used for anomaly detection, alert-storm detection, incident clustering, trend analysis, and forecasting. Related to Network Node via `node_id` and to Customer Account via `service_name`.
- **Network Node** (`sre_topology.network_nodes`, ~64 existing rows): A piece of infrastructure/service topology carrying `node_id`, `node_name`, `node_type`, `region`, `ip_address`, and `status`. Used for dependency mapping, impact analysis, topology visualization, and blast-radius calculations.
- **Runbook / SOP** (`sre_knowledge_base.runbooks`, ~20 existing rows, plus the supporting `embedding_model` reference table): A documented remediation procedure containing SOPs, remediation steps, rollback commands/scripts, and failure signatures, plus a 768-dimension semantic embedding (already generated via Vertex AI `text-embedding-005`) used for similarity retrieval — never keyword search.
- **Customer Account** (`sre_incident_mart.customer_accounts`, ~45 existing rows): Customer/account information, including a `service_name` linkage to Alert and topology data, together with the SLA and revenue-relevant attributes used to estimate business impact — assumed to include (pending live-schema verification per Clarifications) `customer_id`, `customer_name`, `service_name`, `tier`, `monthly_recurring_revenue`, `sla_uptime_target_pct`, `sla_credit_rate_per_hour`, and `user_count`.
- **Incident** (`sre_incident_mart.incidents`, ~18 existing historical rows plus newly clustered rows created by this platform): A single correlated cluster of alerts representing one underlying problem, keyed by `incident_id`. Carries a status (Open, Investigating, Awaiting Approval, Remediating, Resolved, or Closed), root cause, confidence score, and reasoning. Existing rows serve as precedent for root-cause reasoning; new rows are created/updated as the platform clusters live-replayed alerts.
- **Correlated Alert Link** (`sre_incident_mart.correlated_alerts`): The many-to-one relationship (`incident_id`, `alert_id`) tying individual alerts to the incident they were clustered into.
- **Remediation Log** (`sre_incident_mart.remediation_logs`): Historical and newly-appended remediation outcomes (`incident_id`, `runbook_id` linkage), used both as precedent for root-cause/effectiveness learning and as the durable record of every remediation this platform executes.
- **Incident Postmortem** (`sre_incident_mart.incident_postmortems`, currently empty): An automatically generated post-incident summary written by the platform for each resolved incident, linked by `incident_id`; populated exclusively as an output of this feature. Written using a structured field set (per Clarifications): `incident_id`, `generated_at`, `root_cause_summary`, `timeline_summary`, `remediation_summary`, `business_impact_summary`, `full_report_markdown` (the complete human-readable narrative), and `version` (incremented, not duplicated, on regeneration per FR-032).
- **Risk Forecast / Prediction**: A forward-looking statement about a likely future failure, derived from BigQuery ML analysis of `alert_stream` trends, including confidence, time-to-failure window, and affected services; kept conceptually distinct from Incident status.
- **Remediation Action**: A proposed fix paired with its rollback counterpart and an assessed risk level, generated from a matched Runbook for a specific Incident, awaiting or having received human approval.
- **Approval Decision**: A record of a human approver's accept/reject decision on a Remediation Action, including actor, timestamp, and rationale.
- **Audit Log Entry**: An immutable record of a security- or workflow-relevant action, including actor, timestamp, and action taken.
- **User / Role**: An individual, authenticated via Firebase Authentication / Google Identity Platform, with an assigned role (e.g., On-Call Engineer, Incident Commander, Approver, Executive Viewer, Administrator) that governs what they can view or approve.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A burst of 1,000+ related alerts replayed within one minute is consolidated into a single incident visible to responders within 5 minutes of the burst starting.
- **SC-002**: Responders can identify a probable root cause with a supporting explanation for at least 80% of demo incidents without manually cross-referencing alert or topology data themselves.
- **SC-003**: For incidents with a matching precedent among the existing runbooks, a relevant runbook recommendation is surfaced at least 90% of the time.
- **SC-004**: 100% of executed remediation actions have a recorded human approval decision; zero remediations execute without one.
- **SC-005**: At least one impending failure is correctly predicted ahead of it occurring during the demo scenario, with a stated reason and lead time.
- **SC-006**: Executives can view current revenue at risk, SLA exposure, and affected-customer counts for any active incident in a single dashboard view, without engineering assistance to interpret the figures.
- **SC-007**: Incidents handled through the platform show at least a 30% reduction in mean-time-to-resolution compared to the documented historical baseline reflected in existing incident/remediation records.
- **SC-008**: Zero instances of secret or PII leakage are found in the UI, logs, or generated scripts during a security audit review of a demo run.
- **SC-009**: 100% of alerts replayed during a 1,000+ alerts/minute burst are accounted for within the resulting incident cluster(s); none are silently dropped.
- **SC-010**: 100% of resolved demo incidents have a corresponding automatically generated postmortem recorded, with zero duplicate postmortems for the same incident.

## Glossary

- **ADK (Agent Development Kit)**: The mandated framework used to build and coordinate the platform's six specialized AI agents.
- **Alert Storm**: A short-window burst of many related alerts triggered by the same underlying condition.
- **BigQuery**: The mandated Google Cloud data warehouse serving as the system of record this platform queries — already provisioned and populated prior to this feature.
- **BigQuery ML**: The mandated Google Cloud capability used to build the predictive risk forecasting models directly over data stored in BigQuery.
- **BigQuery Vector Search**: The mandated Google Cloud capability used to perform semantic similarity search over the runbook embeddings already stored in BigQuery.
- **Blast Radius**: The set of services, customers, or systems affected by a given incident, derived from the dependency/topology data.
- **Embedding**: A numeric representation of text (e.g., a runbook) that enables semantic similarity search, as opposed to keyword matching.
- **Gemini**: The mandated large language model (accessed via Vertex AI) powering the agents' reasoning, explanation, and generation outputs.
- **Human-in-the-Loop Approval**: The mandatory workflow step requiring an authorized person to review and approve a remediation before it can execute.
- **Incident Cluster**: The consolidated group of correlated alerts treated as a single incident.
- **MTTR (Mean Time To Resolution)**: The average time taken to fully resolve an incident, a key measure of operational efficiency.
- **PII (Personally Identifiable Information)**: Any data that could identify a specific individual, which must be redacted before display or storage for retrieval.
- **Postmortem**: A structured after-action report summarizing an incident's root cause, timeline, remediation, and business impact, generated automatically by the platform and written into `incident_postmortems`.
- **Root Cause Analysis (RCA)**: The process of determining the most probable underlying cause of an incident from supporting evidence.
- **Runbook / SOP (Standard Operating Procedure)**: A documented, pre-approved procedure describing how to resolve a known type of problem.
- **Sandbox Execution**: Running a remediation action in an isolated, non-production environment for safe validation/demonstration.
- **SLA (Service Level Agreement)**: A contractual commitment defining expected service performance and the penalties/credits owed if it is breached.
- **Vector Search**: A retrieval technique that finds the most similar items to a query by comparing their embeddings rather than their literal text.
- **Warehouse**: The pre-existing, fully populated BigQuery datasets (`sre_telemetry`, `sre_topology`, `sre_knowledge_base`, `sre_incident_mart`) that serve as this platform's sole source of truth.

## Assumptions

- The BCE Hackfest Track 2 BigQuery warehouse (datasets `sre_telemetry`, `sre_topology`, `sre_knowledge_base`, `sre_incident_mart`) is already fully provisioned, loaded, and populated in the target GCP project prior to this feature; provisioning the warehouse, any JSON/file ingestion pipeline, ETL, Cloud Storage landing, or embedding generation at ingest time is explicitly OUT of scope for this feature (see Out of Scope below) — the platform is a pure consumer of this existing data via direct BigQuery queries and BigQuery Vector Search. The exact GCP project ID hosting this warehouse is supplied via deployment configuration (e.g., a `GCP_PROJECT_ID` variable) rather than hardcoded; every new resource this feature creates (Cloud Run services, Pub/Sub topics/subscriptions, Vertex AI connections, any BigQuery views) MUST be deployed into that same project, single-region `us-central1`, to co-locate with and avoid cross-region latency or availability mismatches against the existing warehouse (see Clarifications).
- The 768-dimension embeddings already present on `runbooks.embedding` (generated via Vertex AI `text-embedding-005`, per `embedding_model`) are assumed correct and current; this feature does not regenerate, validate, or backfill them.
- The hackathon scoring rubric mandates explicit, visible use of specific Google Cloud services (BigQuery, BigQuery Vector Search, BigQuery ML, Cloud Run, Gemini via Vertex AI, ADK, Pub/Sub, Cloud Scheduler, Cloud Logging, Secret Manager, IAM); these are treated as fixed constraints of this feature rather than open implementation choices. Cloud Storage is no longer part of this mandated list, since there is no upload/landing step under the existing-warehouse premise.
- Looker Studio remains optional/supplementary per the source brief and is not required for core acceptance of this feature. Firestore, while listed as optional in the source brief, IS required by this feature's architecture as the live/ephemeral state store for approvals, predictions, and executive metrics (see plan.md/design.md) — it is not a system of record and never holds any of the four FR-039 BigQuery-written entities.
- "Streaming" alert arrival for demo purposes is simulated by replaying/streaming existing `alert_stream` rows at a controlled rate rather than a live production monitoring integration or new-record ingestion; the replay mechanism does not insert, duplicate, or mutate rows in `alert_stream`. Each replayed row is wrapped in a per-occurrence envelope carrying a freshly generated `replay_event_id` and a rewritten arrival timestamp (see FR-004); downstream agents dedup/cluster on `replay_event_id`, not the reused natural `alert_id`, so the replay mechanism can loop over the finite ~3,000-row history to sustain the 1,000+ alerts/minute target without the Alert Correlation Agent mistaking every repeated pass for the exact same original alert.
- Remediation execution occurs only in a sandboxed/demonstration environment — a dedicated demo target service acted on via real GCP API calls, not a simulated response — and executing remediations against live production infrastructure is out of scope for this feature.
- Users are internal organizational personnel (on-call engineers, incident commanders, approvers, executives, administrators) who already have corporate identity credentials; new end-user account registration is out of scope.
- Similarity/confidence thresholds used to decide a "confident match" for root cause, runbook retrieval, and prediction are configurable and will be tuned during implementation rather than fixed by this spec.
- Meaningful root-cause and prediction confidence depends on the existing ~18 historical incidents and ~20 runbooks as precedent; with such a modest historical corpus, low-confidence/no-match outcomes are expected for genuinely novel failure patterns and MUST degrade gracefully rather than present a high-confidence guess.
- "1,000+ alerts per minute" is treated as a peak burst target for the demo replay scenario rather than a required sustained, continuous load, and is bounded by the ~3,000 rows available in `alert_stream` (the replay mechanism may loop or reuse rows to sustain the target rate across a demo run).
- SLA and revenue-impact attributes needed for executive reporting are assumed to already exist as fields on `customer_accounts`; no separate SLA or revenue data domain is introduced. Absent a live schema inspection, this feature assumes `customer_accounts` exposes at least `customer_id`, `customer_name`, `service_name`, `tier`, `monthly_recurring_revenue`, `sla_uptime_target_pct`, `sla_credit_rate_per_hour`, and `user_count` (see Key Entities → Customer Account); the Executive Impact Agent MUST confirm actual column names/types against the live schema (e.g., via `INFORMATION_SCHEMA.COLUMNS`) at implementation time and adapt its field mapping accordingly rather than hardcoding this assumed list blindly.
- Audit log retention follows standard organizational/regulatory practice; no specific named regulation (e.g., HIPAA, PCI-DSS) was indicated in the source request.

## Out of Scope

- Provisioning, creating, or deploying the BigQuery warehouse, its datasets, tables, or schemas.
- Any JSON/file upload workflow, ETL pipeline, or data-ingestion service.
- Landing raw source data in Cloud Storage (or any other object storage) prior to loading it into BigQuery.
- Generating, regenerating, validating, or backfilling embeddings on `runbooks` (the existing embedding column and `embedding_model` reference are assumed correct and current).
- Modifying, deleting, or overwriting rows in the existing source-of-truth tables (`alert_stream`, `network_nodes`, `runbooks`, `embedding_model`, `customer_accounts`).
- Executing remediations against live production infrastructure (remediation execution is confined to the sandbox/demo target service).
- New end-user account registration or self-service sign-up (users already hold corporate identity credentials).
