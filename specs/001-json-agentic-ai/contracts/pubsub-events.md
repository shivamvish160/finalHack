# Contract: Pub/Sub Event Topics (Agent-to-Agent Communication)

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24

All messages are JSON, UTF-8, with a common envelope:

```json
{
  "eventId": "uuid",
  "eventType": "string",   // matches the topic's canonical event name below
  "occurredAt": "RFC3339",
  "incidentId": "string|null",
  "payload": { }
}
```

Every subscriber is a Cloud Run push subscription (per-topic, independently
scalable per NFR-002/FR-030) with a dead-letter topic
(`<topic>-dlq`) after 5 delivery attempts, so a stuck message never blocks
the rest of the pipeline (NFR-012). Publishing to BigQuery/Firestore always
happens **before** publishing the next event (research.md §6), so a
consumer that reads BigQuery/Firestore after receiving an event always sees
consistent state.

## `ingestion.file-uploaded`
Published by: Eventarc (GCS object-finalize) → this topic.
Consumed by: `ingestion-service`.
```json
{ "payload": { "domain": "alerts|telemetry|incidents|runbooks|topology|sla|revenue", "gcsUri": "string", "jobId": "string", "uploadedBy": "uid" } }
```

## `ingestion.completed`
Published by: `ingestion-service` after a successful MERGE (+ embedding
generation for runbooks).
Consumed by: nothing blocking (informational; updates `ingestion_jobs` doc,
may be used by demo tooling to sequence uploads).
```json
{ "payload": { "jobId": "string", "domain": "string", "rowsUpserted": 0 } }
```

## `alerts.raw`
Published by: `ingestion-service` (fan-out of an uploaded/simulated alert
burst) or `/scripts/demo/simulate-alert-storm.py` directly, for the
≥1000/min load scenario (NFR-001).
Consumed by: Agent 1 (Alert Correlation), pushed to `agent-orchestrator`.
```json
{ "payload": { "alertId": "string", "serviceId": "string", "severity": "string", "description": "string", "firstSeenAt": "RFC3339" } }
```

## `incidents.correlated`
Published by: Agent 1, after clustering one-or-more alerts into an incident
(FR-009, AC-2.1).
Consumed by: Agent 2 (Root Cause Analysis).
```json
{ "incidentId": "string", "payload": { "correlatedAlertIds": ["string"], "affectedServices": ["string"] } }
```

## `incidents.root_cause_identified`
Published by: Agent 2 (FR-010).
Consumed by: Agent 3 (Runbook Retrieval).
```json
{ "incidentId": "string", "payload": { "rootCause": "string", "confidence": 0.0, "reasoning": "string" } }
```

## `incidents.runbook_matched`
Published by: Agent 3 (FR-011). If no match clears the confidence
threshold, `runbookId` is `null` and `belowThreshold` is `true`
(FR-028/AC-3.5) — the event still fires so the incident can proceed to a
human-driven path instead of stalling silently.
Consumed by: Agent 5 (Remediation).
```json
{ "incidentId": "string", "payload": { "runbookId": "string|null", "similarityScore": 0.0, "belowThreshold": false, "recommendedActions": ["string"] } }
```

## `remediation.proposed`
Published by: Agent 5, after generating fix/rollback/risk — incident moves
to `Awaiting Approval` (FR-013, FR-022, FR-023).
Consumed by: `api-gateway` (surfaces via `/approvals`), no automatic
execution consumer exists for this event (NFR-009 — see research.md §7).
```json
{ "incidentId": "string", "payload": { "actionId": "string", "riskLevel": "string" } }
```

## `remediation.approved` / `remediation.rejected`
Published by: `api-gateway`'s `/approvals/{actionId}/decision` handler
**only** (FR-024/FR-025).
Consumed by: Agent 5's execution tool (approved only); rejected path
publishes back to incident state (`Awaiting Approval → Investigating`,
FR-026).
```json
{ "incidentId": "string", "payload": { "actionId": "string", "approverUid": "string", "comments": "string" } }
```

## `remediation.executed`
Published by: Agent 5's execution tool, after the real Cloud Run Admin API
call against `demo-target-service` completes (Clarification #2, FR-027).
Consumed by: Agent 6 (Executive Impact), UI via Firestore projection.
```json
{ "incidentId": "string", "payload": { "actionId": "string", "outcome": "succeeded|failed", "apiResponse": {} } }
```

## `predictions.tick`
Published by: Cloud Scheduler (periodic cadence, independent of alert
traffic — AC-4.1 requires predictions *before* any alert fires).
Consumed by: Agent 4 (Predictive Risk).
```json
{ "payload": { "scheduledFor": "RFC3339" } }
```

## `risk.forecast.created`
Published by: Agent 4, per forecast/anomaly (FR-012, FR-031, FR-032).
Consumed by: Agent 6 (Executive Impact); optionally read (via BigQuery,
not direct coupling) by Agent 2 as supporting evidence.
```json
{ "payload": { "forecastId": "string", "serviceId": "string", "predictedFailure": "string", "confidence": 0.0, "isAnomalyOnly": false } }
```

## `executive.metrics.updated`
Published by: Agent 6, after recomputing `core.executive_metrics`
(FR-014, FR-034–FR-038). Also triggered by its own Cloud Scheduler cadence,
not only by upstream events.
```json
{ "payload": { "snapshotTs": "RFC3339" } }
```
