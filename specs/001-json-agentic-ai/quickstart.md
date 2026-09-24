# Quickstart: JSON-Driven Agentic AI Incident Prevention & Resolution Platform

**Feature**: `001-json-agentic-ai` | **Date**: 2026-09-24

This is the deploy-and-demo path for the primary demonstration flow
described in the spec. It assumes the monorepo layout from `plan.md` has
been implemented (Phase 3+ / `/audi.tasks` + `/audi.implement`) — this
document itself does not contain implementation code.

## Prerequisites

- A Google Cloud project with billing enabled; `gcloud` authenticated with
  an account that can create projects-level IAM bindings.
- APIs enabled: BigQuery, BigQuery Connection, Cloud Run, Pub/Sub, Cloud
  Storage, Cloud Scheduler, Secret Manager, Cloud Logging, Vertex AI
  (`aiplatform.googleapis.com`), Firebase/Identity Platform, Firestore,
  Eventarc.
- Terraform >= 1.7, Python 3.12, Node.js 20+, Docker.
- A Firebase project linked to the same GCP project (for Authentication).

## 1. Provision infrastructure

```powershell
cd infra/environments/demo
terraform init
terraform apply -var-file="terraform.tfvars"
```

Creates: `core`/`ml` BigQuery datasets + tables + the `text-embedding-005`
remote model + BQ connection, the landing Cloud Storage bucket, all Pub/Sub
topics + dead-letter topics + push subscriptions, the three Cloud Run
services (`ingestion-service`, `agent-orchestrator`, `api-gateway`) plus the
`demo-target-service` sandbox target, Cloud Scheduler jobs
(`predictions.tick`, executive metrics refresh), Secret Manager secrets,
and per-service least-privilege service accounts/IAM bindings.

## 2. Build & deploy application images

```powershell
./scripts/deploy/build-and-push.ps1   # builds+pushes all 3 service images + frontend
./scripts/deploy/deploy-all.ps1       # gcloud run deploy for each service, wires env/secrets
```

## 3. Seed demo users & roles

```powershell
./scripts/demo/seed-demo-data.ps1 -Users
```

Creates Firebase Auth accounts for the 5 demo roles (On-Call Engineer,
Incident Commander, Approver, Executive Viewer, Administrator) with custom
role claims set (FR-041).

## 4. Upload the 7 sample data domains

Via the frontend (Live Incident Console → Upload) or directly:

```powershell
./scripts/demo/seed-demo-data.ps1 -UploadSamples ./data/samples
```

Uploads `alerts.sample.json`, `telemetry.sample.json`,
`incidents.sample.json`, `runbooks.sample.json`, `topology.sample.json`,
`sla.sample.json`, `revenue.sample.json`. Confirm ingestion status turns
`succeeded` for all 7 via `GET /uploads/{jobId}` or the UI upload panel
(FR-007) before continuing — this also confirms runbook embeddings were
generated (query `core.runbooks` for non-null `embedding`).

## 5. Run the primary demonstration flow

```powershell
./scripts/demo/simulate-alert-storm.py --rate 1000 --duration-minutes 1
```

Publishes ~1000 related alerts/minute to the `alerts.raw` Pub/Sub topic,
exercising the full spec flow end-to-end:

1. Alert Correlation Agent clusters the burst into one incident
   (Live Incident Console / Alert Correlation View).
2. Root Cause Analysis Agent posts a root cause + confidence + reasoning
   (Root Cause Analysis View).
3. Runbook Retrieval Agent surfaces a semantically matched SOP
   (Runbook Recommendation View).
4. Predictive Risk Agent (already running on its own Cloud Scheduler
   cadence) shows a forecast on the Predictive Health Dashboard,
   independent of the alert burst.
5. Sign in as **Approver**, open the Approval Console, and approve the
   proposed remediation — confirm the rollback plan is visible before
   approving.
6. Confirm `remediation.executed` recorded a real Cloud Run Admin API
   result against `demo-target-service` (check `core.remediation_actions
   .execution_result`).
7. Open the Executive Dashboard and confirm revenue-at-risk, SLA exposure,
   affected-customer count, and MTTR/time-saved figures reflect the
   incident just handled.

## 6. Verify non-functional requirements

- **Load (NFR-001/002)**: while step 5 runs, watch Cloud Run
  `agent-orchestrator` instance count autoscale; confirm the
  `alerts.raw-dlq` dead-letter topic stays empty (zero dropped alerts,
  SC-010).
- **Security (SC-009)**: run the redaction scan script (planned under
  `/scripts/demo/`) against the incident's logs/UI payload/generated
  scripts for known secret/PII canary patterns; expect zero hits.
- **Approval integrity (SC-005)**: query
  `SELECT COUNT(*) FROM core.remediation_actions WHERE status IN
  ('Succeeded','Failed') AND action_id NOT IN (SELECT action_id FROM
  core.approval_decisions WHERE decision='Approved')` — expect `0`.

## Local development (per service)

Each service under `/services/*` and `/agents/*` is independently runnable
against emulators:

```powershell
gcloud emulators firestore start &
gcloud beta emulators pubsub start &
# BigQuery: point at a disposable dev dataset in a real project (no local emulator)
cd services/ingestion-service
pytest
```

See `plan.md`'s Testing section for the full test pyramid.
