---
description: Stage 1 — draft, revise, or approve a feature spec in .claude/specs/
argument-hint: <NN> <slug> "<what you want>"  |  <NN> revise "<feedback>"  |  <NN> approve
---

# /spec — Stage 1: Specification

Arguments: `$ARGUMENTS`

Read `CLAUDE.md` first. The spec says **what** and **why**, never **how**.
Leave file names, class names and code out of the spec.

## Modes

Work out the mode from the arguments:

### `draft` — `<NN> <slug> "<description>"`
1. Check that `.claude/specs/` has no file starting with `NN-`. If one exists,
   stop and suggest `revise`.
2. Check that the previous step (`NN-1`) is `status: done`, unless NN is `01`.
   If it isn't, warn the user and stop.
3. If the description is too thin to write clear acceptance criteria, ask up to
   3 short clarifying questions and wait for the answers. Never invent product
   decisions.
4. Write `.claude/specs/NN-slug.md` from the template below with `status: draft`.

### `revise` — `<NN> revise "<feedback>"`
1. Find `.claude/specs/NN-*.md`. If its status is not `draft`, stop: an approved
   spec only changes when the user explicitly asks to reopen it. In that case,
   set it back to `draft` and say so.
2. Apply the feedback. Renumber acceptance criteria only when necessary.

### `approve` — `<NN> approve`
Only the user runs this mode. Never run it on your own initiative.
1. Find the spec. Check that `status: draft`, that every AC is testable, and
   that "Open questions" is empty or each one has an answer. If not, stop and
   list what's blocking.
2. Set `status: approved` and `approved: <today's date>`.

## Spec template

```markdown
---
step: NN
slug: <slug>
status: draft
created: <YYYY-MM-DD>
approved:
---

# NN — <Title>

## Goal
One or two sentences: the outcome for the user.

## Context / why now
What exists already, and why this step comes next.

## User stories
- As a <role>, I want <capability>, so that <benefit>.

## Acceptance criteria
Each one must be observable and testable.
- **AC-1** Given …, when …, then …
- **AC-2** …
- Include access rules: who can and who cannot (non-members, anonymous users).

## Out of scope
What this step deliberately leaves out.

## Open questions
- (Leave empty when none. Note any need for a new dependency here.)
```

## Final report

End with exactly this and nothing after it:

```
File:   .claude/specs/NN-slug.md
Mode:   draft | revise | approve
Status: <new status>  (<one-line note, e.g. "awaiting your approval">)
Next:   <exact command>
```

The `Next:` line should be: after draft or revise, `/spec NN approve` (or
`/spec NN revise "…"`); after approve, `/plan NN`.
