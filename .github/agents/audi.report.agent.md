---
description: Generate a concise executive summary (executive-summary.md) covering the feature overview, delivery metrics, risks, and a clear recommendation for stakeholders.
handoffs:
  - label: Back to Orchestrator
    agent: audi.orchestrator
    prompt: Show final workflow status
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before report)**:
- Check if `.audi/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_report` key.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`): display it as an optional pre-hook.
  - **Mandatory hook** (`optional: false`): display it as an automatic pre-hook and execute it.
- If no hooks are registered or `.audi/extensions.yml` does not exist, skip silently.

## Outline

### Goal

Produce `executive-summary.md` — a concise, non-technical report for stakeholders that summarises what was built, delivery metrics, risks encountered, and a clear recommendation on release readiness.

### Setup

1. Run `.audi/scripts/powershell/setup-plan.ps1 -Json` (Windows) or `.audi/scripts/bash/setup-plan.sh --json` (Linux/macOS) from repo root.
   - Read `.audi/init-options.json` → `script` field to decide which to use.
   - Parse JSON for `FEATURE_SPEC`, `IMPL_PLAN`, `SPECS_DIR`, `BRANCH`.
2. Load all completed artifacts:
   - `spec.md` — original requirements and acceptance criteria
   - `plan.md` — delivery scope and architecture decisions
   - `design.md` — technical design summary
   - `tasks.md` — task completion status
   - `test-plan.md` — test coverage and results
   - `review.md` — code review verdict and findings
   - `verification-report.md` — final verification decision

### Executive Summary Document

Write `{SPECS_DIR}/executive-summary.md` with the following sections. Write clearly and concisely — this document is for stakeholders, not developers.

---

#### 1. Feature Overview

- **Feature Name**: (from spec.md title)
- **Branch**: `{BRANCH}`
- **Report Date**: (today's date)
- **Status**: [READY FOR RELEASE / CONDITIONALLY READY / NOT READY]

One paragraph (3–5 sentences) summarising what was built, why it was built, and what business value it delivers. Avoid technical jargon.

---

#### 2. Delivery Metrics

| Metric | Value |
|--------|-------|
| Total Tasks | N |
| Tasks Completed | N (N%) |
| Acceptance Criteria | N |
| AC Pass Rate | N% |
| Test Cases Executed | N |
| Test Pass Rate | N% |
| Code Review Verdict | APPROVED / APPROVED WITH CONDITIONS / REVISE REQUIRED |
| Verification Decision | GO / NO-GO / CONDITIONAL GO |

---

#### 3. Key Decisions & Deviations

Summarise the 2–4 most significant architectural or design decisions made during this delivery, and note any approved deviations from the original plan:

- **Decision**: [brief description] — **Rationale**: [why]
- If there were no significant deviations, write: *Delivery proceeded as planned.*

---

#### 4. Risks & Issues

| Risk / Issue | Severity | Status | Mitigation |
|--------------|----------|--------|------------|
| …            | Low / Medium / High | Open / Resolved | … |

If none, write: *No significant risks or issues identified.*

---

#### 5. Technical Debt Summary

Summarise technical debt from `review.md` (if any):

| ID | Description | Severity | Recommended Action |
|----|-------------|----------|--------------------|
| … | … | … | … |

If none, write: *No technical debt recorded.*

---

#### 6. Recommendation

**Recommendation**: [RELEASE / RELEASE WITH CONDITIONS / HOLD]

Provide a 2–3 sentence recommendation for stakeholders. Include any conditions or follow-up actions required before or after release.

---

### Completion

1. Write `{SPECS_DIR}/executive-summary.md`.
2. **Automatically run eval scoring** by executing in the terminal from the **project root**:
   `audi eval report --feature {FEATURE_NAME} --write`
   (Alternatively: `audi eval report --project-dir ".audi/specs/{FEATURE_NAME}" --write`)
   If it succeeds, report the overall score and grade in chat. If it fails (e.g. missing artifacts), note the failure but do not block completion.
3. Output the recommendation, key metrics, and eval score to the chat.
4. Inform the user that the ADLC workflow for this feature is now **complete**.
5. Suggest next steps: open the dashboard (`audi dashboard`), create a PR, schedule a release, or address any outstanding conditions.
