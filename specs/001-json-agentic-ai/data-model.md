# Phase 1 Data Model: JSON-Driven Agentic AI Incident Prevention & Resolution Platform

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24
**Prerequisite**: [research.md](./research.md)

This document maps the spec's Key Entities to concrete storage: BigQuery
datasets/tables (system of record) and Firestore collections (live UI
read model + approval queue). All natural-id / upsert behavior implements
Clarification #1 (upsert by per-domain natural id, or a derived SHA-256 hash
of a documented canonical field subset when no natural id exists).

## Datasets

| Dataset | Purpose |
|---|---|
| `core` | Curated, queryable tables for all 7 ingested domains + derived operational entities (incidents, remediation, approvals, forecasts, audit, executive metrics). System of record. |
| `ml` | BigQuery ML artifacts: the remote text-embedding model and the per-service/metric `ARIMA_PLUS` forecast models. |

Landing of raw uploaded JSON happens in Cloud Storage
(`gs://<project>-landing/<domain>/<upload_id>/<filename>.json`), **not** a
separate BigQuery raw/staging dataset — this keeps "raw JSON landing" (a
mandatory-service requirement) truthful while avoiding a redundant BQ
staging hop for a demo-scale dataset. The ingestion service reads directly
from that GCS object and MERGEs into `core`.

---

## 1. Alert → `core.alerts`

Natural id: source-provided alert id if present, else
`TO_HEX(SHA256(FORMAT('%s|%s|%s|%s', source, resource_id, description, CAST(first_seen_at AS STRING))))`.

```sql
CREATE TABLE IF NOT EXISTS core.alerts (
  alert_id        STRING NOT NULL,   -- natural id or derived hash key
  source          STRING,
  severity        STRING,            -- e.g. CRITICAL/WARNING/INFO
  status          STRING,            -- open/acknowledged/correlated
  service_id      STRING,
  resource_id     STRING,
  description     STRING,            -- redacted before write
  raw_payload     JSON,              -- original record for traceability
  first_seen_at   TIMESTAMP NOT NULL,
  last_seen_at    TIMESTAMP,
  incident_id     STRING,            -- set once correlated (FR-017)
  ingested_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(first_seen_at)
CLUSTER BY service_id, severity;
```

## 2. Telemetry Reading → `core.telemetry`

No natural id (pure time series); dedup key is
`(service_id, metric_name, ts)` used in the MERGE `ON` clause.

```sql
CREATE TABLE IF NOT EXISTS core.telemetry (
  service_id    STRING NOT NULL,
  metric_name   STRING NOT NULL,
  metric_value  FLOAT64 NOT NULL,
  unit          STRING,
  ts            TIMESTAMP NOT NULL,
  ingested_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(ts)
CLUSTER BY service_id, metric_name;
```

## 3. Historical Incident Record → `core.historical_incidents`

Natural id: source incident id, else hash of `(title, opened_at)`.

```sql
CREATE TABLE IF NOT EXISTS core.historical_incidents (
  historical_incident_id STRING NOT NULL,
  title           STRING,
  summary         STRING,            -- redacted before write
  root_cause      STRING,
  resolution      STRING,
  services        ARRAY<STRING>,
  opened_at       TIMESTAMP,
  resolved_at     TIMESTAMP,
  mttr_minutes    FLOAT64,
  ingested_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(opened_at)
CLUSTER BY historical_incident_id;
```

## 4. Runbook / SOP → `core.runbooks`

Natural id: source runbook id, else hash of `(title, steps)`. `content` is
the concatenated text (title + applicability + steps) fed to the embedding
model. `embedding` is populated synchronously by the ingestion service via
`ML.GENERATE_EMBEDDING` (see research.md §2) immediately after MERGE.

```sql
CREATE TABLE IF NOT EXISTS core.runbooks (
  runbook_id      STRING NOT NULL,
  title           STRING,
  applicability   STRING,            -- when this SOP applies
  steps           JSON,               -- ordered remediation steps
  rollback_steps  JSON,
  risk_level      STRING,            -- low/medium/high, as authored
  content         STRING,            -- text used to generate the embedding
  embedding       ARRAY<FLOAT64>,     -- from ML.GENERATE_EMBEDDING(text-embedding-005)
  embedding_model STRING,             -- e.g. 'text-embedding-005', for traceability
  ingested_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY runbook_id;

-- Created once >=1 row exists; VECTOR_SEARCH falls back to brute force until ACTIVE.
CREATE OR REPLACE VECTOR INDEX runbooks_embedding_idx
ON core.runbooks(embedding)
OPTIONS(distance_type = 'COSINE', index_type = 'IVF');
```

Fallback path (documented, not built for the demo): an autonomous
`GENERATED ALWAYS AS (AI.EMBED(content, connection_id => ..., endpoint =>
'text-embedding-005')) STORED OPTIONS(asynchronous = TRUE)` column could
replace the synchronous call for a non-latency-sensitive bulk historical
import.

## 5. Service Topology / Dependency Graph → `core.services`, `core.service_dependencies`

```sql
CREATE TABLE IF NOT EXISTS core.services (
  service_id   STRING NOT NULL,
  name         STRING,
  tier         STRING,
  owner_team   STRING,
  ingested_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY service_id;

CREATE TABLE IF NOT EXISTS core.service_dependencies (
  service_id          STRING NOT NULL,
  depends_on_service  STRING NOT NULL,
  relationship_type   STRING,        -- e.g. calls/depends_on/hosted_on
  ingested_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY service_id;
```

Natural id / dedup key: `(service_id, depends_on_service, relationship_type)`
for edges; `service_id` for the dimension table.

## 6. SLA Definition → `core.sla_definitions`

```sql
CREATE TABLE IF NOT EXISTS core.sla_definitions (
  sla_id              STRING NOT NULL,   -- natural id or hash(service_id, customer_segment)
  service_id          STRING NOT NULL,
  customer_segment    STRING,
  uptime_target_pct   FLOAT64,
  credit_terms        JSON,
  penalty_per_breach_usd FLOAT64,
  ingested_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY service_id;
```

## 7. Revenue Impact Record → `core.revenue_impact`

Carries the customer/user-count attribute used to compute affected-customer
counts (Clarification #4) — no separate "customer" data domain is
introduced.

```sql
CREATE TABLE IF NOT EXISTS core.revenue_impact (
  record_id           STRING NOT NULL,  -- natural id or hash(service_id, customer_segment)
  service_id          STRING NOT NULL,
  customer_segment    STRING,
  revenue_per_hour_usd FLOAT64,
  customer_count      INT64,            -- basis for "affected customers" (FR-034)
  ingested_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY service_id;
```

---

## Derived / operational entities (written by agents & orchestrator, not uploaded)

## 8. Incident → `core.incidents` (+ `core.incident_timeline_events`)

Status enum is fixed per Clarification #5: `Open, Investigating,
Awaiting Approval, Remediating, Resolved, Closed`. A prediction is **never**
a status value here — see Risk Forecast below.

```sql
CREATE TABLE IF NOT EXISTS core.incidents (
  incident_id           STRING NOT NULL,
  status                STRING NOT NULL,  -- enum enforced in application layer
  opened_at             TIMESTAMP NOT NULL,
  resolved_at           TIMESTAMP,
  root_cause            STRING,
  root_cause_confidence FLOAT64,
  root_cause_reasoning  STRING,
  affected_services     ARRAY<STRING>,
  correlated_alert_ids  ARRAY<STRING>,
  updated_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(opened_at)
CLUSTER BY incident_id;

CREATE TABLE IF NOT EXISTS core.incident_timeline_events (
  incident_id  STRING NOT NULL,
  event_type   STRING NOT NULL,  -- alert_correlated/root_cause_set/runbook_matched/...
  description  STRING,
  actor        STRING,           -- agent name or user uid
  ts           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(ts)
CLUSTER BY incident_id;
```

State transitions: `Open → Investigating → Awaiting Approval → Remediating →
Resolved → Closed`, with a reject path `Awaiting Approval → Investigating`
(FR-026) and a direct `Open/Investigating → Closed` archival path for
stale/duplicate incidents.

## 9. Remediation Action → `core.remediation_actions`

```sql
CREATE TABLE IF NOT EXISTS core.remediation_actions (
  action_id       STRING NOT NULL,
  incident_id     STRING NOT NULL,
  runbook_id      STRING,
  fix_script      STRING,   -- redacted before write/display (FR-042)
  rollback_script STRING,
  risk_level      STRING,
  status          STRING NOT NULL, -- Proposed/Approved/Rejected/Executing/Succeeded/Failed
  execution_result JSON,    -- real Cloud Run Admin API response/exit status
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY incident_id;
```

## 10. Approval Decision → `core.approval_decisions`

```sql
CREATE TABLE IF NOT EXISTS core.approval_decisions (
  decision_id  STRING NOT NULL,
  action_id    STRING NOT NULL,
  approver_uid STRING NOT NULL,   -- Firebase uid (FR-025/NFR-008)
  decision     STRING NOT NULL,   -- Approved/Rejected
  comments     STRING,
  decided_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY action_id;
```

## 11. Risk Forecast / Prediction → `core.risk_forecasts`

Always a separate entity from Incident status, per Clarification #5.
`occurred` is filled in later (nullable) to track forecast accuracy per the
"predicted outage did not occur" edge case.

```sql
CREATE TABLE IF NOT EXISTS core.risk_forecasts (
  forecast_id           STRING NOT NULL,
  service_id            STRING NOT NULL,
  metric_name           STRING,
  predicted_failure     STRING,
  time_to_failure_start TIMESTAMP,
  time_to_failure_end   TIMESTAMP,
  confidence            FLOAT64,
  rationale             STRING,   -- from ML.EXPLAIN_FORECAST (NFR-010)
  is_anomaly_only       BOOL,     -- TRUE = flagged trend, not a full prediction (FR-031)
  occurred              BOOL,     -- nullable; backfilled for accuracy tracking
  created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY service_id;
```

## 12. Audit Log Entry → `core.audit_log`

```sql
CREATE TABLE IF NOT EXISTS core.audit_log (
  entry_id   STRING NOT NULL,
  actor_uid  STRING,
  action     STRING NOT NULL,   -- upload/incident_view/approval_decision/remediation_execute/...
  resource   STRING,            -- e.g. incident_id, action_id, upload job id
  ts         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  details    JSON
)
PARTITION BY DATE(ts)
CLUSTER BY actor_uid;
```

## 13. Executive metrics snapshot → `core.executive_metrics`

Refreshed by the Executive Impact Agent on event + Cloud Scheduler cadence.

```sql
CREATE TABLE IF NOT EXISTS core.executive_metrics (
  snapshot_ts               TIMESTAMP NOT NULL,
  revenue_at_risk_usd       FLOAT64,
  sla_exposure_usd          FLOAT64,
  affected_customers        INT64,
  mttr_minutes              FLOAT64,
  mttr_reduction_pct        FLOAT64,
  resolution_success_rate_pct FLOAT64,
  time_saved_hours          FLOAT64
)
PARTITION BY DATE(snapshot_ts);
```

## 14. User / Role — Firebase Authentication (not a BigQuery table)

Identity + role live in Firebase Auth custom claims
(`role ∈ {OnCallEngineer, IncidentCommander, Approver, ExecutiveViewer,
Administrator}`), per Clarification #3. `approver_uid`/`actor_uid` columns
above are Firebase uids, joined to Firebase Auth (not a local users table)
to avoid duplicating identity state.

---

## BigQuery ML models (`ml` dataset)

```sql
-- Embedding remote model (research.md §2)
CREATE OR REPLACE MODEL ml.runbook_embedding_model
REMOTE WITH CONNECTION DEFAULT
OPTIONS (ENDPOINT = 'text-embedding-005');

-- Forecast model, one logical model covering all service/metric time series
-- (research.md §4); retrained on a Cloud Scheduler cadence.
CREATE OR REPLACE MODEL ml.telemetry_forecast_model
OPTIONS (
  MODEL_TYPE = 'ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL = 'ts',
  TIME_SERIES_DATA_COL = 'metric_value',
  TIME_SERIES_ID_COL = ['service_id', 'metric_name'],
  HORIZON = 60,
  AUTO_ARIMA = TRUE
) AS
SELECT service_id, metric_name, ts, metric_value FROM core.telemetry;
```

`ML.FORECAST(MODEL ml.telemetry_forecast_model, STRUCT(60 AS horizon, 0.95 AS
confidence_level))` produces the prediction; `ML.DETECT_ANOMALIES` and
`ML.EXPLAIN_FORECAST` on the same model produce the anomaly flag and
rationale respectively (both feed `core.risk_forecasts`).

---

## Firestore collections (live UI read model + approval queue)

Firestore is **not** the system of record — every field here is a
denormalized projection of the BigQuery rows above, written immediately
after the corresponding BigQuery write so the UI can subscribe in realtime
without polling BigQuery.

```text
incidents/{incident_id}
  status, root_cause, root_cause_confidence, affected_services,
  correlated_alert_count, current_stage, updated_at

approvals/{action_id}
  incident_id, status (pending/approved/rejected), risk_level,
  proposer, created_at, decided_at, approver_uid, comments

ingestion_jobs/{job_id}
  domain, filename, status (pending/in_progress/succeeded/failed),
  error_reason, uploaded_by, updated_at
```

`ingestion_jobs` directly satisfies FR-007 (per-file ingestion status
visible to the uploading user).

## Validation rules (applied by the ingestion service before any MERGE)

- Each domain has a JSON Schema (`services/ingestion-service/app/validators/`)
  describing required fields and types; a file failing validation never
  reaches BigQuery — it produces a `failed` `ingestion_jobs` doc with a
  specific reason (FR-005, AC-1.3).
- Every table's natural-id/hash-key column is `NOT NULL` and is the MERGE
  key — re-uploading the same logical record updates the existing row
  in place (FR-002/FR-006/AC-1.4), never appends a duplicate.
- Free-text fields (`description`, `summary`, `content`, `fix_script`,
  `rollback_script`) pass through the shared redaction utility before
  being written (FR-033/FR-044).
