# Feature Specification: JSON-Driven Agentic AI Incident Prevention & Resolution Platform

**Feature Branch**: `001-json-agentic-ai`  
**Created**: 2026-09-24  
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

## Overview

This feature delivers an Agentic AI Incident Prevention & Resolution Platform on Google Cloud that ingests raw operational JSON exports (alerts, telemetry, historical incidents, runbooks, topology, SLA, and revenue impact data) into BigQuery, then drives a six-agent ADK pipeline — Alert Correlation, Root Cause Analysis, Runbook Retrieval (BigQuery Vector Search), Predictive Risk (BigQuery ML), Remediation (with mandatory human approval), and Executive Impact — to turn alert storms into a single explained incident with a retrieved SOP, a safe approved fix, an outage forecast, and an executive-facing business-impact summary. Every output is derived from real ingested data and live model/vector-search calls; no alert-to-resolution mapping, runbook match, or forecast is hardcoded.

## Problem Statement

SRE and incident-response teams are overwhelmed by alert storms (hundreds to 1000+/minute) that obscure the true root cause, forcing manual correlation, manual runbook lookup, and manual impact estimation — all of which slow Mean Time To Resolution (MTTR), increase SLA breach risk, and hide revenue-at-risk from executives until after the fact. There is no existing system that automatically clusters raw alerts into a single explained incident, semantically retrieves the right SOP from historical runbooks, forecasts failures before they happen, and quantifies business impact — all backed by real ingested data rather than static, hand-authored mappings.

## Clarifications

### Session 2026-09-24

- Q: How should ingestion handle duplicate/re-uploaded alert or historical-incident records? → A: Upsert by a per-domain natural identifier (or a derived hash key when absent) so duplicates update/are skipped instead of creating duplicate rows.
- Q: Is the "sandbox/demonstration environment" remediation execution real or simulated? → A: Real — the Remediation Agent invokes actual GCP APIs (e.g., Cloud Run Admin API) against a dedicated, isolated demo target service; the recorded outcome comes from real execution logs/exit codes, never a mocked or random result.
- Q: What identity mechanism authenticates end users for RBAC and approval attribution? → A: Firebase Authentication / Google Identity Platform sign-in issuing per-user identity and custom role claims (On-Call Engineer, Incident Commander, Approver, Executive Viewer, Administrator), enforced server-side; GCP IAM separately governs service-to-service access to GCP resources.
- Q: Where does the "affected customers/users impacted" figure come from? → A: A customer/user-count attribute on the ingested Revenue Impact Record (per service/customer segment), aggregated across the incident's blast radius from the dependency graph — no new data domain is introduced.
- Q: What are the canonical incident status values? → A: Fixed enum — Open, Investigating, Awaiting Approval, Remediating, Resolved, plus Closed as a terminal archival state; a forecast remains a separate Risk Forecast/Prediction entity, never an incident status.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Multi-Source Data Ingestion into BigQuery (Priority: P1)

As a platform operator, I upload the organization's raw JSON exports (alerts, telemetry, historical incidents, runbooks/SOPs, network topology & service dependencies, SLA definitions, and revenue impact data), and the platform automatically loads, structures, and prepares all of it — including generating searchable embeddings for runbooks — so every downstream capability can use real data immediately, with no manual mapping, scripting, or database administration required.

**Why this priority**: Every other capability in the platform — clustering, root cause analysis, runbook retrieval, prediction, and executive reporting — depends entirely on real ingested data. Without reliable, zero-touch ingestion, the "no hardcoded mappings/no static runbooks" promise cannot be honored and no other user story can be demonstrated with real results.

**Independent Test**: Can be fully tested by uploading one sample file for each of the 7 data domains and confirming, without any manual steps, that each dataset becomes queryable and that runbook content becomes semantically searchable — independent of whether any agent has yet run against it.

**Acceptance Scenarios**:

1. **AC-1.1**: **Given** no prior data has been ingested, **When** a user uploads a valid alerts file, **Then** the alerts become available as structured, queryable records without manual schema configuration.
2. **AC-1.2**: **Given** a user uploads a valid runbooks/SOP file, **When** ingestion completes, **Then** each runbook is available for semantic similarity search, not just keyword lookup.
3. **AC-1.3**: **Given** a user uploads a file that does not match any expected data domain structure, **When** ingestion is attempted, **Then** the platform reports a clear validation failure identifying the problem instead of silently accepting bad data.
4. **AC-1.4**: **Given** data for all 7 domains has already been ingested, **When** a user uploads an updated/corrected version of one file (e.g., a revised SLA file), **Then** the new data is incorporated without discarding unrelated previously ingested history.

---

### User Story 2 - Alert Storm Clustering & Root Cause Isolation (Priority: P1)

As an on-call engineer facing hundreds of simultaneous alerts, I want the platform to automatically consolidate them into a single incident with a clearly explained probable root cause, correlated alerts, timeline, affected services, and dependency graph, so I can understand and respond to the real underlying problem in minutes instead of manually triaging a flood of individual alerts.

**Why this priority**: This is the platform's headline capability and the first milestone — turning alert chaos into a single, explainable incident. It is the moment of highest value for the on-call responder and the clearest demonstration that the platform works on real, uploaded data.

**Independent Test**: Can be fully tested by feeding a pre-ingested burst of related alerts (e.g., 200+ alerts referencing a shared set of services) into the platform and confirming a single incident is produced with correlated alerts, timeline, dependency view, and a root cause with confidence score and reasoning — without needing runbook retrieval, prediction, or remediation to be present.

**Acceptance Scenarios**:

1. **AC-2.1**: **Given** hundreds of alerts referencing overlapping services arrive within a short window, **When** the platform processes them, **Then** they are consolidated into one incident record rather than shown as hundreds of separate items.
2. **AC-2.2**: **Given** an incident has been formed, **When** a user opens it, **Then** the user can see every original alert correlated into it, an ordered timeline of events, the related/affected services, and a dependency graph.
3. **AC-2.3**: **Given** an incident has been formed, **When** the user views the root cause, **Then** the platform shows a probable root cause, a confidence score, and a plain-language explanation referencing the supporting telemetry/historical evidence.
4. **AC-2.4**: **Given** two unrelated alert groups affecting entirely different, non-dependent services arrive at the same time, **When** the platform clusters them, **Then** they are kept as separate incidents rather than incorrectly merged.

---

### User Story 3 - Semantic Runbook Retrieval & Approved Remediation (Priority: P2)

As an on-call engineer or incident commander handling an open incident, I want the platform to find the most relevant remediation procedure from the organization's own SOP library using semantic understanding (not keyword search), propose a concrete fix with an explicit rollback plan and risk level, and require my explicit approval before anything is executed, so resolution is fast, safe, and never happens without human sign-off.

**Why this priority**: This delivers the second milestone and the core "safe remediation" value proposition. It depends on an incident already existing (from User Story 2 or a directly supplied incident) but does not require prediction or executive reporting to demonstrate value.

**Independent Test**: Can be fully tested by taking a known incident with a clear precedent in the ingested runbook library and confirming the platform surfaces a semantically matched runbook with similarity score, a step-by-step fix, a rollback plan, a risk rating, and that no action executes until an approver explicitly approves it.

**Acceptance Scenarios**:

1. **AC-3.1**: **Given** an open incident and an ingested runbook library, **When** the platform searches for a remediation, **Then** it returns the most semantically similar runbook(s) with a similarity score and recommended actions, without relying on exact keyword matches.
2. **AC-3.2**: **Given** a matched runbook, **When** the platform proposes a fix, **Then** it presents a step-by-step remediation plan, a corresponding rollback plan, and an assessed risk level before any action is taken.
3. **AC-3.3**: **Given** a proposed remediation is awaiting review, **When** an authorized approver rejects it, **Then** no action is executed and the incident remains open for further action.
3. **AC-3.4**: **Given** a proposed remediation is approved, **When** execution proceeds, **Then** it runs as a real action (via a GCP API call, e.g., Cloud Run Admin API) against the designated sandbox/demo target service — not a simulated response — and the outcome (success/failure) is recorded against the incident from the actual execution result.
5. **AC-3.5**: **Given** no ingested runbook meets the minimum similarity/confidence threshold for an incident, **When** retrieval completes, **Then** the platform clearly indicates no confident match was found instead of presenting a low-quality guess as authoritative.

---

### User Story 4 - Proactive Predictive Risk Forecasting (Priority: P2)

As a reliability engineer, I want the platform to continuously analyze telemetry trends across the environment and warn me of a likely future outage — including what will fail, roughly when, how confident the prediction is, and why — so my team can act before customers are impacted, even under a high-volume alert load.

**Why this priority**: This delivers the predictive half of the third milestone and represents the platform's most forward-looking value: preventing incidents rather than only reacting to them. It builds on ingested telemetry/history but does not require the runbook/remediation workflow to demonstrate value on its own.

**Independent Test**: Can be fully tested by supplying historical telemetry showing a degrading trend for a service and confirming the platform surfaces a prediction (predicted failure, time window, confidence, affected services, and rationale) before any alert for that failure has actually fired.

**Acceptance Scenarios**:

1. **AC-4.1**: **Given** historical telemetry shows a degrading trend consistent with a past pre-outage pattern, **When** the predictive capability evaluates current data, **Then** it surfaces a forecast identifying the likely failure, an estimated time-to-failure window, a confidence level, the affected services, and the reasoning behind the forecast.
2. **AC-4.2**: **Given** telemetry deviates from established historical norms, **When** the platform evaluates it, **Then** the deviation is surfaced as a flagged anomaly trend, whether or not it yet meets the threshold for a full outage prediction.
3. **AC-4.3**: **Given** an alert burst of 1,000+ alerts arrives within one minute, **When** the platform is processing this load, **Then** it continues to accept and cluster incoming alerts without dropping alerts or becoming unresponsive.
4. **AC-4.4**: **Given** alert or telemetry content contains secrets or personally identifiable information, **When** that content is surfaced in any prediction, dashboard, or log, **Then** the sensitive values are redacted while preserving enough context to remain useful.

---

### User Story 5 - Executive Business Impact Reporting (Priority: P3)

As an executive or business stakeholder, I want a single dashboard that translates active and predicted incidents into business terms — revenue at risk, SLA exposure, affected customers, resolution success rate, and time/MTTR saved — so I can understand operational risk and platform value without needing engineering support to interpret raw technical data.

**Why this priority**: This delivers the fourth milestone and demonstrates business value, but is meaningful only once incidents (User Story 2) and, ideally, predictions (User Story 4) already exist to report on — making it a natural capstone rather than a foundational capability.

**Independent Test**: Can be fully tested by seeding a sample incident together with matching revenue, SLA, and customer-impact data, then confirming the executive dashboard displays correctly computed revenue-at-risk, SLA exposure, affected-customer count, and MTTR figures for that incident, independent of whether remediation or prediction workflows have run.

**Acceptance Scenarios**:

1. **AC-5.1**: **Given** an active incident with associated revenue and customer data, **When** the executive dashboard loads, **Then** it displays the estimated number of affected customers and the estimated revenue at risk for that incident.
2. **AC-5.2**: **Given** an incident affects a service with a defined SLA, **When** the dashboard evaluates impact, **Then** it displays the applicable SLA exposure/credit risk in business terms.
3. **AC-5.3**: **Given** one or more incidents have been resolved through the platform, **When** the dashboard is viewed, **Then** it displays MTTR, resolution success rate, and estimated time saved compared to the manual baseline.
4. **AC-5.4**: **Given** a predicted (not yet occurred) outage exists, **When** the dashboard is viewed, **Then** the predicted incident is distinguished from currently active incidents while still contributing to the platform's forward-looking risk view.

---

### Primary Demonstration Flow (End-to-End)

This flow illustrates how User Stories 1-5 work together in the platform's flagship demonstration and is the definitive test of the feature as a whole:

1. **Given** alerts, telemetry, historical incidents, runbooks, topology, SLA, and revenue data have already been uploaded and ingested, **When** approximately 1,000 related alerts arrive within about one minute, **Then** the platform accepts all of them without loss and begins clustering them in real time.
2. **Given** the alert burst is clustering, **When** clustering completes, **Then** the platform presents a single incident with its correlated alerts, timeline, affected services, and dependency graph.
3. **Given** the incident exists, **When** root cause analysis runs, **Then** the platform presents a probable root cause with a confidence score and supporting reasoning.
4. **Given** a root cause has been identified, **When** runbook retrieval runs, **Then** the platform presents a semantically matched runbook with a similarity score and recommended actions.
5. **Given** telemetry trends are evaluated in parallel, **When** a degrading pattern is detected, **Then** the platform surfaces a predicted outage with a time-to-failure window, confidence, and rationale.
6. **Given** a remediation and rollback plan have been generated from the matched runbook, **When** the plan is presented to an approver, **Then** execution is blocked until the approver explicitly approves it.
7. **Given** the approver approves the remediation, **When** execution proceeds, **Then** it runs in the sandbox environment and the result is recorded against the incident.
8. **Given** the incident, prediction, and remediation outcome are known, **When** the executive dashboard refreshes, **Then** it reflects updated revenue at risk, SLA exposure, affected customers, and MTTR/time-saved figures.

### Edge Cases

- What happens when an uploaded JSON file is malformed, incomplete, or does not match the expected structure for its data domain?
- What happens when the same alert or incident data is uploaded more than once (duplicate ingestion)?
- How does the system behave when an alert storm exceeds the 1,000 alerts/minute target — does it degrade gracefully or lose data?
- What happens when no historical precedent exists for a new type of incident (cold start), leaving root cause confidence very low?
- What happens when two independent incidents share a coincidentally overlapping service but are not actually related?
- What happens when a proposed remediation's rollback plan itself fails or cannot be validated?
- What happens when a designated approver is unavailable and a proposed remediation sits pending for an extended period?
- How does the system handle secrets/PII embedded inside unstructured runbook text or alert messages rather than in clearly labeled fields?
- What happens when revenue, SLA, or customer-impact data is missing or incomplete for a service involved in an incident — can the executive dashboard still show a partial view?
- What happens when a predictive forecast turns out to be wrong (predicted outage does not occur) — how is that tracked?

## Requirements *(mandatory)*

### Functional Requirements

#### Data Ingestion (BigQuery-Backed)

- **FR-001**: System MUST allow a user to upload JSON source files for each of the following data domains: alerts, telemetry, historical incidents, runbooks/SOPs, network topology & service dependencies, SLA definitions, and revenue impact.
- **FR-002**: System MUST automatically land uploaded files in cloud object storage and load them into BigQuery as structured, queryable tables without any manual schema mapping or manual transformation step performed by the uploading user. Records MUST be upserted using a per-domain natural identifier (or a derived hash key when no natural identifier is present) so that duplicate or re-submitted records update/are skipped rather than creating duplicate rows (see FR-006).
- **FR-003**: System MUST generate semantic embeddings for all runbook/SOP content at ingestion time and make those embeddings searchable immediately after ingestion completes.
- **FR-004**: System MUST make newly ingested data available to every downstream capability (correlation, root cause analysis, runbook retrieval, prediction, executive impact calculation) without any additional manual step.
- **FR-005**: System MUST validate uploaded files against the expected structure for their data domain and MUST report a clear, actionable error for any file that fails validation rather than silently accepting or partially loading it.
- **FR-006**: System MUST support re-upload of updated data (e.g., corrected SLA figures, new runbooks) without requiring a full system reset or loss of previously ingested history, matching records via the same per-domain identity key used for ingestion (FR-002).
- **FR-007**: System MUST show the uploading user the ingestion status (pending, in progress, succeeded, failed) of each uploaded file.

#### Multi-Agent Incident Intelligence (ADK)

- **FR-008**: System MUST implement six distinct, coordinated agent roles — Alert Correlation, Root Cause Analysis, Runbook Retrieval, Predictive Risk, Remediation, and Executive Impact — using the Agent Development Kit (ADK), each responsible for one stage of incident handling described below.
- **FR-009**: The Alert Correlation Agent MUST deduplicate and group related streaming alerts into a single incident cluster.
- **FR-010**: The Root Cause Analysis Agent MUST analyze correlated telemetry, topology, and historical incident data to produce a probable root cause, a confidence score, and supporting reasoning.
- **FR-011**: The Runbook Retrieval Agent MUST identify candidate remediation procedures using BigQuery Vector Search over embedded runbook content only (no keyword-based matching), and MUST output the matched runbook, its similarity score, and recommended actions.
- **FR-012**: The Predictive Risk Agent MUST use BigQuery ML over historical telemetry and trend data to output a predicted failure, an estimated time-to-failure window, a confidence level, and the services likely affected.
- **FR-013**: The Remediation Agent MUST produce a proposed remediation script, a corresponding rollback script, and a risk assessment, and MUST NOT allow either to execute without prior human approval.
- **FR-014**: The Executive Impact Agent MUST calculate and output the number of users impacted, revenue at risk, SLA credit exposure, and MTTR reduction in business-friendly terms.
- **FR-015**: Every agent output MUST be generated from data currently ingested in BigQuery for the active environment; no agent MAY rely on hardcoded example mappings, static canned answers, or fixed alert-to-resolution logic.

#### Alert Clustering & Root Cause Isolation (Milestone 1)

- **FR-016**: System MUST consolidate hundreds of related alerts arriving within a short window into a single incident record rather than displaying them as separate, unrelated items.
- **FR-017**: System MUST preserve traceability from a consolidated incident back to every original alert that was correlated into it.
- **FR-018**: System MUST present, for every incident, a chronological timeline, the related/affected services, and a visual service dependency graph.
- **FR-019**: System MUST present the probable root cause, its confidence score, and a plain-language explanation of the supporting evidence for every incident.
- **FR-020**: System MUST track every incident against a fixed status enum — Open, Investigating, Awaiting Approval, Remediating, Resolved, Closed — and allow users to distinguish currently open incidents (any pre-Resolved status) from resolved/historical ones within the same interface.

#### Runbook Retrieval & Safe Remediation (Milestone 2)

- **FR-021**: System MUST present, for an open incident, the matched runbook(s) together with the similarity score and recommended actions.
- **FR-022**: System MUST present a step-by-step remediation plan and a corresponding rollback plan for any proposed fix.
- **FR-023**: System MUST present an assessed risk level for every proposed remediation action.
- **FR-024**: System MUST require a designated human approver to explicitly review and approve a proposed remediation before any execution occurs.
- **FR-025**: System MUST record the approver's identity, decision (approve/reject), timestamp, and any comments for every remediation decision.
- **FR-026**: System MUST allow a rejected remediation to return the incident to an actionable state (e.g., select a different runbook, escalate) rather than leaving it stuck.
- **FR-027**: System MUST restrict remediation execution to a controlled sandbox/demonstration environment — a dedicated, isolated demo target service that the Remediation Agent operates on via real GCP API calls (e.g., Cloud Run Admin API) rather than a simulated/mocked response — and MUST make the rollback plan available if the executed fix does not resolve the issue.
- **FR-028**: System MUST clearly indicate when no runbook meets the minimum similarity/confidence threshold for an incident, rather than presenting a low-confidence guess as authoritative.

#### Predictive Risk & Resilience at Scale (Milestone 3)

- **FR-029**: System MUST continue accepting and clustering incoming alerts during bursts of at least 1,000 alerts per minute without dropping alerts, using a streaming ingestion path (Pub/Sub) feeding autoscaling compute (Cloud Run).
- **FR-030**: System MUST automatically scale its alert-processing capacity up and down with incoming load rather than requiring manual capacity changes.
- **FR-031**: System MUST detect and surface anomalous telemetry trends that deviate from established historical patterns, independent of whether a full outage prediction is triggered.
- **FR-032**: System MUST produce, for each predicted future failure, the predicted failure/outage, an estimated time-to-failure window, a confidence level, the affected services, and an explanation of why the prediction was made.
- **FR-033**: System MUST redact secrets and personally identifiable information from alert, telemetry, and log content before that content is displayed, stored for retrieval, or included in any generated summary or remediation script.

#### Executive Business Impact (Milestone 4)

- **FR-034**: System MUST calculate, for each incident or prediction, the estimated number of affected users/customers by combining the customer/user-count attribute on the ingested Revenue Impact Record with the set of services in the incident's blast radius from the dependency graph.
- **FR-035**: System MUST calculate revenue at risk and applicable SLA credit/penalty exposure for each incident.
- **FR-036**: System MUST track mean-time-to-resolution (MTTR) for incidents handled through the platform and report the estimated MTTR reduction versus the manual baseline.
- **FR-037**: System MUST present, in one consolidated view, current incidents, predicted incidents, resolution success rate, and estimated time saved for business stakeholders.
- **FR-038**: System MUST express all business-impact figures (revenue, customers, SLA exposure) in plain business terms rather than technical/system terms.

#### User Interface

- **FR-039**: System MUST provide the following distinct views: Live Incident Console, Incident Timeline, Alert Correlation View, Root Cause Analysis View, Runbook Recommendation View, Approval Console, Predictive Health Dashboard, and Executive Dashboard.
- **FR-040**: System MUST let an authorized user navigate from an incident in the Live Incident Console to its correlation, root cause, runbook, and approval detail views while keeping a consistent incident identity across all views.

#### Security & Governance

- **FR-041**: System MUST authenticate every end user via Firebase Authentication / Google Identity Platform sign-in issuing per-user identity and custom role claims (On-Call Engineer, Incident Commander, Approver, Executive Viewer, Administrator), and MUST enforce role-based access control derived from those claims — separate from the GCP IAM roles governing service-to-service access to GCP resources — so only authorized users can view sensitive incident data or approve/execute remediations.
- **FR-042**: System MUST store all credentials and secrets in a managed secret store (Secret Manager) and MUST NOT expose them in plaintext in the UI, logs, or generated scripts.
- **FR-043**: System MUST record every security-relevant action (data upload, incident access, approval decision, remediation execution) in an auditable log capturing the actor, timestamp, and action taken.
- **FR-044**: System MUST mask sensitive fields (e.g., customer identifiers, credentials embedded in free text) within ingested historical/reference data domains (incidents, runbooks, telemetry) so they are never exposed via agent outputs or dashboards.

### Non-Functional Requirements

#### Performance & Scalability

- **NFR-001**: System MUST sustain an incoming alert rate of at least 1,000 alerts per minute without alert loss or unacceptable processing delay.
- **NFR-002**: Alert-processing and analysis capacity MUST scale automatically with incoming load, without manual operator intervention, and scale back down when load subsides.
- **NFR-003**: System SHOULD produce a consolidated incident (root cause, correlated alerts, timeline) within a bounded time (target: within 5 minutes) of an alert storm beginning, so responders are not left waiting during an active incident.
- **NFR-004**: Newly ingested data MUST become usable by all agents within a bounded time after upload completes (target: within 5 minutes for a typical demo-sized dataset).

#### Security & Data Protection

- **NFR-005**: All access to incident data, approval actions, and dashboards MUST be authenticated (via Firebase Authentication / Google Identity Platform, per FR-041) and authorized; there MUST be no anonymous access to incident or business-impact data.
- **NFR-006**: No secret or credential value MUST ever appear in plaintext in any UI, log, exported report, or generated remediation/rollback script.
- **NFR-007**: Personally identifiable information present in source data MUST be redacted before being surfaced in any agent output, dashboard, or audit trail entry, while preserving enough surrounding context to remain useful for diagnosis.

#### Trust, Safety & Governance

- **NFR-008**: Every approval/rejection decision and every executed remediation or rollback action MUST be individually attributable to an actor and timestamp and retained for subsequent compliance review.
- **NFR-009**: No remediation action capable of altering a system MUST execute without an explicit prior human approval, regardless of alert volume or perceived urgency.
- **NFR-010**: Every automated determination shown to a user (root cause, runbook match, prediction, risk level) MUST include a human-readable rationale and a confidence or similarity indicator rather than a bare conclusion.
- **NFR-011**: All correlation, root-cause, retrieval, prediction, and remediation outputs MUST be derived solely from data ingested for the active environment; the system MUST NOT ship with, or fall back to, pre-baked example mappings unrelated to the uploaded data.

#### Reliability & Usability

- **NFR-012**: Temporary unavailability of any single analysis capability (e.g., prediction) MUST NOT prevent core incident visibility and alert correlation from continuing to function.
- **NFR-013**: Business-impact figures MUST be presented in terms a non-technical stakeholder can interpret without engineering assistance (currency amounts, customer counts, percentages, plain-language summaries).

### Key Entities *(include if feature involves data)*

- **Alert**: A raw signal from a monitoring source representing a single detected condition; carries severity, timestamp, source, affected resource, a description, and a per-source natural identifier (or derived hash key when absent) used to detect duplicate/re-uploaded records.
- **Incident**: A single, correlated cluster of one or more alerts representing one underlying problem; carries a status (Open, Investigating, Awaiting Approval, Remediating, Resolved, or Closed), timeline, root cause, confidence score, correlated alert set, and affected services.
- **Telemetry Reading**: A time-series operational data point (metric/log/trace signal) used to support correlation, root cause analysis, and prediction.
- **Historical Incident Record**: A previously resolved incident retained as precedent, used to inform root cause reasoning and pattern-based prediction.
- **Runbook / SOP**: A documented remediation procedure with applicability context, ordered steps, and a semantic embedding used for similarity retrieval.
- **Service Topology / Dependency Graph**: The set of relationships describing how services and infrastructure components depend on one another; used to scope blast radius and root cause candidates.
- **SLA Definition**: A contractual service-level commitment (e.g., uptime target, credit terms) associated with a service or customer, used to compute breach exposure.
- **Revenue Impact Record**: Business/financial value and an associated customer/user-count attribute for a service or customer segment, used to estimate revenue at risk and affected-customer counts during an incident.
- **Remediation Action**: A proposed fix paired with its rollback counterpart and an assessed risk level, tied to a specific incident.
- **Approval Decision**: A record of a human approver's accept/reject decision on a remediation action, including actor, timestamp, and rationale.
- **Risk Forecast / Prediction**: A forward-looking statement about a likely future failure, including confidence, time-to-failure window, and affected services.
- **Audit Log Entry**: An immutable record of a security- or workflow-relevant action, including actor, timestamp, and action taken.
- **User / Role**: An individual, authenticated via Firebase Authentication / Google Identity Platform, with an assigned role (e.g., On-Call Engineer, Incident Commander, Approver, Executive Viewer, Administrator) that governs what they can view or approve.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 7 supported data domains (alerts, telemetry, historical incidents, runbooks, topology, SLA, revenue) can be uploaded and become usable for analysis without any manual data-mapping step.
- **SC-002**: A burst of 1,000+ related alerts arriving within one minute is consolidated into a single incident visible to responders within 5 minutes of the burst starting.
- **SC-003**: Responders can identify a probable root cause with a supporting explanation for at least 80% of demo incidents without manually cross-referencing telemetry or topology themselves.
- **SC-004**: For incidents with a matching precedent in the ingested runbook library, a relevant runbook recommendation is surfaced at least 90% of the time.
- **SC-005**: 100% of executed remediation actions have a recorded human approval decision; zero remediations execute without one.
- **SC-006**: At least one impending failure is correctly predicted ahead of it occurring during the demo scenario, with a stated reason and lead time.
- **SC-007**: Executives can view current revenue at risk, SLA exposure, and affected-customer counts for any active incident in a single dashboard view, without engineering assistance to interpret the figures.
- **SC-008**: Incidents handled through the platform show at least a 30% reduction in mean-time-to-resolution compared to the documented manual baseline.
- **SC-009**: Zero instances of secret or PII leakage are found in the UI, logs, or generated scripts during a security audit review of a demo run.
- **SC-010**: 100% of alerts submitted during a 1,000+ alerts/minute burst are accounted for within the resulting incident cluster(s); none are silently dropped.

## Glossary

- **ADK (Agent Development Kit)**: The mandated framework used to build and coordinate the platform's six specialized AI agents.
- **Alert Storm**: A short-window burst of many related alerts triggered by the same underlying condition.
- **BigQuery**: The mandated Google Cloud data warehouse serving as the system of record for all ingested data.
- **BigQuery ML**: The mandated Google Cloud capability used to build the predictive risk forecasting models directly over data stored in BigQuery.
- **BigQuery Vector Search**: The mandated Google Cloud capability used to perform semantic similarity search over embedded runbook content stored in BigQuery.
- **Blast Radius**: The set of services, customers, or systems affected by a given incident, derived from the dependency graph.
- **Embedding**: A numeric representation of text (e.g., a runbook) that enables semantic similarity search, as opposed to keyword matching.
- **Gemini**: The mandated large language model (accessed via Vertex AI) powering the agents' reasoning, explanation, and generation outputs.
- **Human-in-the-Loop Approval**: The mandatory workflow step requiring an authorized person to review and approve a remediation before it can execute.
- **Incident Cluster**: The consolidated group of correlated alerts treated as a single incident.
- **MTTR (Mean Time To Resolution)**: The average time taken to fully resolve an incident, a key measure of operational efficiency.
- **PII (Personally Identifiable Information)**: Any data that could identify a specific individual, which must be redacted before display or storage for retrieval.
- **Root Cause Analysis (RCA)**: The process of determining the most probable underlying cause of an incident from supporting evidence.
- **Runbook / SOP (Standard Operating Procedure)**: A documented, pre-approved procedure describing how to resolve a known type of problem.
- **Sandbox Execution**: Running a remediation action in an isolated, non-production environment for safe validation/demonstration.
- **SLA (Service Level Agreement)**: A contractual commitment defining expected service performance and the penalties/credits owed if it is breached.
- **Vector Search**: A retrieval technique that finds the most similar items to a query by comparing their embeddings rather than their literal text.

## Assumptions

- The hackathon scoring rubric mandates explicit, visible use of specific Google Cloud services (BigQuery, BigQuery Vector Search, BigQuery ML, Cloud Storage, Cloud Run, Gemini via Vertex AI, ADK, Pub/Sub, Cloud Scheduler, Cloud Logging, Secret Manager, IAM); these are treated as fixed constraints of this feature rather than open implementation choices, which is why they appear directly in the requirements above.
- Looker Studio and Firestore are optional/supplementary per the source brief and are not required for core acceptance of this feature.
- "Streaming" alert ingestion for demo purposes is simulated via uploaded JSON files representing an alert burst rather than a live production monitoring integration.
- Remediation execution occurs only in a sandboxed/demonstration environment — a dedicated demo target service acted on via real GCP API calls, not a simulated response — and executing remediations against live production infrastructure is out of scope for this feature.
- Users are internal organizational personnel (on-call engineers, incident commanders, approvers, executives, administrators) who already have corporate identity credentials; new end-user account registration is out of scope.
- Similarity/confidence thresholds used to decide a "confident match" for root cause, runbook retrieval, and prediction are configurable and will be tuned during implementation rather than fixed by this spec.
- Meaningful root-cause and prediction confidence depends on having some ingested historical data; a completely empty history is expected to degrade gracefully to low-confidence output rather than to a high-confidence result.
- "1,000+ alerts per minute" is treated as a peak burst target for the demo scenario rather than a required sustained, continuous load.
- Audit log retention follows standard organizational/regulatory practice; no specific named regulation (e.g., HIPAA, PCI-DSS) was indicated in the source request.
