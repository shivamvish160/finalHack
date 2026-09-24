---
description: Execute the test plan from test-plan.md against the implementation, record pass/fail results for each acceptance criterion, and produce verification-report.md with a go/no-go decision.
handoffs:
  - label: Generate Executive Report
    agent: audi.report
    prompt: Generate executive summary report
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before verify)**:
- Check if `.audi/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_verify` key.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`): display it as an optional pre-hook.
  - **Mandatory hook** (`optional: false`): display it as an automatic pre-hook and execute it.
- If no hooks are registered or `.audi/extensions.yml` does not exist, skip silently.

## Outline

Before verifying results, consult graphify for the feature's repository context
so the validation report reflects the same graph-first workflow used during
implementation.

### Goal

Produce `verification-report.md` — a formal verification record that maps each acceptance criterion to test results, and delivers a clear **Go / No-Go** decision for release.

Also create the `.verify-done` marker file to signal completion to the orchestrator.

### Setup

1. Run `.audi/scripts/powershell/setup-plan.ps1 -Json` (Windows) or `.audi/scripts/bash/setup-plan.sh --json` (Linux/macOS) from repo root.
   - Read `.audi/init-options.json` → `script` field to decide which to use.
   - Parse JSON for `FEATURE_SPEC`, `IMPL_PLAN`, `SPECS_DIR`, `BRANCH`.
2. Load `spec.md` — acceptance criteria.
3. Load `test-plan.md` — test cases, expected outcomes, coverage matrix.
4. Load `review.md` — any conditions or blockers from the code review.
5. Load `tasks.md` — confirm all tasks are `[x]` (if not, list unchecked tasks as a blocker).

### Verification Document

Write `{SPECS_DIR}/verification-report.md` with the following sections.

---

#### 1. Overview

- **Feature**: (from spec.md title)
- **Branch**: `{BRANCH}`
- **Verification Date**: (today's date)
- **Tester**: AI-assisted verification
- **Decision**: [GO / NO-GO / CONDITIONAL GO]

---

#### 2. Acceptance Criteria Results

For each acceptance criterion in `spec.md`:

| AC # | Description | Test Case(s) | Result | Notes |
|------|-------------|--------------|--------|-------|
| AC-1 | …           | TC-1, TC-2   | ✅ PASS / ❌ FAIL / ⚠️ PARTIAL | … |

---

#### 3. Test Execution Summary

For each test case in `test-plan.md`:

| TC # | Test Case | Type | Expected | Actual | Status |
|------|-----------|------|----------|--------|--------|
| TC-1 | …         | Unit / Integration / E2E | … | … | ✅ / ❌ / ⚠️ |

**Summary counts**:
- Total test cases: N
- Passed: N
- Failed: N
- Blocked / Skipped: N

---

#### 4. Review Conditions Check

If `review.md` verdict was **APPROVED WITH CONDITIONS**, verify each condition:

| Condition | Addressed? | Evidence |
|-----------|------------|----------|
| …         | Yes / No   | …        |

If verdict was **APPROVED** (no conditions), write: *No review conditions to verify.*

---

#### 5. Non-Functional Requirements

Verify any NFRs from `spec.md` (performance, security, accessibility, etc.):

| NFR | Requirement | Result | Notes |
|-----|-------------|--------|-------|
| …   | …           | ✅ / ❌ / N/A | … |

---

#### 6. Go / No-Go Decision

**Decision**: [GO / NO-GO / CONDITIONAL GO]

| Criterion | Status |
|-----------|--------|
| All ACs pass | ✅ / ❌ |
| No open review blockers | ✅ / ❌ |
| All tasks completed | ✅ / ❌ |
| NFRs satisfied | ✅ / ❌ |

Provide a 2–3 sentence justification for the decision. If **NO-GO**, list specific failures that must be resolved before re-verification.

---

### Completion

1. Write `{SPECS_DIR}/verification-report.md`.
2. Create the marker file `{SPECS_DIR}/.verify-done` (empty file).
3. Output the decision summary to the chat.
4. If **GO** or **CONDITIONAL GO**: proceed to `/audi.report`.
5. If **NO-GO**: list failures and instruct the user to fix them and re-run `/audi.verify`.
