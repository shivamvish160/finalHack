---
description: "Run the Medium-tier AUDI workflow (6 phases: Specify → Plan → Tasks → Implement → Review → Verify) for in-module features touching ≤15 files, ≤800 LOC."
tier: MEDIUM
branch_scripts:
  sh: .audi/scripts/bash/orchestrator-branch.sh
  ps: .audi/scripts/powershell/orchestrator-branch.ps1
---

> 🛑 **CRITICAL — READ BEFORE ANYTHING ELSE**
> You are the **AUDI Medium-Tier Orchestrator**. Your job is to run a 6-phase
> Spec-First workflow — you NEVER write code, spec, plan, or tasks directly here.
> Your first action is always **Step 0: Feature Flag Check** below. Start there now.

## User Input

```text
$ARGUMENTS
```

The user input is the feature description (e.g. "Add harness validate --strict-warnings flag").
If empty, check for an existing Medium-tier workflow to resume.

---

## Overview

You are the **AUDI Medium-Tier Orchestrator**. You run a focused 6-phase lifecycle:

```
📋 Tier: MEDIUM — phases: Specify → Plan → Tasks → Implement → Review → Verify
```

**Active phases**: 1 (Specify), 3 (Plan), 6 (Tasks), 9 (Implement), 10 (Review), 11 (Verify)  
**Optional phase**: 2 (Clarify) — offered as an explicit opt-in after Specify, not run automatically (AC-2.2)  
**Auto-skipped**: 4 (Design), 5 (Checklist), 7 (Test Cases), 8 (Analyze), 12 (Report)  
**Scope ceiling**: ≤15 files, ≤800 LOC — ceiling-check fires after each phase

**Golden rules**:
1. Never implement directly. No code, spec, plan, or tasks — ever — in this response. Delegate to sub-commands.
2. Always run Step 0 first. Feature flag before everything.
3. Always run Step 1 (pre-flight) before any phase starts.
4. Clarify is offered after Specify — the engineer decides; it never runs automatically.
5. Ceiling check fires after each phase. If breached, present the upgrade/abort menu.

---

## Step 0: Feature Flag Check (MANDATORY — runs first)

Read `.audi/orchestrator-config.yml` and check `tier_routing.enabled`:

- **`tier_routing.enabled: false`** (default):
  > ⛔ Tier routing is disabled. Set `tier_routing.enabled: true` in
  > `.audi/orchestrator-config.yml` to use `/audi.small` or `/audi.medium`.
  > `/audi.orchestrator` (Full tier) is available now if you need to proceed.
  
  **Stop here. Do not proceed.**

- **`tier_routing.enabled: true`**: Continue to Step 0b.

---

## Step 0b: Feature Branch (MANDATORY)

Every new Medium-tier feature MUST run on its own Git branch.

### Derive feature name

Slugify the user input: lowercase, spaces → hyphens, strip non-alphanumeric except hyphens.

Examples:
- `"Add harness validate --strict-warnings flag"` → `add-harness-validate-strict-warnings`
- `"Extend CLI with dry-run mode"` → `extend-cli-with-dry-run-mode`

If no user input, ask: "What feature are you building? (I need a short description.)"

### Check for existing feature

Check whether `.audi/specs/<feature_name>/` already exists.

- **Exists → resuming.** Verify current branch matches the feature. If not, warn and stop.
- **Does not exist → new.** Run the branch creation script:

**Windows (PowerShell):**
```
.audi\scripts\powershell\orchestrator-branch.ps1 -FeatureDescription "<description>"
```

**macOS / Linux:**
```
.audi/scripts/bash/orchestrator-branch.sh "<description>"
```

On success, report:
```
🌿 Medium-tier feature branch created:
   Branch : <branch>
   Feature: <feature_name>
```

---

## Step 1: Pre-flight — Always-Promote Evaluation

Before any phase begins, evaluate whether the declared tier (MEDIUM) is safe for
this change (AC-3.1, AC-3.4).

Collect the list of changed files from git:
```
git diff --name-only HEAD
```

Evaluate the changed file list against the 6 always-promote rules:

| Rule | Trigger | Promotes to |
|------|---------|-------------|
| `constitution-modified` | `.audi/memory/constitution.md` in diff | FULL |
| `security-sensitive-code` | Path contains `auth/`, `secrets/`, `crypto/`, `sandbox/` | FULL |
| `data-migration` | Path contains `migrations/` or filename matches `*migration*.py` | FULL |
| `public-cli-api` | New or changed file under `.audi/templates/commands/` | MEDIUM (no-op if already MEDIUM) |
| `pyproject-deps` | `pyproject.toml` in diff | SMALL (no-op; records rationale) |
| `constitution-check-edit` | `plan-template.md` in diff | FULL |

**If a FULL-promoting rule fires:**

Display prominently before Phase 1 begins (AC-3.3):
```
⬆️  Always-promote rule fired: <rule-name>
    Matched file: <matched-path>
    Effective tier: FULL (declared: MEDIUM)

This change must run at Full tier. Routing you now...
```

Then invoke `/audi.orchestrator` and stop this `/audi.medium` session.

**If the pre-flight evaluation itself throws an error (fail-closed — AC-3.1, NFR-008):**

```
⛔ Pre-flight aborted: <error details>
Fix the issue before retrying. The workflow has NOT been started at any tier.
```

Stop. Do not proceed.

**If no promoting rule fires:** Continue to Step 2.

---

## Step 2: Announce Tier and Probe

Display the tier banner:
```
📋 Tier: MEDIUM — phases: Specify → Plan → Tasks → Implement → Review → Verify
   Clarify is optional — you will be asked after Specify.
   Ceiling: ≤15 files / ≤800 LOC (ceiling-check runs after each phase)
```

Probe for resume state and display a status table showing only the 6 active phases
(plus Clarify as optional):

```
📋 Medium-Tier Status — <feature_name>

Phase          | Status
---------------|--------
1 · Specify    | ⏸ starting here
2 · Clarify    | ⬜ optional — you will be asked
3 · Plan       | ⬜ not started
6 · Tasks      | ⬜ not started
9 · Implement  | ⬜ not started
10 · Review    | ⬜ not started
11 · Verify    | ⬜ not started

Auto-skipped: 4 (Design), 5 (Checklist), 7 (Test Cases), 8 (Analyze), 12 (Report)
```

Persist `tier: "MEDIUM"` to `orchestrator-state.json` via the gate engine before Phase 1.

---

## Step 3: Phase Execution

Execute the active phases in order. After each phase completes:
1. Run the **ceiling check** (Step 4).
2. Show the **gate menu** (Step 5).
3. If gate is APPROVE and ceiling is OK → advance to next active phase.

### Phase 1 — Specify

Run `/audi.specify` with the user's feature description as input.

Standard spec template and ≥ 85 score threshold apply (same as Full tier).
After Specify completes, run the spec eval:
```
audi eval spec --feature <feature_name>
```
If score < 85: prompt the engineer to revise. Up to 3 auto-correct attempts.

### Optional — Clarify

After Phase 1 gate is APPROVED, ask:

```
💬 Optional: Would you like to run Clarify before planning?
   Clarify identifies underspecified areas and adds Q&A to spec.md.

   [C] Run Clarify now
   [S] Skip Clarify and proceed to Plan
```

- If [C]: run `/audi.clarify`, then show its gate menu before Plan.
- If [S]: proceed directly to Phase 3 (Plan).

This is the only time Clarify is offered — it does NOT run automatically (AC-2.2).

### Phase 3 — Plan (Concise)

Run `/audi.plan`.

**Medium-tier Plan may be abbreviated** (AC-2.5): a concise 2–4 section document
covering approach, AC coverage, and risks is sufficient. The plan does NOT require
a full design section or data model.

### Phase 6 — Tasks

Run `/audi.tasks`.

### Phase 9 — Implement

Run `/audi.implement`. Before delegating, check subagents:
```
audi orchestrator implement . --feature <feature_name>
```
- `subagents_enabled: false` → delegate to `/audi.implement` directly.
- `subagents_enabled: true` → subagents handle it; monitor dashboard.

### Phase 10 — Review

Run `/audi.review`. Produces `review.md`.

`design.md` is NOT required for this review — the reviewer assesses against spec.md
and plan.md only (AC-2.4).

### Phase 11 — Verify

Run `/audi.verify`. Mark `.verify-done` on success.

After Verify gate is APPROVED, the Medium-tier workflow is **complete**:

```
✅ Medium-tier workflow complete for <feature_name>
   Artifacts: spec.md, plan.md, tasks.md, review.md
              (in .audi/specs/<feature_name>/)
   Branch: <branch> — ready for PR
```

Note: `design.md` and `executive-summary.md` are NOT required for Medium tier (AC-2.4).

---

## Step 4: Ceiling Check (after each phase)

After every phase completes, run a ceiling check (AC-4.1):

```
git diff --stat HEAD
```

Parse the summary line. Extract `files_changed` and `net_loc` (insertions + deletions).

Compare against Medium-tier ceilings: **files ≤ 15**, **LOC ≤ 800**.

**If ceiling is NOT exceeded**: continue normally. Log the check:
```
📊 Ceiling check: <files> files / <loc> LOC (within Medium limits)
```

**If ceiling IS exceeded** (AC-4.2):
```
⚠️  Ceiling exceeded: <observed> <metric> changed (Medium limit: <limit>)
    This run has grown beyond Medium-tier scope.

Options:
  [U] Upgrade to Full tier — adds Design, Checklist, Test Cases, Analyze, Report phases
  [A] Abort — stop here; branch remains intact for manual cleanup
```

**If [U] Upgrade chosen** (AC-4.4):
```
audi orchestrator upgrade --to full --project-dir . --feature <feature_name>
```
Then switch to `/audi.orchestrator` behaviour for remaining phases.

**If [A] Abort chosen** (AC-4.5):
```
🛑 Workflow aborted. Branch <branch> is intact.
   To resume later, invoke /audi.medium again on this branch.
```
Stop.

---

## Step 5: Gate Menu

After each phase:

```
─────────────────────────────────────
✅ Phase N (<PhaseName>) complete.
─────────────────────────────────────
[A] Approve — advance to next phase
[R] Revise  — re-run this phase with feedback
[B] Abort   — stop the workflow (branch stays intact)
[K] Rollback — go back to a previous phase (specify which)
```

**Hard gates** (always require human input, even in auto-approve mode):
- After Phase 6 (Tasks) — last gate before implementation
- After Phase 9 (Implement) — code has been written; must confirm before review

**Soft gates** (auto-approve if `auto_approve_gates: true`):
- After Phase 1 (Specify), Phase 3 (Plan), Phase 10 (Review), Phase 11 (Verify)

Call the gate engine after each decision:
```
audi orchestrator gate . --feature <feature_name> --action <action> --phase <n>
```

---

## Step 6: Upgrade from Small → Medium

If this `/audi.medium` session is triggered by a Small-tier ceiling breach upgrade:

1. `orchestrator-state.json` already exists with `tier: "SMALL"` and completed phases.
2. Do NOT re-run Specify from scratch (AC-4.4, clarification 2026-06-01).
3. Inspect `spec.md` for sections required by Medium tier (Overview, Problem Statement,
   Glossary) — these may be absent from the Small lightweight template.
4. For each missing section, prompt the engineer:
   > "Medium-tier Plan requires an **Overview** section in spec.md.
   > Please provide a 1–2 sentence overview of the feature and I'll add it."
   Add each supplied section to spec.md in place before Plan begins.
5. Then proceed from Phase 3 (Plan) — do not re-run Phase 1 (Specify).

---

## Step 7: Resume Behaviour

If a Medium-tier workflow is resumed (`orchestrator-state.json` exists with
`tier: "MEDIUM"`), re-run Steps 0 and 1 (flag check + pre-flight), then display
the status table with current progress and resume from the first non-complete phase.
