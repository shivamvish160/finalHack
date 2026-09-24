# Contract: `api-gateway` REST API (Backend-for-Frontend)

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24

All endpoints require a Firebase Authentication ID token (`Authorization:
Bearer <token>`) unless noted; `api-gateway` verifies the token and reads
the `role` custom claim for authorization (FR-041, NFR-005). Every request
that views incident data or performs a security-relevant action writes a
`core.audit_log` row (FR-043). Roles:
`OnCallEngineer | IncidentCommander | Approver | ExecutiveViewer | Administrator`.

This is an interface contract (request/response shape), not an
implementation — handlers are built in Phase 3+ (`/audi.tasks` /
`/audi.implement`).

## Uploads (User Story 1)

### `POST /uploads/{domain}`
`domain ∈ {alerts, telemetry, incidents, runbooks, topology, sla, revenue}`.
Roles: OnCallEngineer, IncidentCommander, Administrator.

Request: `{ "filename": string, "contentType": "application/json" }`

Response `200`:
```json
{ "jobId": "string", "uploadUrl": "https://storage.googleapis.com/...", "expiresAt": "RFC3339" }
```
Returns a v4 signed URL for direct-to-GCS upload; the client PUTs the file
body to `uploadUrl`. GCS object-finalize → Eventarc → Pub/Sub
`ingestion.file-uploaded` (see `pubsub-events.md`) drives the rest of
ingestion.

### `GET /uploads/{jobId}`
Response `200`: `{ "jobId", "domain", "filename", "status": "pending|in_progress|succeeded|failed", "errorReason": "string|null", "updatedAt": "RFC3339" }`
(FR-007; mirrors the `ingestion_jobs/{job_id}` Firestore doc.)

## Incidents (User Story 2)

### `GET /incidents?status=open|resolved|all`
Roles: any authenticated role except ExecutiveViewer-only accounts still
see a read-only summary. Response: array of
`{ incidentId, status, openedAt, rootCause, confidence, affectedServices }`.

### `GET /incidents/{incidentId}`
Response: full incident (status, root cause, confidence, reasoning,
affected services, dependency graph edges, correlated alert count).

### `GET /incidents/{incidentId}/alerts`
Response: array of original alerts correlated into the incident (FR-017).

### `GET /incidents/{incidentId}/timeline`
Response: ordered `core.incident_timeline_events` rows (FR-018).

### `GET /incidents/{incidentId}/dependency-graph`
Response: `{ nodes: [{serviceId,name,tier}], edges: [{from,to,relationshipType}] }`
scoped to the incident's blast radius (FR-018, FR-034).

## Runbook retrieval (User Story 3)

### `GET /incidents/{incidentId}/runbook-matches`
Response: array of
`{ runbookId, title, similarityScore, recommendedActions, belowThreshold }`
— `belowThreshold=true` and an empty/low-confidence set is a valid, clearly
labeled response, never a guess presented as authoritative (FR-028, AC-3.5).

### `GET /incidents/{incidentId}/remediation`
Response: latest `core.remediation_actions` row — `fixScript`,
`rollbackScript` (both already redacted), `riskLevel`, `status`.

## Approval workflow (User Story 3)

### `GET /approvals?status=pending`
Roles: Approver, IncidentCommander, Administrator.
Response: array of pending `core.remediation_actions` (+ incident summary).

### `POST /approvals/{actionId}/decision`
Roles: Approver, IncidentCommander, Administrator.
Request: `{ "decision": "approve" | "reject", "comments": "string" }`
Response `200`: `{ "actionId", "decision", "decidedAt" }`
Effect: writes `core.approval_decisions` (approver uid + timestamp +
comments, FR-025), then publishes `remediation.approved` or
`remediation.rejected`. This is the **only** code path that can lead to
real execution (research.md §7) — the endpoint itself never executes
anything synchronously.

## Predictive risk (User Story 4)

### `GET /predictions?activeOnly=true`
Response: array of `core.risk_forecasts` rows (predicted failure, window,
confidence, affected services, rationale) — distinguished from
`/incidents` (FR-032, AC-5.4, Clarification #5).

### `GET /predictions/anomalies`
Response: array of flagged anomaly trends not yet meeting the
full-prediction threshold (FR-031, AC-4.2).

## Executive dashboard (User Story 5)

### `GET /executive/summary`
Roles: ExecutiveViewer, IncidentCommander, Administrator.
Response: latest `core.executive_metrics` row plus current vs. predicted
incident counts (FR-037/FR-038, all figures in plain business terms —
currency, counts, percentages).

## Auth/session

### `GET /me`
Response: `{ "uid", "role", "displayName" }` — resolved from the verified
ID token's custom claims; used by the frontend to gate UI navigation
consistently across all 8 pages (FR-040).

## Error shape (all endpoints)

```json
{ "error": { "code": "string", "message": "string" } }
```
`401` missing/invalid token, `403` authenticated but role not permitted,
`404` unknown resource, `422` validation failure (e.g. bad upload domain),
`500` unexpected.
