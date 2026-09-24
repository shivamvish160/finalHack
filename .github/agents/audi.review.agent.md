---
name: AUDI Review
description: Perform a structured code review against design.md and spec.md, evaluating design adherence, security, code quality, and technical debt, then produce review.md with a PR-readiness verdict.
handoffs:
  - label: Verify Implementation
    agent: audi.verify
    prompt: Run verification against acceptance criteria
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before review)**:
- Check if `.audi/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_review` key.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`): display it as an optional pre-hook.
  - **Mandatory hook** (`optional: false`): display it as an automatic pre-hook and execute it.
- If no hooks are registered or `.audi/extensions.yml` does not exist, skip silently.

## Outline

### Goal

Produce `review.md` — a structured code review report that evaluates the implementation against `design.md` and `spec.md`, surfaces technical debt and security concerns, and delivers a clear PR-readiness verdict.

When reviewing implementation details, use graphify first for repository
structure and refresh it if the graph is missing or stale before broad reads.

### Setup

1. Run `.audi/scripts/powershell/setup-plan.ps1 -Json` (Windows) or `.audi/scripts/bash/setup-plan.sh --json` (Linux/macOS) from repo root.
   - Read `.audi/init-options.json` → `script` field to decide which to use.
   - Parse JSON for `FEATURE_SPEC`, `IMPL_PLAN`, `SPECS_DIR`, `BRANCH`.
2. Load `spec.md` — acceptance criteria, user stories, non-functional requirements.
3. Load `plan.md` — architecture decisions, module breakdown.
4. Load `design.md` — component architecture, API contracts, data model.
5. Load `tasks.md` — implementation task list (verify all tasks are checked `[x]`).
6. Load `test-plan.md` — test cases and coverage expectations.

### Review Document

Write `{SPECS_DIR}/review.md` with the following sections.

---

#### 1. Overview

- **Feature**: (from spec.md title)
- **Branch**: `{BRANCH}`
- **Review Date**: (today's date)
- **Reviewer**: AI-assisted code review
- **Verdict**: [APPROVED / APPROVED WITH CONDITIONS / REVISE REQUIRED]

---

#### 2. Design Adherence

For each major component or module in `design.md`:

- **Implemented as designed?** (Yes / Partial / No)
- **Deviations**: List any deviations from `design.md` and classify each as:
  - `Acceptable` — minor improvement or equivalent approach
  - `Concern` — diverges from design intent, needs discussion
  - `Blocker` — violates architectural constraint from design.md or constitution.md

---

#### 3. Acceptance Criteria Coverage

For each acceptance criterion in `spec.md`:

| AC # | Description | Covered in Code | Test Coverage | Status |
|------|-------------|-----------------|---------------|--------|
| AC-1 | …           | Yes / Partial / No | Yes / No   | ✅ / ⚠️ / ❌ |

---

#### 4. Security Review

Evaluate the implementation for:

- **Input validation**: All external inputs validated/sanitised?
- **Authentication & authorisation**: Access controls enforced correctly?
- **Secrets management**: No secrets hardcoded; using env vars or vault?
- **Dependency risk**: Any new dependencies with known CVEs?
- **Data exposure**: Sensitive data not logged or leaked in responses?

List each finding as `OK`, `Low Risk`, `Medium Risk`, or `High Risk`.

---

#### 5. Code Quality

- **Readability**: Code is clear, well-named, and sufficiently commented.
- **Duplication**: No significant code duplication; shared logic extracted.
- **Error handling**: Errors caught and handled; no silent failures.
- **Test coverage**: Unit and integration tests present for critical paths.
- **Logging & observability**: Structured logging in place for key operations.
- **Simplicity**: Would a senior engineer call any part of this overcomplicated? Flag any abstraction, layer, or pattern not required by the spec or tasks.
- **Scope traceability**: Does every changed file trace to a task ID in `tasks.md`? Flag any change that cannot be linked to a task. If `tasks.md` does not exist, rate this dimension `N/A - tasks.md not found`.

Rate each area: `Good` / `Needs Improvement` / `Blocking Issue`.

---

#### 6. Technical Debt

List any technical debt introduced or discovered:

| ID | Description | Severity | Recommended Action |
|----|-------------|----------|--------------------|
| TD-1 | … | Low / Medium / High | … |

If none, write: *No significant technical debt identified.*

---

#### 7. PR Readiness Checklist

- [ ] All acceptance criteria are covered
- [ ] No high-severity security findings
- [ ] No architectural blockers
- [ ] All tasks in `tasks.md` are checked `[x]`
- [ ] Test plan (`test-plan.md`) is satisfied
- [ ] No hardcoded secrets or environment-specific values
- [ ] Documentation updated (README, API docs, etc.)

---

#### 8. Summary & Recommendation

**Verdict**: [APPROVED / APPROVED WITH CONDITIONS / REVISE REQUIRED]

Provide a 2–4 sentence summary of the overall quality of the implementation. If the verdict is not APPROVED, list the specific blockers that must be addressed before the PR can be merged.

---

### Completion

After writing `review.md`:

1. Output the review summary to the chat.
2. If verdict is **APPROVED** or **APPROVED WITH CONDITIONS**: proceed to `/audi.verify`.
3. If verdict is **REVISE REQUIRED**: list the blockers clearly and instruct the user to address them before re-running `/audi.review`.
