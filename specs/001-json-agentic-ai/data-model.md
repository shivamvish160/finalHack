# Phase 1 Data Model: SRE Agentic AI Incident Prevention & Resolution Platform

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24
**Prerequisite**: [research.md](./research.md)

This document describes how the **already-provisioned and populated**
BigQuery warehouse is queried and written to by each agent — it is **not**
a DDL/schema-creation document. No `CREATE TABLE` statement appears anywhere
in this file for the 9 existing warehouse tables (`alert_stream`,
`network_nodes`, `runbooks`, `embedding_model`, `customer_accounts`,
`incidents`, `correlated_alerts`, `remediation_logs`,
`incident_postmortems`) — all nine already exist (FR-001/Out of Scope). The
only new schema artifacts this feature introduces are a BigQuery ML model in
a new, platform-owned dataset (§5) and several Firestore collections (§6),
neither of which are part of "the warehouse".

Per [research.md §8](./research.md#8-schema-verification-discipline-for-non-enumerated-existing-tables):
column names for `alert_stream`, `network_nodes`, `runbooks`/
`embedding_model`, `customer_accounts`, and `incident_postmortems` are taken
verbatim from spec.md (fully enumerated there). Column names for `incidents`
and `remediation_logs` beyond their documented key/linkage columns are
**illustrative placeholders** pending `INFORMATION_SCHEMA.COLUMNS`
verification at implementation time.

## 1. Existing warehouse tables (read reference)

| Table | Rows (approx) | Documented columns | Write access from this platform |
|---|---|---|---|
| `sre_telemetry.alert_stream` | ~3,000 | `alert_id, node_id, service_name, severity, alert_type, message, measured_value, timestamp` | **Read-only** (FR-039) |
| `sre_topology.network_nodes` | ~64 | `node_id, node_name, node_type, region, ip_address, status` | **Read-only** |
| `sre_knowledge_base.runbooks` | ~20 | `runbook_id, ..., embedding ARRAY<FLOAT64>(768)` (steps/rollback/risk columns per entity description; exact names to verify) | **Read-only** |
| `sre_knowledge_base.embedding_model` | n/a (model ref) | Remote model over `text-embedding-005` | **Read-only** (queried via `AI.GENERATE_EMBEDDING`/`ML.GENERATE_EMBEDDING`) |
| `sre_incident_mart.customer_accounts` | ~45 | `customer_id, customer_name, service_name, tier, monthly_recurring_revenue, sla_uptime_target_pct, sla_credit_rate_per_hour, user_count` (assumed, per spec Clarification — verify at implementation time) | **Read-only** |
| `sre_incident_mart.incidents` | ~18 existing + platform-created | `incident_id, status, root_cause, root_cause_confidence, root_cause_reasoning, opened_at, resolved_at, ...` (placeholder beyond `incident_id`/`status`) | **Insert new / update existing rows** |
| `sre_incident_mart.correlated_alerts` | grows with platform use | `incident_id, alert_id` (many-to-one link) | **Insert new links** |
| `sre_incident_mart.remediation_logs` | historical + platform-appended | `incident_id, runbook_id, ...` (placeholder beyond linkage columns) | **Append new outcome rows** |
| `sre_incident_mart.incident_postmortems` | 0 (empty) | `incident_id, generated_at, root_cause_summary, timeline_summary, remediation_summary, business_impact_summary, full_report_markdown, version` (fully specified by spec Clarification) | **Upsert via MERGE** |

Documented join paths (FR-005), all enforced as `LEFT JOIN` so an
unresolved relationship never drops the row — the unresolved side is
surfaced as `Unmapped` rather than filtered out:

```text
alert_stream.node_id       -> network_nodes.node_id
alert_stream.service_name  -> customer_accounts.service_name
correlated_alerts.incident_id -> incidents.incident_id
correlated_alerts.alert_id    -> alert_stream.alert_id
remediation_logs.incident_id  -> incidents.incident_id
remediation_logs.runbook_id   -> runbooks.runbook_id
incident_postmortems.incident_id -> incidents.incident_id
```

**Security note**: every `@param` below is a named BigQuery query
parameter (research.md §18) — never string-concatenated.

---

## 2. Agent 1 — Alert Correlation Agent (FR-006, FR-007, FR-008, FR-011)

Consumes `alerts.replay` envelopes (research.md §11). For each envelope,
resolves topology and checks the live Firestore `pending_alerts` window
(short-TTL, see §6) for other envelopes sharing `node_id`/`service_name`/an
inferred dependency signal (research.md §7) within the clustering time
window.

```sql
-- Topology resolution + Unmapped marking for a batch of node_ids in the window (FR-005)
SELECT n.node_id, n.node_name, n.node_type, n.region, n.status
FROM UNNEST(@node_ids) AS node_id
LEFT JOIN `sre_topology.network_nodes` AS n USING (node_id);
-- node_id values with no matching row are marked 'Unmapped' in the dependency view.

-- Precedent check: has this node/service combination clustered into an
-- incident before? (signal for same-vs-separate-incident decisions, FR-011)
SELECT DISTINCT ca.incident_id, i.status
FROM `sre_incident_mart.correlated_alerts` AS ca
JOIN `sre_telemetry.alert_stream` AS al USING (alert_id)
JOIN `sre_incident_mart.incidents` AS i USING (incident_id)
WHERE al.node_id IN UNNEST(@node_ids) OR al.service_name IN UNNEST(@service_names)
ORDER BY i.opened_at DESC
LIMIT 20;
```

On forming/updating a cluster:

```sql
-- New incident (or UPDATE if the orchestrator already created one for this cluster)
INSERT INTO `sre_incident_mart.incidents` (incident_id, status, opened_at)
VALUES (@incident_id, 'Open', CURRENT_TIMESTAMP());

-- Link every correlated alert (FR-006/FR-007) — natural alert_id, not replay_event_id
INSERT INTO `sre_incident_mart.correlated_alerts` (incident_id, alert_id)
SELECT @incident_id, alert_id FROM UNNEST(@alert_ids) AS alert_id;
```

The chronological timeline (FR-008) is assembled at read time by merging
(a) `correlated_alerts` → `alert_stream.timestamp`/`original_timestamp` per
alert and (b) the Firestore `incidents/{incident_id}.stage_history` array
(§6) recording each workflow-stage transition — there is no BigQuery
timeline-events table (research.md §2 boundary rule).

## 3. Agent 2 — Root Cause Analysis Agent (FR-009)

```sql
-- Every alert correlated into this incident, with topology resolved
SELECT
  al.alert_id, al.node_id, al.service_name, al.severity, al.alert_type,
  al.message, al.measured_value, al.timestamp,
  n.node_name, n.node_type, n.region, n.status AS node_status,
  IF(n.node_id IS NULL, 'Unmapped', 'Mapped') AS topology_mapping_status
FROM `sre_incident_mart.correlated_alerts` AS ca
JOIN `sre_telemetry.alert_stream` AS al USING (alert_id)
LEFT JOIN `sre_topology.network_nodes` AS n ON al.node_id = n.node_id
WHERE ca.incident_id = @incident_id;

-- Historical precedent: past incidents/remediations touching the same services
SELECT i.incident_id, i.root_cause, i.root_cause_confidence, i.status,
       r.runbook_id, r.executed_at
FROM `sre_incident_mart.incidents` AS i
LEFT JOIN `sre_incident_mart.remediation_logs` AS r USING (incident_id)
WHERE i.incident_id != @incident_id
  AND EXISTS (
    SELECT 1 FROM `sre_incident_mart.correlated_alerts` AS ca2
    JOIN `sre_telemetry.alert_stream` AS al2 USING (alert_id)
    WHERE ca2.incident_id = i.incident_id
      AND al2.service_name IN UNNEST(@current_service_names))
ORDER BY i.opened_at DESC
LIMIT 10;
```

`message` content is passed through the redaction utility (research.md §15)
before it ever reaches the Gemini prompt. Output (root cause, confidence,
reasoning) is persisted:

```sql
UPDATE `sre_incident_mart.incidents`
SET root_cause = @root_cause,
    root_cause_confidence = @confidence,
    root_cause_reasoning = @reasoning,
    status = 'Investigating'
WHERE incident_id = @incident_id;
```

## 4. Agent 3 — Runbook Retrieval Agent (FR-012, FR-013, FR-014)

Query-time embedding + `VECTOR_SEARCH`, exact syntax per research.md §3:

```sql
SELECT base.runbook_id, base.title, base.risk_level, base.steps,
       base.rollback_steps, distance AS vector_distance
FROM VECTOR_SEARCH(
  TABLE `sre_knowledge_base.runbooks`, 'embedding',
  (SELECT ml_generate_embedding_result AS query_embedding
   FROM AI.GENERATE_EMBEDDING(
     MODEL `sre_knowledge_base.embedding_model`,
     (SELECT @query_text AS content),
     STRUCT('RETRIEVAL_QUERY' AS task_type))),
  query_column_to_search => 'query_embedding',
  top_k => 5, distance_type => 'COSINE')
ORDER BY vector_distance ASC;
```

`@query_text` is built from the incident's `root_cause_reasoning` plus a
small, redacted sample of its correlated alert `message` values. A
configurable similarity threshold on `vector_distance` decides
`belowThreshold` (FR-014/AC-2.5) — if no row clears it, the agent returns an
explicit no-confident-match result rather than the nearest (but poor) row.

## 5. Agent 4 — Predictive Risk Agent (FR-022, FR-023)

Triggered by Cloud Scheduler (`predictions.tick`), not by alert arrival —
predictions must exist *before* a failure's alerts fire (AC-3.1). Uses the
BQML model from research.md §6 (`ML.FORECAST` / `ML.DETECT_ANOMALIES` /
`ML.EXPLAIN_FORECAST` against `sre_ml_ops.alert_trend_forecast_model`,
itself trained from `sre_telemetry.alert_stream`). Output is written only to
Firestore `predictions/{service_name}__{alert_type}` (research.md §2
boundary rule) — **not** to any new BigQuery table.

## 6. Agent 5 — Remediation Agent (FR-015 – FR-021)

Reads the matched runbook's documented procedure by id:

```sql
SELECT runbook_id, title, steps, rollback_steps, risk_level
FROM `sre_knowledge_base.runbooks`
WHERE runbook_id = @runbook_id;
```

Fix/rollback scripts are LLM-generated *from* these documented steps (never
hardcoded), validated, then held in Firestore `approvals/{action_id}`
(status `Proposed`) until a human decision arrives (FR-017). Only after
`remediation.approved` and a real Cloud Run Admin API execution does the
outcome get appended to the one relevant BigQuery table:

```sql
INSERT INTO `sre_incident_mart.remediation_logs`
  (incident_id, runbook_id, outcome, executed_at, executed_by, details)
VALUES (@incident_id, @runbook_id, @outcome, CURRENT_TIMESTAMP(), @executed_by, @details);
```

(Column names beyond `incident_id`/`runbook_id` are placeholders — research.md §8.)
A rejected proposal (FR-021) updates the Firestore `approvals/{action_id}`
status to `Rejected` and the incident's Firestore stage back to
`Investigating`; nothing is written to `remediation_logs` for a rejection
(only real executed outcomes are logged there).

## 7. Agent 6 — Executive Impact Agent (FR-027 – FR-032)

```sql
-- Business-impact join for one incident (FR-027)
SELECT ca.customer_id, ca.customer_name, ca.tier, ca.monthly_recurring_revenue,
       ca.sla_uptime_target_pct, ca.sla_credit_rate_per_hour, ca.user_count,
       IF(ca.service_name IS NULL, 'Unmapped', 'Mapped') AS impact_mapping_status
FROM `sre_incident_mart.correlated_alerts` AS link
JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = link.alert_id
LEFT JOIN `sre_incident_mart.customer_accounts` AS ca ON ca.service_name = al.service_name
WHERE link.incident_id = @incident_id;
```

Business formulas (documented, not hardcoded per-incident): `revenue_at_risk_usd
= SUM(monthly_recurring_revenue) / (24*30) * incident_duration_hours`;
`sla_exposure_usd = SUM(sla_credit_rate_per_hour) * incident_duration_hours`
for accounts breaching `sla_uptime_target_pct`; `affected_customers =
COUNT(DISTINCT customer_id)`; `affected_users = SUM(user_count)`.

```sql
-- MTTR (FR-028): platform-handled vs. historical baseline
SELECT AVG(TIMESTAMP_DIFF(resolved_at, opened_at, MINUTE)) AS avg_mttr_minutes
FROM `sre_incident_mart.incidents`
WHERE status IN ('Resolved', 'Closed') AND resolved_at IS NOT NULL
  AND opened_at >= @platform_deployment_ts;  -- excludes the ~18 pre-existing seed incidents
```

Postmortem write: the `MERGE` from research.md §16, run once per
`incidents.resolved` event. Executive metrics (revenue at risk, SLA
exposure, MTTR, resolution success rate, time saved) are computed live and
cached to Firestore `executive_metrics/latest` (research.md §2 boundary
rule) — **not** a new BigQuery table.

---

## 8. New BigQuery ML dataset (not part of the existing warehouse)

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
```

`sre_ml_ops` is a new, Terraform-created dataset in the same project/region
as the existing warehouse (single-region `us-central1`, per Clarification),
holding only this model object. Retrained on a Cloud Scheduler cadence.

## 9. Firestore collections (live/ephemeral state — research.md §2)

```text
incidents/{incident_id}
  status, root_cause, root_cause_confidence, affected_services[],
  correlated_alert_count, current_stage, stage_history: [{stage, actor, at}],
  updated_at

approvals/{action_id}
  incident_id, runbook_id, fix_script, rollback_script, risk_level,
  status (Proposed|Approved|Rejected|Executing|Succeeded|Failed),
  proposer, created_at, approver_uid, decision, comments, decided_at,
  execution_result (real Cloud Run Admin API response, once executed)

predictions/{service_name}__{alert_type}
  predicted_failure, time_to_failure_start, time_to_failure_end,
  confidence, rationale, is_anomaly_only, generated_at

executive_metrics/latest
  revenue_at_risk_usd, sla_exposure_usd, affected_customers, affected_users,
  mttr_minutes, mttr_reduction_pct, resolution_success_rate_pct,
  time_saved_hours, snapshot_ts

pending_alerts/{replay_event_id}   -- TTL ~10 minutes, live clustering window only
  alert_id, node_id, service_name, severity, alert_type, measured_value,
  occurred_at, incident_id (once assigned)
```

`approvals/{action_id}` **is** the Approval Decision and Remediation Action
record (FR-016, FR-017, FR-018) — there is no separate BigQuery table for
either; only the final executed outcome is appended to `remediation_logs`.

## 10. Cloud Logging audit entry (FR-037/NFR-008 — not a BigQuery table)

```json
{
  "severity": "NOTICE",
  "jsonPayload": {
    "actor_uid": "string",
    "action": "incident_view | approval_decision | remediation_execute | ...",
    "resource": "incident_id or action_id",
    "timestamp": "RFC3339",
    "details": {}
  }
}
```

## 11. Validation & security rules

- Every query above uses named `@param` parameters (research.md §18) — no
  string concatenation of event- or user-derived values into SQL text.
- Free-text fields pulled from `alert_stream.message`, `runbooks`
  steps/content, or `incidents` notes pass through the shared redaction
  utility before reaching any prompt, dashboard field, generated
  script, or log line (research.md §15) — applied at read/output time since
  this feature performs no ingestion.
- `alert_stream`, `network_nodes`, `runbooks`, `embedding_model`, and
  `customer_accounts` are never targeted by `INSERT`/`UPDATE`/`MERGE`/
  `DELETE` anywhere in this platform (FR-039).
