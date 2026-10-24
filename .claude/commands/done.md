---
description: Stage 5 — close a reviewed step, settle findings, and update CLAUDE.md
argument-hint: <NN>
---

# /done — Stage 5: Done

Arguments: `$ARGUMENTS`

## Flow

1. **Confirm before closing:**
   - the plan is `status: reviewed` (if not, stop and name the right
     command), and the spec is `approved`;
   - the required verification from `/build` is recorded as green;
   - no High finding is unresolved;
   - every important Medium finding is fixed, accepted or deliberately
     deferred.
2. **Verify only if needed.**
   - If no code changed after the last successful full-suite run (including
     verified review fixes), don't re-run the suite.
   - If code did change, re-run the focused tests for the changed area and
     the full suite, in CLAUDE.md's standard order.
   - If anything fails, stop and recommend `/build NN retest`. Don't close
     the step.
3. **Settle the open findings.** Ask the user once, listing them, and label
   each one with the answer:
   - **High:** must be resolved, or the step stays blocked;
   - **Medium:** fixed, accepted or deferred, deliberately;
   - **Low:** accepted by default.
4. **Update `CLAUDE.md` with lasting knowledge only:**
   - structural decisions, with the reason (apps, model relationships, URL
     namespaces, permission patterns);
   - important conventions;
   - real known limitations, meaning only future items that are genuinely
     useful;
   - a "Steps landed" line, `NN — <title>: <one-sentence summary>`, with the
     correct test count.

   Don't add cosmetic findings, temporary documentation mistakes, minor test
   clean-up or findings that are already fixed. Keep it brief: the reasoning
   and the structure, not a list of files.
5. **Set the spec and the plan to `status: done`.**
6. If this is a git repo, suggest a commit message (`NN: <title>`), but
   **don't commit** unless the user asks.

## Optional verification agent

`test-runner` is optional. Use it only when independent final verification
is materially useful.

## Final report

End with exactly this and nothing after it:

```
File:   .claude/specs/NN-slug.md, .claude/plans/NN-slug.md, CLAUDE.md
Mode:   close
Status: done  (tests <passed>/<total>)
Next:   /spec <NN+1> <slug> "<description>"
```
