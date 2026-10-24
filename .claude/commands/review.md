---
description: Stage 4 — one concise review of a built step; log findings by severity
argument-hint: <NN>  |  <NN> recheck
---

# /review — Stage 4: Review

Arguments: `$ARGUMENTS`

Read `CLAUDE.md`, the approved spec and the plan for NN first.

## Modes

- **`<NN>`:** the plan must be `status: built`. Do one concise review.
- **`<NN> recheck`:** the plan must be `status: built` and already have a
  review log entry. Re-review **only** the fixed findings and the files they
  changed. Use it only after a High or important Medium fix, never for Low
  findings alone.

## Flow

1. **Scope:** the plan's "Files changed" list, plus `git diff` if this is a
   git repo.
2. **Review against the approved spec, the plan and CLAUDE.md**, mainly for:
   1. **Correctness:** the ACs are really implemented; no obvious regressions
      or wrong edge cases.
   2. **Security and access control, where relevant:** queryset and object
      scoping, authentication and authorization, CSRF and state-changing
      methods, escaping and injection, secrets and sensitive data.
   3. **Data integrity:** constraints, relationships, transactional
      behaviour, and race conditions where relevant.
   4. **Accessibility:** for changed UI.
   5. **Architecture and maintainability:** only issues that could
      materially affect future work.
3. **Rank findings High / Medium / Low.** Each has a `file:line`, the
   evidence, and a suggested fix in plain language.
   - **High:** normally blocking.
   - **Medium:** fix when it materially affects correctness, security,
     access control, data integrity, accessibility, architecture or future
     maintainability.
   - **Low:** accepted by default, unless it affects security, access
     control, data integrity, accessibility or future architecture.

   Don't produce long lists of cosmetic, documentation or test-style Low
   findings.
4. **Log the review** concisely as a dated entry under "Review log" in the
   plan, with IDs continuing the existing numbering (`S-n`, `Q-n`) and the
   label `open`.
5. **Don't fix anything.** The user decides which findings to fix (via
   `/build NN retest`) and which to accept or defer.
6. **Set `status: reviewed`** when no High finding is open. Otherwise leave
   it at `built`. Never recommend a recheck only for Low findings.

## Optional specialist reviewers

- **`security-reviewer`:** use it only when the step materially involves
  authentication, authorization or access control, permissions, secrets,
  uploads, payments, external APIs, sensitive data or production security
  settings.
- **`quality-reviewer`:** use it only for substantial architecture changes,
  major refactors or risky cross-app structural changes.

Never invoke either automatically for ordinary features. If you use one,
summarise only its actionable findings; don't duplicate its whole analysis.

## Final report

Print the ranked findings table first (or "No findings"), then end with
exactly this and nothing after it:

```
File:   .claude/plans/NN-slug.md
Mode:   review | recheck
Status: reviewed | built (<n> High open)
Found:  High <n> · Medium <n> · Low <n>
Next:   <exact command>
```

The `Next:` line should be: if reviewed, `/done NN` (or `/build NN retest`
when you recommend fixing an important Medium); if High findings are open,
`/build NN retest` once the user has said which findings to fix.
