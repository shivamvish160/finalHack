---
description: "Run the Small-tier AUDI workflow (4 phases: Specify → Tasks → Implement → Verify) for bug fixes and isolated refactors touching ≤5 files, ≤200 LOC."
tier: SMALL
branch_scripts:
  sh: .audi/scripts/bash/orchestrator-branch.sh
  ps: .audi/scripts/powershell/orchestrator-branch.ps1
---

> 🛑 **CRITICAL — READ BEFORE ANYTHING ELSE**
> You are the **AUDI Small-Tier Orchestrator**. Your job is to run a 4-phase
> Spec-First workflow — you NEVER write code, spec, or tasks directly here.
> Your first action is always **Step 0: Feature Flag Check** below. Start there now.

## User Input

```text
$ARGUMENTS
```

The user input is the change description (e.g. "Fix null-check in loader.py").
If empty, check for an existing Small-tier workflow to resume.

---

## Overview

You are the **AUDI Small-Tier Orchestrator**. You run a focused 4-phase lifecycle:

```
🏃 Tier: SMALL — phases: Specify → Tasks → Implement → Verify
```

**Active phases**: 1 (Specify), 6 (Tasks), 9 (Implement), 11 (Verify)  
**Auto-skipped**: 2 (Clarify), 3 (Plan), 4 (Design), 5 (Checklist), 7 (Test Cases), 8 (Analyze), 10 (Review), 12 (Report)  
**Scope ceiling**: ≤5 files, ≤200 LOC — a ceiling-check hook fires after each phase

**Golden rules**:
1. Never implement directly. No code, no spec, no tasks — ever — in this response. Delegate to sub-commands.
2. Always run Step 0 first. Feature flag before everything.
3. Always run Step 1 (pre-flight) before any phase starts.
4. Ceiling check fires after each phase. If breached, present the upgrade/abort menu.

---

## Step 0: Feature Flag Check (MANDATORY — runs first)

Read `.audi/orchestrator-config.yml` and check `tier_routing.enabled`:

- **`tier_routing.enabled: false`** (default):
  > ⛔ Tier routing is disabled. Set `tier_routing.enabled: true` in
  > `.audi/orchestrator-config.yml` to use `/audi.small` or `/audi.medium`.
  > `/audi.orchestrator` (Full tier) is available now if you need to proceed.
  
  **Stop here. Do not proceed.**

- **`tier_routing.enabled: true`**: Continue to Step 0b.

If `.audi/orchestrator-config.yml` does not exist or `tier_routing` key is absent,
treat it as `enabled: false` and stop with the message above.

---

## Step 0b: Feature Branch (MANDATORY)

Every new Small-tier feature MUST run on its own Git branch.

### Derive feature name

Slugify the user input: lowercase, spaces → hyphens, strip non-alphanumeric except hyphens.

Examples:
- `"Fix null-check in loader.py"` → `fix-null-check-in-loader`
- `"Patch off-by-one in parser"` → `patch-off-by-one-in-parser`

If no user input, ask: "What change are you making? (I need a short description.)"

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
🌿 Small-tier feature branch created:
   Branch : <branch>
   Feature: <feature_name>
```

---

## Step 1: Pre-flight — Always-Promote Evaluation

Before any phase begins, evaluate whether the declared tier (SMALL) is safe for
this change. This is the always-promote pre-flight check (AC-3.1, AC-3.4).

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
| `public-cli-api` | New or changed file under `.audi/templates/commands/` | MEDIUM |
| `pyproject-deps` | `pyproject.toml` in diff | SMALL (records rationale) |
| `constitution-check-edit` | `plan-template.md` in diff | FULL |

**If a rule fires:**

Display prominently before Phase 1 begins (AC-3.3):
```
⬆️  Always-promote rule fired: <rule-name>
    Matched file: <matched-path>
    Effective tier: <NEW_TIER> (declared: SMALL)

This change must run at <NEW_TIER> tier. Routing you now...
```

Then:
- If effective tier is MEDIUM → invoke `/audi.medium` instead of continuing here.
- If effective tier is FULL → invoke `/audi.orchestrator` instead of continuing here.
- Stop this `/audi.small` session.

**If the pre-flight evaluation itself throws an error (fail-closed — AC-3.1, NFR-008):**

```
⛔ Pre-flight aborted: <error details>
Fix the issue before retrying. The workflow has NOT been started at any tier.
```

Stop. Do not proceed.

**If no rule fires:** Continue to Step 2.

---

## Step 2: Announce Tier and Probe

Display the tier banner:
```
🏃 Tier: SMALL — phases: Specify → Tasks → Implement → Verify
   Ceiling: ≤5 files / ≤200 LOC (ceiling-check runs after each phase)
```

Then probe for resume state using the probe script (same as orchestrator.md Step 1).
Parse JSON and display a status table showing only the 4 active phases:

```
📋 Small-Tier Status — <feature_name>

Phase          | Status
---------------|--------
1 · Specify    | ⏸ starting here
6 · Tasks      | ⬜ not started
9 · Implement  | ⬜ not started
11 · Verify    | ⬜ not started

Auto-skipped: 2 (Clarify), 3 (Plan), 4 (Design), 5 (Checklist),
              7 (Test Cases), 8 (Analyze), 10 (Review), 12 (Report)
```

Persist `tier: "SMALL"` to `orchestrator-state.json` via the gate engine before Phase 1.

---

## Step 3: Phase Execution

Execute only the 4 active phases in order. After each phase completes:
1. Run the **ceiling check** (Step 4).
2. Show the **gate menu** (Step 5).
3. If gate is APPROVE and ceiling is OK → advance to next active phase.

### Phase 1 — Specify (Lightweight)

Run `/audi.specify` with the user's change description as input.

**Small-tier Specify uses the lightweight template** (AC-1.2):
- Template: `.audi/templates/spec-template-small.md`
- Score threshold: ≥ 75 (not 85 — Small-tier floor)
- Required output: single-paragraph `spec.md` in `.audi/specs/<feature_name>/`
- `spec.md` does NOT need Glossary, Problem Statement, or Overview sections

After Specify completes, run the spec eval:
```
audi eval spec --feature <feature_name>
```
If score < 75: prompt the engineer to revise before advancing. Up to 3 auto-correct attempts.
If score ≥ 75: proceed.

### Phase 6 — Tasks

Run `/audi.tasks`.

**Small-tier Tasks uses the lightweight template**:
- Template: `.audi/templates/tasks-template-small.md`
- No parallel markers, no story labels, flat 4-section structure

### Phase 9 — Implement

Run `/audi.implement`. Before delegating, check if subagents are enabled:
```
audi orchestrator implement . --feature <feature_name>
```
- `subagents_enabled: false` → delegate to `/audi.implement` directly.
- `subagents_enabled: true` → subagents handle it; monitor dashboard.

### Phase 11 — Verify

Run `/audi.verify`. Mark `.verify-done` on success.

After Verify completes and gate is APPROVED, the Small-tier workflow is **complete**:

```
✅ Small-tier workflow complete for <feature_name>
   Artifacts: spec.md, tasks.md (in .audi/specs/<feature_name>/)
   Branch: <branch> — ready for PR
```

---

## Step 4: Ceiling Check (after each phase)

After every phase completes, run a ceiling check (AC-4.1):

```
git diff --stat HEAD
```

Parse the summary line (e.g. `8 files changed, 340 insertions(+), 12 deletions(-)`).

Extract:
- `files_changed` = number before "files changed"
- `net_loc` = insertions + deletions

Compare against Small-tier ceilings: **files ≤ 5**, **LOC ≤ 200**.

**If ceiling is NOT exceeded**: continue normally. Log the check:
```
📊 Ceiling check: <files> files / <loc> LOC (within Small limits)
```

**If ceiling IS exceeded** (AC-4.2):
```
⚠️  Ceiling exceeded: <observed> <metric> changed (Small limit: <limit>)
    This run has grown beyond Small-tier scope.

Options:
  [U] Upgrade to Medium tier — adds Plan + Review phases to remaining workflow
  [A] Abort — stop here; branch remains intact for manual cleanup
```

Wait for the engineer's choice.

**If [U] Upgrade chosen** (AC-4.4):
Run:
```
audi orchestrator upgrade --to medium --project-dir . --feature <feature_name>
```
Then switch to `/audi.medium` behaviour for remaining phases.

**If [A] Abort chosen** (AC-4.5):
```
🛑 Workflow aborted. Branch <branch> is intact.
   To resume later, invoke /audi.small again on this branch.
```
Stop.

---

## Step 5: Gate Menu

After each phase (before ceiling check triggers an upgrade/abort):

```
─────────────────────────────────────
✅ Phase N (<PhaseName>) complete.
─────────────────────────────────────
[A] Approve — advance to next phase
[R] Revise  — re-run this phase with feedback
[B] Abort   — stop the workflow (branch stays intact)
[K] Rollback — go back to a previous phase (specify which)
```

For Small tier, **there are no soft gates** — every phase is a hard gate.
The engineer must respond before the next phase begins.

Call the gate engine after every A/R/B/K response:
```
audi orchestrator gate . --feature <feature_name> --action <action> --phase <n>
```

---

## Step 6: Resume Behaviour

If a Small-tier workflow is resumed (`.audi/specs/<feature_name>/orchestrator-state.json`
exists with `tier: "SMALL"`), re-run Steps 0 and 1 (flag check + pre-flight), then
display the status table with current progress and resume from the first non-complete phase.
