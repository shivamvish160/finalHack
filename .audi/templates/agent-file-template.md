# [PROJECT NAME] Development Guidelines

Auto-generated from all feature plans. Last updated: [DATE]

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

[EXTRACTED FROM ALL PLAN.MD FILES]

## Project Structure

```text
[ACTUAL STRUCTURE FROM PLANS]
```

## Commands

[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES]

## Context Rules

- Check graphify before broad repository reads.
- Refresh graphify when the graph is missing or stale.
- Limit fallback reads to graph-identified files or a bounded target set.

## Code Style

[LANGUAGE-SPECIFIC, ONLY FOR LANGUAGES IN USE]

## Recent Changes

[LAST 3 FEATURES AND WHAT THEY ADDED]

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
