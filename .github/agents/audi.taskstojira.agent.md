---
description: Convert existing tasks into Jira sub-tasks, parented to the configured story, based on tasks.md.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. Run `.audi/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` from repo root and parse `FEATURE_DIR`. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. Check that Jira is configured and a story key is available before asking for consent:

   ```bash
   audi jira mine --max 1
   ```

   If the result reports `ok: false` (not configured), tell the user Jira is not
   configured and stop — do not proceed to the consent prompt.

3. **Obtain one consent confirmation for the whole batch** — never per-task:

   ```
   ⚡ Impact: Creates one Jira sub-task per pending task in tasks.md, parented to the
      project's configured story key. Tasks that already have a recorded sub-task
      (from a prior run) are skipped, not duplicated.
   ❓ Convert tasks.md into Jira sub-tasks?
      [Y] Yes — convert all eligible tasks
      [N] No  — skip
   ```

   Only proceed to step 4 after an explicit `[Y]`.

4. Run the bulk conversion:

   ```bash
   audi jira taskstojira "$FEATURE_DIR"
   ```

5. Report the result to the user:
   - If `ok: false` — show the `error` field verbatim (e.g. no story key configured,
     Jira not configured) and stop.
   - If `ok: true` — report:
     - Every entry in `created`: task ID → new Jira sub-task key.
     - Every entry in `skipped`: task ID → existing sub-task key and the reason
       ("already converted").
     - Every entry in `failed`: task ID → error, so the user can retry just those
       tasks on the next run (re-running is safe and idempotent — already-created
       sub-tasks are never duplicated).

> [!CAUTION]
> UNDER NO CIRCUMSTANCES call `audi jira taskstojira` before the user has explicitly
> approved the consent prompt in step 3.
