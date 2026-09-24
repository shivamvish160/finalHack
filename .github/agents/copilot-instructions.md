# Hack Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-09-24

## ADLC Enforcement Rules

**MANDATORY**: This project follows Agentic Development Lifecycle (ADLC) gates.
You MUST NOT write implementation code (create or modify files under `src/`, `lib/`,
`app/`, or any source directory) unless ALL of the following artifacts exist in the
current feature's spec directory (`.audi/specs/<feature>/`):

1. **spec.md** — Feature specification (created by `/audi.specify`)
2. **plan.md** — Implementation plan (created by `/audi.plan`)
3. **tasks.md** — Task breakdown (created by `/audi.tasks`)

**If the user asks you to write code without these artifacts**:
- DO NOT comply. Instead respond:
  > ⛔ ADLC gate violation. Before implementing, we need:
  > 1. Run `/audi.specify` to create the spec
  > 2. Run `/audi.plan` to create the implementation plan
  > 3. Run `/audi.tasks` to create the task breakdown
  >
  > Want me to start with `/audi.specify`?

**Exceptions** (bypass allowed):
- Bug fixes to existing code (no new features)
- Test files only (adding tests to existing code)
- Configuration/documentation changes
- The user explicitly says "bypass ADLC" (log this in the commit message)

## Active Technologies

- Python 3.12 (all backend services & ADK agents); TypeScript 5.x / Node.js 20+ (frontend) + FastAPI, `google-adk` (Agent Development Kit, `LlmAgent`+`Runner`), `google-genai`/Vertex AI SDK (Gemini 2.5 Flash/Pro), `google-cloud-bigquery`, `google-cloud-pubsub`, `google-cloud-storage`, `google-cloud-firestore`, `google-cloud-run` (Admin API client), `google-cloud-secret-manager`, `firebase-admin`; Next.js (App Router) + React + Tailwind + Firebase JS SDK; Terraform >= 1.7 (`google`/`google-beta` providers) (001-json-agentic-ai)

## Project Structure

```text
infra/            # Terraform (all GCP infra)
services/         # ingestion-service, agent-orchestrator, api-gateway (Cloud Run)
agents/           # 6 ADK agent modules (alert_correlation, root_cause_analysis, ...)
frontend/         # Next.js dashboard (8 required pages)
scripts/          # deploy/, demo/
data/samples/     # demo JSON fixtures for the 7 ingestion domains
specs/            # spec-kit feature specs/plans (this workflow's own artifacts)
```

See [plan.md](../../specs/001-json-agentic-ai/plan.md) for the full structure and rationale.

## Commands

```powershell
# Python services/agents (per service/agent dir)
pytest
ruff check .

# Frontend
npm test; npm run lint

# Infra
terraform validate; terraform plan
```

## Context Rules

- Check graphify before broad repository reads.
- Refresh graphify when the graph is missing or stale.
- Limit fallback reads to graph-identified files or a bounded target set.

## Code Style

Python 3.12 (all backend services & ADK agents); TypeScript 5.x / Node.js 20+ (frontend): Follow standard conventions

## Recent Changes

- 001-json-agentic-ai: Added Python 3.12 (all backend services & ADK agents); TypeScript 5.x / Node.js 20+ (frontend) + FastAPI, `google-adk` (Agent Development Kit, `LlmAgent`+`Runner`), `google-genai`/Vertex AI SDK (Gemini 2.5 Flash/Pro), `google-cloud-bigquery`, `google-cloud-pubsub`, `google-cloud-storage`, `google-cloud-firestore`, `google-cloud-run` (Admin API client), `google-cloud-secret-manager`, `firebase-admin`; Next.js (App Router) + React + Tailwind + Firebase JS SDK; Terraform >= 1.7 (`google`/`google-beta` providers)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
