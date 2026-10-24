---
description: Stage 3 — Build & Verify an approved plan (implement, write tests, run verification)
argument-hint: <NN>  |  <NN> resume  |  <NN> retest
---

# /build — Stage 3: Build & Verify

Arguments: `$ARGUMENTS`

Read `CLAUDE.md`, the approved spec and the approved plan for NN first.

## Modes

- **`<NN>` (implement):** the plan must be `status: approved`. Run the full
  flow below.
- **`<NN> resume`:** the plan is `approved` and some steps are already ticked.
  Continue from the first unticked step.
- **`<NN> retest`:** the plan is `built`, `approved` or `reviewed`, and named
  findings or failures need fixing. Fix only those. Then re-run the
  verification for the changed area, and the full suite when appropriate.
  Set the plan back to `built`.

If the plan's status doesn't match the mode, stop and name the right command.

## Flow

1. **Implement only what the approved plan allows.** Work through
   "Implementation steps" in order and tick each one (`- [x]`).
   - If the **technical** approach must change, stop and recommend
     `/plan NN revise "…"`.
   - If **product behaviour** would change, stop and recommend reopening the
     spec (`/spec NN revise "…"`).
   - Don't improvise around either.
2. **Migrations.** If models changed, run
   `.venv/Scripts/python.exe manage.py makemigrations <app>` and then
   `migrate`.
3. **Write or update tests yourself:**
   - derive them from the approved spec's acceptance criteria, not the
     implementation;
   - give important ACs appropriate coverage, each naming its AC;
   - prefer behaviour-focused tests to brittle source or markup assertions;
   - never weaken an existing test just to make it pass. Change one only
     where the approved spec deliberately changes that behaviour, and say so.
4. **Verify directly**, in this order, with `.venv/Scripts/python.exe`:
   1. focused tests;
   2. `manage.py makemigrations --check --dry-run`;
   3. `manage.py check`;
   4. `manage.py test` (the full suite).
5. **If a test exposes an application bug:**
   - fix the application, as long as the fix stays within the approved plan;
   - don't weaken the test;
   - if the fix would change product behaviour or go beyond the plan, stop
     and report it.

   Environment failures: stop and report.
6. **Manual or browser checks:** do any the plan requires. If the browser
   tools aren't available, stop **once** and give the user a concise manual
   checklist, then resume when they report back. Record only what was
   actually checked, and keep user-reported results apart from measured
   ones.
7. **Record concisely in the plan:**
   - "Files changed" (created, modified or deleted);
   - important decisions and deviations;
   - "Test results" (the commands run, pass/fail counts, anything
     unresolved).
8. **Set `status: built`** only when the required verification is complete
   and green, or the user has accepted the failures.

## Optional sub-agents

`test-author` and `test-runner` are **optional**. Use one only when
independent test design or verification materially improves correctness, for
example:
- **`test-author`:** complicated authorization rules, race conditions,
  complex business rules or security-sensitive behaviour;
- **`test-runner`:** an unusually risky change where independent
  verification is valuable.

For normal features, `/build` does both itself. Never invoke them
automatically.

## Token efficiency

- Don't send large copies of CLAUDE.md, the spec or the plan to sub-agents.
- Keep reports short when checks pass.
- Don't repeat checks that already passed unless affected code changed.
- Prefer one build-and-verify pass.

## Final report

End with exactly this and nothing after it:

```
File:   .claude/plans/NN-slug.md
Mode:   implement | resume | retest
Status: built | approved (blocked: <reason>)
Tests:  <passed>/<total>; drift: clean|DRIFT; check: ok|issues
Next:   <exact command>
```

The `Next:` line should be: if built, `/review NN` (or `/done NN` after a
retest of review fixes that need no further review); if blocked, the exact fix
command (e.g. `/plan NN revise "…"` or `/build NN retest`).
