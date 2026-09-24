# Contract: `api-gateway` REST API (Backend-for-Frontend)

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24 (re-derived for the
existing-warehouse premise — all `/uploads/*` endpoints from the prior
version of this contract are removed; there is no ingestion in this
feature)

All endpoints require a Firebase Authentication ID token (`Authorization:
Bearer <token>`); `api-gateway` verifies the token and reads the `role`
custom claim for authorization (FR-035, NFR-005). Every request that views
incident data or performs a security-relevant action writes a structured
Cloud Logging audit entry (FR-037, `data-model.md` §10) — there is no
`audit_log` BigQuery table. Roles:
`OnCallEngineer | IncidentCommander | Approver | ExecutiveViewer | Administrator`.

This is an interface contract (request/response shape), not an
implementation — handlers are built in Phase 3+ (`/audi.tasks` /
`/audi.implement`). **Primary path for live UI state** (incident status,
approval queue, predictions, executive metrics) is a direct Firestore
client-SDK realtime listener (research.md §19); the REST endpoints below
exist for on-demand BigQuery-backed drill-downs, non-realtime/SSR clients,
and the one write path that must be gated server-side (approval decisions).

## Incidents (User Story 1)

### `GET /incidents?status=open|resolved|all`
Response: array of
`{ incidentId, status, openedAt, rootCause, confidence, affectedServices }`
(BigQuery `incidents`, live query).

### `GET /incidents/{incidentId}`
Response: full incident — status, root cause, confidence, reasoning,
affected services, correlated alert count (FR-009/FR-010).

### `GET /incidents/{incidentId}/alerts`
Response: array of original `alert_stream` rows correlated into the
incident via `correlated_alerts` (FR-007), each carrying a
`topologyMappingStatus: "Mapped"|"Unmapped"` flag (FR-005). `message` is
redacted before this response is built (research.md §15).

### `GET /incidents/{incidentId}/timeline`
Response: ordered array merging `alert_stream` timestamps (via
`correlated_alerts`) with the Firestore `stage_history` array (FR-008;
`data-model.md` §2/§9 — there is no BigQuery timeline-events table).

### `GET /incidents/{incidentId}/dependency-graph`
Response: `{ nodes: [{nodeId,nodeName,nodeType,region,status,mapped:bool}],
edges: [{from,to,basis:"same_region_type"|"historical_cooccurrence"}] }`
— edges are the data-driven inference from research.md §7, not a stored
topology edge table (none exists in `network_nodes`).

## Runbook retrieval & remediation (User Story 2)

### `GET /incidents/{incidentId}/runbook-matches`
Response: array of `{ runbookId, title, similarityScore, recommendedActions,
belowThreshold }` from `VECTOR_SEARCH` (FR-012/FR-013) —
`belowThreshold=true` with an empty/low-confidence set is a valid, clearly
labeled response, never presented as an authoritative guess (FR-014,
AC-2.5).

### `GET /incidents/{incidentId}/remediation`
Response: the current Firestore `approvals/{actionId}` document for this
incident — `fixScript`, `rollbackScript` (both redacted), `riskLevel`,
`status`, and, once executed, the real `executionResult` (mirrors
`remediation_logs` once appended).

### `GET /incidents/{incidentId}/postmortem`
Response: the `incident_postmortems` row for this incident if one exists
(`404` otherwise) — `rootCauseSummary`, `timelineSummary`,
`remediationSummary`, `businessImpactSummary`, `fullReportMarkdown`,
`version`, `generatedAt` (FR-031/FR-032).

## Approval workflow (User Story 2)

### `GET /approvals?status=pending`
Roles: Approver, IncidentCommander, Administrator.
Response: array of pending Firestore `approvals/{actionId}` docs + incident
summary.

### `POST /approvals/{actionId}/decision`
Roles: Approver, IncidentCommander, Administrator.
Request: `{ "decision": "approve" | "reject", "comments": "string" }`
Response `200`: `{ "actionId", "decision", "decidedAt" }`
Effect: updates the Firestore `approvals/{actionId}` doc (approver uid +
timestamp + comments, FR-018), writes the Cloud Logging audit entry, then
publishes `remediation.approved` or `remediation.rejected`. This is the
**only** code path that can lead to real execution (research.md §12) — the
endpoint itself never executes anything synchronously, and never touches
BigQuery directly (only the eventual `remediation.executed` handler appends
to `remediation_logs`).

## Predictive risk (User Story 3)

### `GET /predictions?activeOnly=true`
Response: array of Firestore `predictions/{serviceName}__{alertType}` docs
(FR-022) — predicted failure, window, confidence, affected services,
rationale — distinguished from `/incidents` (never a status value,
Clarification #5).

### `GET /predictions/anomalies`
Response: array of flagged anomaly-only entries (`isAnomalyOnly: true`,
FR-023/AC-3.2) not yet meeting the full-prediction threshold.

## Executive dashboard (User Story 4)

### `GET /executive/summary`
Roles: ExecutiveViewer, IncidentCommander, Administrator.
Response: the Firestore `executive_metrics/latest` document (FR-029) plus
current vs. predicted incident counts — all figures in plain business
terms (currency, counts, percentages; FR-030/NFR-013).

## Auth/session

### `GET /me`
Response: `{ "uid", "role", "displayName" }` — resolved from the verified ID
token's custom claims; used by the frontend to gate navigation consistently
across all 8 UI pages (FR-034).

## Error shape (all endpoints)

```json
{ "error": { "code": "string", "message": "string" } }
```
`401` missing/invalid token, `403` authenticated but role not permitted,
`404` unknown resource, `422` validation failure, `500` unexpected.
