# Quickstart: SRE Agentic AI Incident Prevention & Resolution Platform

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24 (re-derived for the
existing-warehouse premise — there is no upload/sample-data-seeding step in
this version; the warehouse is assumed already provisioned and populated)

This is the deploy-and-demo path for the primary demonstration flow
described in `spec.md`. It assumes the monorepo layout from `plan.md` has
been implemented (Phase 3+ / `/audi.tasks` + `/audi.implement`) — this
document itself contains no implementation code.

## Prerequisites

- The BCE Hackfest Track 2 BigQuery warehouse already exists and is
  populated in the target GCP project: `sre_telemetry.alert_stream`,
  `sre_topology.network_nodes`, `sre_knowledge_base.runbooks` +
  `embedding_model`, `sre_incident_mart.customer_accounts` / `incidents` /
  `correlated_alerts` / `remediation_logs` / `incident_postmortems`. This
  quickstart does **not** create or seed any of these.
- `GCP_PROJECT_ID` (deployment config, not hardcoded) points at that same
  project; all new resources deploy to `us-central1` (Clarification).
- APIs enabled: BigQuery, BigQuery Connection, Cloud Run, Pub/Sub, Cloud
  Scheduler, Secret Manager, Cloud Logging, Vertex AI
  (`aiplatform.googleapis.com`), Firebase/Identity Platform, Firestore.
- Terraform >= 1.7, Python 3.12, Node.js 20+, Docker.
- A Firebase project linked to the same GCP project (for Authentication).
- A principal with `roles/bigquery.dataViewer` on the 4 existing datasets
  and `roles/bigquery.dataEditor` scoped to `sre_incident_mart` only (for
  the 4 FR-039 write targets) — never broader than that.

## 0. Verify warehouse connectivity (smoke test)

Before provisioning anything new, confirm read access to the existing
warehouse with a trivial parameterized query against each dataset (e.g. `SELECT COUNT(*) FROM sre_telemetry.alert_stream`,
`sre_knowledge_base.runbooks`, `sre_incident_mart.incidents`) and run
`INFORMATION_SCHEMA.COLUMNS` against `customer_accounts`, `incidents`, and
`remediation_logs` to confirm/adjust the placeholder column names flagged in
`data-model.md` (research.md §8) before writing real queries against them.

## 1. Provision NEW supporting infrastructure only

```powershell
cd infra/environments/demo
terraform init
terraform apply -var-file="terraform.tfvars"
```

Creates **only** new supporting resources — **never** the warehouse itself:
the `sre_ml_ops` dataset + `alert_trend_forecast_model` BQML model object,
all Pub/Sub topics + dead-letter topics + push subscriptions (`contracts/pubsub-events.md`),
the Cloud Run services (`alert-replay-service`, `agent-orchestrator`,
`api-gateway`, `demo-target-service`), Firestore (native mode) + its
collections' security rules, Cloud Scheduler jobs (`predictions.tick`,
executive-metrics refresh), Secret Manager secrets, and per-service
least-privilege service accounts/IAM bindings — including the narrow
`bigquery.dataEditor` grant scoped to `sre_incident_mart` needed for
`incident_postmortems` (and the other 3 FR-039 tables) writes.

## 2. Build & deploy application images

```powershell
./scripts/deploy/build-and-push.ps1   # builds+pushes all 4 service images + frontend
./scripts/deploy/deploy-all.ps1       # gcloud run deploy for each service, wires env/secrets
```

## 3. Seed demo users & roles

```powershell
./scripts/demo/seed-demo-users.ps1
```

Creates Firebase Auth accounts for the 5 demo roles (On-Call Engineer,
Incident Commander, Approver, Executive Viewer, Administrator) with custom
role claims set (FR-035).

## 4. Run the primary demonstration flow

```powershell
./scripts/demo/start-alert-replay.ps1 --rate 1000 --duration-minutes 1
```

Starts `alert-replay-service` replaying `sre_telemetry.alert_stream` at
~1,000 envelopes/minute (looping over the ~3,000-row history, each with a
fresh `replayEventId`, per FR-004). Exercises the full spec flow end-to-end:

1. Alert Correlation Agent clusters the burst into one incident (Live
   Incident Console / Alert Correlation View) within ~5 minutes (SC-001).
2. Root Cause Analysis Agent posts a root cause + confidence + reasoning,
   grounded in `alert_stream`/`network_nodes`/historical `incidents`
   (Root Cause Analysis View).
3. Runbook Retrieval Agent surfaces a semantically matched SOP via
   `VECTOR_SEARCH` over `runbooks.embedding` (Runbook Recommendation View).
4. Predictive Risk Agent (already running on its own Cloud Scheduler
   cadence, independent of the alert burst) shows a forecast on the
   Predictive Health Dashboard.
5. Sign in as **Approver**, open the Approval Console, and approve the
   proposed remediation — confirm the rollback plan is visible before
   approving (FR-016/FR-017).
6. Confirm `remediation.executed` recorded a real Cloud Run Admin API
   result against `demo-target-service` (check the incident's
   `approvals/{actionId}.executionResult` in Firestore, and the
   corresponding new row in `remediation_logs`).
7. Open the Executive Dashboard and confirm revenue-at-risk, SLA exposure,
   affected-customer count, and MTTR/time-saved figures reflect the
   incident just handled (`executive_metrics/latest`).
8. Confirm the incident reached `Resolved` and a row now exists in
   `incident_postmortems` for it (FR-031); re-run step 8's trigger and
   confirm `version` incremented rather than a duplicate row appearing
   (FR-032, SC-010).

## 5. Verify non-functional requirements

- **Load (NFR-001/002)**: while step 4 runs, watch each
  `agent-orchestrator` subscription's Cloud Run instance count autoscale
  per the concrete table in `research.md` §17; confirm every
  `<topic>-dlq` dead-letter topic stays empty (zero dropped alerts, SC-009).
- **Security (SC-008)**: run the redaction scan script (`/scripts/demo/`)
  against the incident's logs/UI payload/generated scripts for known
  secret/PII canary patterns; expect zero hits.
- **Approval integrity (SC-004)**: query
  `SELECT COUNT(*) FROM sre_incident_mart.remediation_logs WHERE incident_id = @incidentId`
  and cross-check every row has a corresponding `Approved` decision in the
  matching Firestore `approvals/{actionId}` document — expect the counts to
  match with zero unattributed executions.
- **No hardcoded logic (NFR-011)**: run the CI static check (blocks literal
  alert/runbook/service identifiers in agent source outside test fixtures)
  and the ADK agent-eval pass against a held-out `alert_stream`/`runbooks`
  subset never referenced in prompts (research.md §20).

## 6. Demo-day contingency

- If Vertex AI/Gemini quota or latency spikes mid-demo, the model ID is a
  Cloud Run env var (research.md §1) — a pre-briefed fallback is to redeploy
  `agent-orchestrator` with a known-good pinned model version, not to
  debug prompts live.
- If `VECTOR_SEARCH` or the BQML model becomes unavailable, NFR-012 requires
  core incident visibility and alert correlation (Agent 1/2) to keep
  working — rehearse the demo path with Agent 3/4 intentionally disabled to
  confirm this degrade-gracefully behavior before demo day.
- Because the replay mechanism only reads `alert_stream` (never mutates
  it), the entire demo is idempotently re-runnable: stopping
  `alert-replay-service` and re-running step 4 from a clean `incidents`
  state (new `incident_id`s) is always safe.

## Local development (per service)

Each service under `/services/*` and `/agents/*` is independently runnable
against emulators:

```powershell
gcloud emulators firestore start &
gcloud beta emulators pubsub start &
# BigQuery: no local emulator — point at a disposable dev dataset in the
# real project, never at the production warehouse datasets directly.
cd services/agent-orchestrator
pytest
```

Local-only fixtures (never used to seed the real warehouse) live under
`/data/samples` for unit/integration tests that need example
alert/runbook/incident shapes without hitting BigQuery. See `plan.md`'s
Testing & Verification Strategy for the full test pyramid.
