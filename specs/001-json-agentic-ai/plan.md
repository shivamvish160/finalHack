# Implementation Plan: JSON-Driven Agentic AI Incident Prevention & Resolution Platform

**Branch**: `001-json-agentic-ai` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-json-agentic-ai/spec.md`

**Note**: This template is filled in by the `/audi.plan` command. See `.audi/templates/plan-template.md` for the execution workflow.

## Summary

Build a Google Cloud-native Agentic AI Incident Prevention & Resolution
Platform: users upload 7 JSON data domains (alerts, telemetry, historical
incidents, runbooks, topology, SLA, revenue) which land in Cloud Storage and
are automatically MERGE-loaded into BigQuery by a Cloud Run ingestion
service, which also synchronously generates runbook embeddings
(`ML.GENERATE_EMBEDDING` over a `text-embedding-005` remote model) and
maintains a `VECTOR_SEARCH` index. Six ADK `LlmAgent`s (Alert Correlation,
Root Cause Analysis, Runbook Retrieval, Predictive Risk, Remediation,
Executive Impact), each backed by `gemini-2.5-flash`/`gemini-2.5-pro` via
Vertex AI, are composed by a **custom Pub/Sub-driven orchestrator**
(ADK's `SequentialAgent`/`ParallelAgent` are deprecated upstream — see
`research.md` §5) rather than in-process ADK sub-agent trees, so each stage
can scale/schedule independently on Cloud Run. BigQuery is the durable
system of record (including a BigQuery ML `ARIMA_PLUS` model for outage
forecasting + anomaly detection); Firestore holds a live, denormalized
projection for the frontend and the human-in-the-loop approval queue. A
React/Next.js frontend renders the 8 required UI pages against a
BFF (`api-gateway`) that enforces Firebase Authentication + custom-claim
RBAC, while GCP IAM governs service-to-service access. Remediation always
stops at a proposal until a human approves it via `api-gateway`; only then
does an isolated execution tool call the real Cloud Run Admin API against a
dedicated sandbox target service. All infrastructure is defined in
Terraform.

## Technical Context

**Language/Version**: Python 3.12 (all backend services & ADK agents); TypeScript 5.x / Node.js 20+ (frontend)
**Primary Dependencies**: FastAPI, `google-adk` (Agent Development Kit, `LlmAgent`+`Runner`), `google-genai`/Vertex AI SDK (Gemini 2.5 Flash/Pro), `google-cloud-bigquery`, `google-cloud-pubsub`, `google-cloud-storage`, `google-cloud-firestore`, `google-cloud-run` (Admin API client), `google-cloud-secret-manager`, `firebase-admin`; Next.js (App Router) + React + Tailwind + Firebase JS SDK; Terraform >= 1.7 (`google`/`google-beta` providers)
**Storage**: BigQuery (`core` + `ml` datasets — system of record for all 7 ingested domains + derived incidents/remediation/approvals/forecasts/audit/executive metrics, plus `VECTOR_SEARCH` index and `ARIMA_PLUS` forecast model); Cloud Storage (raw JSON landing); Firestore (live UI projection + approval queue, non-authoritative); Secret Manager (credentials/secrets)
**Testing**: pytest + pytest-asyncio (services/agents, mocked GCP clients); Firestore/Pub/Sub emulators + a disposable BigQuery dataset for integration tests; JSON Schema contract tests for uploads and Pub/Sub payloads; ADK agent-eval harness for prompt/tool regression; Vitest + React Testing Library + Playwright (frontend); a dedicated load-test script for the ≥1000 alerts/min burst; `terraform validate`/`plan` for infra
**Target Platform**: Google Cloud — Cloud Run (services + jobs, autoscaling), single-region demo deployment
**Project Type**: web (frontend + multi-service backend: ingestion-service, agent-orchestrator, api-gateway, plus the 6 ADK agent modules they host)
**Performance Goals**: sustain ≥1,000 alerts/minute ingestion with zero loss (NFR-001); consolidated incident within 5 minutes of storm start (NFR-003); newly ingested data usable by all agents within 5 minutes (NFR-004)
**Constraints**: remediation execution MUST NOT occur without prior explicit human approval regardless of load/urgency (NFR-009); no secret/PII in plaintext in UI/logs/scripts (NFR-006/NFR-007); every correlation/RCA/retrieval/prediction/remediation output MUST derive solely from ingested data, no hardcoded fallback mappings (NFR-011); temporary unavailability of one analysis capability MUST NOT block core incident visibility (NFR-012)
**Scale/Scope**: 7 ingestion domains, 6 coordinated ADK agents, 8 frontend views, demo-scale data volumes (thousands of alerts/telemetry rows per run, dozens of runbooks), 5 RBAC roles

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.audi/memory/constitution.md` contains only unfilled template placeholders
(`[PRINCIPLE_1_NAME]`, `[GOVERNANCE_RULES]`, etc.) — no project constitution
has been ratified for this repository. There are therefore no
constitution-derived gates to evaluate for this plan; none are asserted as
passing or failing. If a constitution is ratified later, re-run this check
against it before further implementation. **Status: N/A (no constitution) —
not a blocking condition.**

**Post-Phase-1 re-check (2026-09-24)**: Phase 1 artifacts (`data-model.md`,
`contracts/rest-api.md`, `contracts/pubsub-events.md`, `quickstart.md`)
introduce no new architectural elements beyond what Phase 0 already
researched, and no constitution exists to gate against — re-check confirms
the same **N/A** status; no violations to record.

## Project Structure

### Documentation (this feature)

```text
specs/001-json-agentic-ai/
├── plan.md              # This file (/audi.plan command output)
├── research.md          # Phase 0 output (/audi.plan command)
├── data-model.md        # Phase 1 output (/audi.plan command)
├── quickstart.md        # Phase 1 output (/audi.plan command)
├── contracts/           # Phase 1 output (/audi.plan command)
│   ├── rest-api.md
│   └── pubsub-events.md
└── tasks.md             # Phase 2 output (/audi.tasks command - NOT created by /audi.plan)
```

### Source Code (repository root)

```text
infra/                              # Terraform — all GCP infrastructure
  environments/demo/                 # terraform.tfvars for the hackathon demo env
  modules/
    networking/
    bigquery/                        # datasets, tables, vector index, ARIMA_PLUS + embedding models
    pubsub/                          # topics, DLQs, push subscriptions
    cloud-run/                       # services + jobs, autoscaling config
    storage/                         # landing bucket
    security/                        # IAM service accounts, Secret Manager, Firebase project config
  main.tf, variables.tf, outputs.tf, providers.tf, backend.tf

services/
  ingestion-service/                 # Cloud Run: upload endpoint, validation, BQ MERGE, embeddings
    app/{main.py, routers/, validators/, bigquery/, pubsub/}
    Dockerfile, tests/
  agent-orchestrator/                # Cloud Run: hosts the 6 ADK agents + custom Pub/Sub orchestrator
    app/{main.py, orchestrator/, runners/}
    Dockerfile, tests/
  api-gateway/                       # Cloud Run: BFF for the 8 UI pages, Firebase auth + RBAC, approvals
    app/{main.py, routers/, services/}
    Dockerfile, tests/

agents/                              # 6 ADK agent modules (imported by agent-orchestrator)
  alert_correlation/{agent.py, tools.py, prompts.py}
  root_cause_analysis/
  runbook_retrieval/
  predictive_risk/
  remediation/
  executive_impact/
  common/                             # shared BigQuery/Pub/Sub clients, redaction utility

frontend/                            # Next.js dashboard (8 required pages)
  app/{incidents/, incidents/[id]/timeline, incidents/[id]/correlation,
       incidents/[id]/root-cause, incidents/[id]/runbook, approvals/,
       predictive/, executive/}
  components/, lib/ (API client + Firebase auth), tests/

scripts/
  deploy/{build-and-push, deploy-all}
  demo/{seed-demo-data, simulate-alert-storm}

data/samples/                        # Demo JSON fixtures for all 7 domains
  alerts.sample.json, telemetry.sample.json, incidents.sample.json,
  runbooks.sample.json, topology.sample.json, sla.sample.json,
  revenue.sample.json
```

**Structure Decision**: Web application + multi-service backend structure
(Option 2 generalized to 3 backend services instead of 1, since the spec
requires independently-scalable ingestion, agent-orchestration, and
BFF/API concerns per NFR-001/002/012). `frontend/` is the Next.js app for
all 8 UI pages; `services/*` are the 3 deployable Cloud Run backends;
`agents/*` is a shared library package (not independently deployed) imported
by `services/agent-orchestrator`; `infra/` holds 100% of the Terraform
needed to stand up every GCP resource named in the spec's mandatory-service
list; `data/samples/` and `scripts/demo/` exist specifically to make the
primary demonstration flow (spec.md) reproducible end-to-end.

## Testing & Verification Strategy

Full detail lives in `research.md` §12 and the executable checks in
`quickstart.md` §6; summarized here per requirement category:

| Category | Approach | Requirements verified |
|---|---|---|
| Unit | pytest, mocked BigQuery/Pub/Sub/Vertex/Cloud Run Admin clients, per service/agent | Business logic in validators, redaction, hash-key derivation, agent tools |
| Contract | JSON Schema tests for all 7 upload domains (`data/samples`) + REST (`contracts/rest-api.md`) + Pub/Sub payload schemas (`contracts/pubsub-events.md`) | FR-001, FR-005, AC-1.3 |
| Integration | Firestore + Pub/Sub emulators, disposable BigQuery dataset; exercises ingestion MERGE/upsert idempotency and full event-chain orchestration | FR-002, FR-006, AC-1.4, Clarification #1 |
| Agent evaluation | ADK agent-eval harness with a small labeled set (alerts→expected cluster count, incidents→expected runbook match); asserts every agent's `output_schema` always carries a confidence/similarity + rationale | NFR-010, FR-009–FR-014 |
| Load | `/scripts/demo/simulate-alert-storm.py` publishing ≥1000 msgs/min; asserts Cloud Run autoscale-out and an empty `alerts.raw-dlq` | NFR-001, NFR-002, AC-4.3, SC-010 |
| Security | Redaction/secret-leak scan of a demo run's logs/UI payloads/generated scripts against canary values; approval-integrity SQL check (every executed/failed remediation has a matching approved decision) | SC-009, SC-005, NFR-006, NFR-007, NFR-009 |
| End-to-end demo | `quickstart.md` reproduces the spec's Primary Demonstration Flow against a deployed environment — doubles as the literal hackathon demo runbook | All 5 user stories + primary flow |
| Infra | `terraform validate` + `terraform plan` (CI), optional `tfsec`/`checkov` static scan for IAM over-privilege | Security & Governance requirements (FR-041–FR-044) |
| Frontend | Vitest + React Testing Library (components), Playwright (the 8 pages' critical navigation paths, FR-040) | FR-039, FR-040 |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Not applicable — no constitution is ratified for this repository (see
Constitution Check above), so there are no gate violations to justify. The
three-backend-service split (instead of a single backend project) is
driven directly by the spec's own non-functional requirements (independent
autoscaling of ingestion vs. agent orchestration vs. API/BFF traffic,
NFR-001/002/012), not by a constitutional principle, so it is documented as
a Structure Decision above rather than a tracked violation.
