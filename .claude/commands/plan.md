---
description: Stage 2 — draft, revise, or approve the implementation plan for an approved spec
argument-hint: <NN>  |  <NN> revise "<feedback>"  |  <NN> approve
---

# /plan — Stage 2: Implementation plan

Arguments: `$ARGUMENTS`

Read `CLAUDE.md` and the spec `.claude/specs/NN-*.md` first. The plan says
**how**. It must follow the stack constraints and conventions in CLAUDE.md, and
must not re-argue them.

## Modes

### `draft` — `<NN>`
1. The spec must be `status: approved`. If it isn't, stop and point to
   `/spec NN approve`.
2. No plan may exist yet for NN. If one does, suggest `revise`.
3. Read the existing code relevant to the step (models, urls, templates,
   settings) so the plan fits what is actually there.
4. Write `.claude/plans/NN-slug.md` (same slug as the spec) from the template
   below with `status: draft`.
5. Any new dependency, or any change that breaks a CLAUDE.md constraint, goes
   under "Decisions needing approval". Never put it straight into the steps.

### `revise` — `<NN> revise "<feedback>"`
Only allowed while `status: draft`. Apply the feedback and keep the AC mapping
complete.

### `approve` — `<NN> approve`
Only the user runs this mode. Never run it on your own initiative.
1. Check that `status: draft`, that every spec AC appears in the test plan, and
   that every item under "Decisions needing approval" has an answer.
2. Set `status: approved` and `approved: <today's date>`.

## Plan template

```markdown
---
step: NN
slug: <slug>
spec: .claude/specs/NN-slug.md
status: draft
created: <YYYY-MM-DD>
approved:
---

# Plan NN — <Title>

## Approach
A short summary of the design, and why it is this design rather than the
obvious alternative.

## Data model & migrations
Models and fields added or changed, plus the migrations expected.

## URLs, views, templates
| URL name | View | Template | Access rule |

## Implementation steps
- [ ] 1. …
- [ ] 2. …

## Test plan
| AC | Test module | What it asserts |
Every spec AC has a row, including the access-denied cases.

## Risks
Security, data and migration risks, plus what is done about each one.

## Decisions needing approval
- (none)

## Files changed
_(filled in by /build)_

## Test results
_(filled in by /build)_

## Review log
_(filled in by /review)_
```

## Final report

End with exactly this and nothing after it:

```
File:   .claude/plans/NN-slug.md
Mode:   draft | revise | approve
Status: <new status>  (<one-line note>)
Next:   <exact command>
```

The `Next:` line should be: after draft or revise, `/plan NN approve` (or
`/plan NN revise "…"`); after approve, `/build NN`.
