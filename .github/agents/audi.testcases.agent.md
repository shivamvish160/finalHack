---
description: Generate a full test plan and executable test cases from tasks.md with end-to-end traceability.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Produce a complete, implementation-ready testing package for the active feature using existing planning artifacts.

Required output:

- `test-plan.md` in the active `FEATURE_DIR`

Optional output (only if user explicitly asks):

- `traceability-matrix.md`
- `test-cases.csv`

## Stack Profile Overrides

If user input indicates **Playwright** and an **MVC application with embedded React widget(s)**, apply these defaults automatically:

- Prefer `e2e` and `integration` coverage using Playwright.
- Treat MVC host pages and React widgets as separate test surfaces with explicit integration checks.
- Include widget bootstrap/lifecycle validation (mount, re-render, unmount, error fallback).
- Include host↔widget communication validation (props/config, DOM container availability, API/session handoff).
- Include cross-browser matrix (Chromium, Firefox, WebKit) and responsive viewport checks.

If user does not specify test tooling, infer from `plan.md` and existing repository conventions.

## Execution Steps

1. **Initialize context**
   - Run `.audi/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` once from repo root and parse JSON for `FEATURE_DIR` and `AVAILABLE_DOCS`.
   - Resolve absolute paths for:
     - `SPEC = FEATURE_DIR/spec.md`
     - `PLAN = FEATURE_DIR/plan.md`
     - `TASKS = FEATURE_DIR/tasks.md`
   - Abort with a clear message if any required file is missing.
   - For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load artifacts**
   - Required: `spec.md`, `plan.md`, `tasks.md`
   - Optional (if present): `data-model.md`, `research.md`, `quickstart.md`, `contracts/`

3. **Build traceability model**
   - Extract and normalize:
     - User stories (`US1`, `US2`, ...)
     - Functional requirements (`FR-*`)
     - Acceptance criteria
     - Task IDs (`T001`, ...)
   - Map each test case to at least one of: user story, requirement, acceptance criterion, task.
   - Flag and report any unmapped story/requirement/task.

4. **Generate `test-plan.md`**
   - Create or update `FEATURE_DIR/test-plan.md`.
   - The plan MUST include all sections below:

   ```markdown
   # Test Plan: [Feature Name]

   ## 1. Scope
   - In Scope
   - Out of Scope

   ## 2. Test Strategy
   - Levels: unit, integration, end-to-end, contract (if applicable)
   - Risk priorities: P0/P1/P2/P3
   - Entry/Exit criteria

   ## 3. Environment & Data
   - Environments
   - Test data strategy
   - Tooling from plan.md

   ## 4. Story Coverage
   - One subsection per user story with independent validation criteria

   ## 5. Test Cases
   - Table with: TC ID, Priority, Level, Story, Requirement/AC refs, Preconditions, Steps, Expected Result

   ## 6. Regression Set
   - Minimum must-run suite for release confidence

   ## 7. Risks & Mitigations

   ## 8. Traceability Matrix
   - FR/AC/US/Task ↔ Test Case mapping
   ```

5. **Test case quality rules (mandatory)**
   - Every test case must be atomic and independently executable.
   - Use stable IDs: `TC-001`, `TC-002`, ...
   - Each test case must define:
     - Preconditions
     - Exact execution steps
     - Expected result
     - Priority (`P0`..`P3`)
     - Test level (`unit|integration|e2e|contract|non-functional`)
   - Include negative/error-path and edge-case coverage for each user story.
   - Where non-functional requirements exist (performance/security/reliability), add explicit non-functional tests.

6. **Playwright execution details (when Playwright is selected)**
    - Add a `## Playwright Execution` section inside `test-plan.md` with:
       - Browser matrix: Chromium, Firefox, WebKit
       - Execution modes:
          - Headless CI run
          - Headed local debug run
       - Recommended artifact capture:
          - Traces on retry/failure
          - Video on failure
          - Screenshots on failure
    - Provide concise runnable command examples that match project tooling (e.g., npm/pnpm/yarn).
    - Ensure at least one representative end-to-end flow explicitly validates widget behavior inside the MVC host page in a real browser context.

7. **Completeness checks before finalizing**
   - No `TBD`, `TODO`, placeholder text, or unresolved references.
   - Every user story from `spec.md` has at least one P0/P1 validation test.
   - Every task phase from `tasks.md` is represented in coverage.
   - Report any gaps with concrete recommendations.

8. **Final report in chat**
   - Output:
     - Path to `test-plan.md`
     - Number of total test cases
     - Cases by level and priority
     - Coverage % by user story
     - List of uncovered requirements/tasks (if any)
   - Suggest next command: `/audi.implement` (to build missing tests/code) or `/audi.analyze` (to audit consistency).

## Operating Constraints

- Do not alter `spec.md`, `plan.md`, or `tasks.md` unless user explicitly asks.
- Prefer deterministic, concise, implementation-ready tests over narrative text.
- If user requests framework-specific format (e.g., Playwright, pytest, xUnit), reflect that in test case structure.
