# Contract: Pub/Sub Event Topics (Agent-to-Agent Communication)

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24 (re-derived for the
existing-warehouse premise — all `ingestion.*` topics from the prior version
of this contract are removed; there is no ingestion in this feature.
`alerts.raw` is renamed `alerts.replay` to make its real source explicit)

All messages are JSON, UTF-8, with a common envelope:

```json
{
  "eventId": "uuid",
  "eventType": "string",
  "occurredAt": "RFC3339",
  "incidentId": "string|null",
  "payload": {}
}
```

Every subscriber is a Cloud Run push subscription with its own tuned
autoscaling (research.md §17) and a dead-letter topic (`<topic>-dlq`) after
5 delivery attempts (NFR-012). Whenever a handler writes to one of the four
FR-039 BigQuery tables, that write happens **before** publishing the next
event, and before the corresponding Firestore projection update, so a
consumer never observes an event ahead of the state it describes.

## `alerts.replay`
Published by: `alert-replay-service`, reading `sre_telemetry.alert_stream`
read-only and looping over the ~3,000 rows at a controlled rate to sustain
≥1,000 msgs/min (FR-004, NFR-001; research.md §11).
Consumed by: Agent 1 (Alert Correlation).
```json
{
  "payload": {
    "replayEventId": "uuid",
    "replaySessionId": "uuid (shared by one bounded replay run)",
    "sourceAlert": {
      "alertId": "string", "nodeId": "string", "serviceName": "string",
      "severity": "string", "alertType": "string",
      "message": "string (redacted before publish)",
      "measuredValue": 0.0, "originalTimestamp": "RFC3339"
    }
  }
}
```
Dedup/clustering key is `replayEventId`, never `sourceAlert.alertId`
(Clarification #2) — the same underlying row reappears many times across a
demo run and must be treated as a fresh occurrence each time.

## `incidents.correlated`
Published by: Agent 1, after clustering one-or-more replayed alerts into an
incident and writing `correlated_alerts`/`incidents` (FR-006, AC-1.1).
Consumed by: Agent 2 (Root Cause Analysis).
```json
{ "incidentId": "string", "payload": { "correlatedAlertIds": ["string"], "affectedServices": ["string"] } }
```

## `incidents.root_cause_identified`
Published by: Agent 2, after persisting root cause/confidence/reasoning to
`incidents` (FR-009).
Consumed by: Agent 3 (Runbook Retrieval).
```json
{ "incidentId": "string", "payload": { "rootCause": "string", "confidence": 0.0, "reasoning": "string" } }
```

## `incidents.runbook_matched`
Published by: Agent 3 (FR-012). If no match clears the confidence
threshold, `runbookId` is `null` and `belowThreshold` is `true`
(FR-014/AC-2.5) — the event still fires so the incident proceeds to a
human-driven path instead of stalling silently.
Consumed by: Agent 5 (Remediation).
```json
{ "incidentId": "string", "payload": { "runbookId": "string|null", "similarityScore": 0.0, "belowThreshold": false, "recommendedActions": ["string"] } }
```

## `remediation.proposed`
Published by: Agent 5, after writing the proposal to Firestore
`approvals/{actionId}` (status `Proposed`) — incident's Firestore stage
moves to `Awaiting Approval` (FR-015, FR-016).
Consumed by: `api-gateway` (surfaces via `/approvals`); no automatic
execution consumer exists for this event (NFR-009 — research.md §12).
```json
{ "incidentId": "string", "payload": { "actionId": "string", "riskLevel": "string" } }
```

## `remediation.approved` / `remediation.rejected`
Published by: `api-gateway`'s `/approvals/{actionId}/decision` handler
**only** (FR-017/FR-018).
Consumed by: Agent 5's execution tool (approved only); the rejected path
returns the incident's Firestore stage to `Investigating` (FR-021) — no
BigQuery write occurs for a rejection.
```json
{ "incidentId": "string", "payload": { "actionId": "string", "approverUid": "string", "comments": "string" } }
```

## `remediation.executed`
Published by: Agent 5's execution tool, after the real Cloud Run Admin API
call against `demo-target-service` completes and the outcome is appended to
`remediation_logs` (FR-019, FR-020).
Consumed by: the orchestrator (marks `incidents.status = 'Resolved'` on
success and publishes `incidents.resolved`; on failure, surfaces the
rollback plan and keeps the incident in `Remediating`), and the UI via the
Firestore `approvals/{actionId}` projection.
```json
{ "incidentId": "string", "payload": { "actionId": "string", "outcome": "succeeded|failed", "apiResponse": {} } }
```

## `incidents.resolved`
Published by: the orchestrator immediately after setting
`incidents.status = 'Resolved'`.
Consumed by: Agent 6 (Executive Impact) — triggers the postmortem `MERGE`
(FR-031/FR-032) and an executive-metrics recompute in the same handler.
```json
{ "incidentId": "string", "payload": { "resolvedAt": "RFC3339" } }
```

## `predictions.tick`
Published by: Cloud Scheduler (periodic cadence, independent of alert
traffic — AC-3.1 requires predictions *before* any alert for that failure
fires).
Consumed by: Agent 4 (Predictive Risk).
```json
{ "payload": { "scheduledFor": "RFC3339" } }
```

## `risk.forecast.created`
Published by: Agent 4, per forecast/anomaly, after writing the Firestore
`predictions/{serviceName}__{alertType}` doc (FR-022, FR-023) — **not** a
BigQuery write (research.md §2 boundary rule).
Consumed by: no hard dependency; UI reads Firestore directly. Optionally
read (via BigQuery historical context, not direct coupling) by Agent 2 as
supporting evidence for a later incident.
```json
{ "payload": { "serviceName": "string", "alertType": "string", "predictedFailure": "string", "confidence": 0.0, "isAnomalyOnly": false } }
```

## `executive.metrics.updated`
Published by: Agent 6, after recomputing and writing Firestore
`executive_metrics/latest` (FR-027–FR-030). Triggered by `incidents.resolved`
and independently by its own Cloud Scheduler cadence.
```json
{ "payload": { "snapshotTs": "RFC3339" } }
```
