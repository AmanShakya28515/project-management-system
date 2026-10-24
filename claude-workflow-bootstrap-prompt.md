You are setting up a spec-driven, approval-gated Claude Code workflow in this
repository. Create every file listed below with the contents given, adapting
only the parts marked {{LIKE_THIS}} using the PROJECT FACTS section. Do not
write any application code, do not install anything, and do not run git
commands. If a PROJECT FACT is missing or unclear, ask me (at most 5 short
questions) before writing files. When finished, print the file tree you
created and a 3-line "how to start" note.

=====================================================================
PROJECT FACTS  (I fill these in; ask me about any left blank)
=====================================================================
- Project name:            {{PROJECT_NAME}}
- One-paragraph purpose:   {{WHAT_IT_DOES}}
- Goals, in priority order: {{GOAL_1}}; {{GOAL_2}}
- OS / shell:              {{e.g. Windows + PowerShell & Git Bash / macOS zsh}}
- Language + version:      {{e.g. Python 3.12}}
- Framework + version:     {{e.g. Django 5.2 LTS}}
- Database (now / later):  {{e.g. SQLite now, PostgreSQL later}}
- Frontend approach:       {{e.g. server templates + Tailwind Play CDN}}
- Test framework:          {{e.g. django.test / pytest / vitest}}
- Dependency file:         {{e.g. requirements.txt / package.json}}
- Interpreter / runner:    {{e.g. .venv/Scripts/python.exe — never bare python}}
- Commands:
  - dev server:       {{CMD_RUN}}
  - focused tests:    {{CMD_TEST_FOCUSED}}  (e.g. manage.py test <app>.tests.<module>)
  - full test suite:  {{CMD_TEST_ALL}}
  - migration drift:  {{CMD_DRIFT}}   (or "n/a")
  - static/system check: {{CMD_CHECK}}  (or "n/a")
  - apply migrations: {{CMD_MIGRATE}}  (or "n/a")
  - install deps:     {{CMD_INSTALL}}
- Dependencies NOT to add without asking: {{DENY_LIST}}
- UI skill/design system to use for frontend work (optional): {{UI_SKILL_OR_NONE}}
- Is this a git repo yet?  {{yes/no}}

=====================================================================
FILES TO CREATE
=====================================================================

.
├── CLAUDE.md
└── .claude/
    ├── commands/   spec.md  plan.md  build.md  review.md  done.md
    ├── agents/     test-author.md  test-runner.md  security-reviewer.md  quality-reviewer.md
    ├── specs/      (empty; add .gitkeep)
    └── plans/      (empty; add .gitkeep)

---------------------------------------------------------------------
FILE: CLAUDE.md
---------------------------------------------------------------------
# CLAUDE.md

Guidance for Claude Code in this repository. This file records **why**
decisions were made, not just what they are. If a rule here looks wrong, raise
it with the user. Do not quietly work around it, and do not reopen a settled
choice in a spec or plan unless the user asks.

---

## What this project is

{{WHAT_IT_DOES}}

Goals, in this order:
1. {{GOAL_1}}
2. {{GOAL_2}}

**Why the order matters:** {{one sentence, e.g. "later phases need a real,
well-tested app, so the app stays simple and conventional now"}}.

---

## Common commands

Always use the project interpreter/runner explicitly ({{INTERPRETER}}); a
global install can silently differ from the project's.

| Purpose | Command |
|---|---|
| Dev server | `{{CMD_RUN}}` |
| Focused tests | `{{CMD_TEST_FOCUSED}}` |
| Full test suite | `{{CMD_TEST_ALL}}` |
| Migration drift | `{{CMD_DRIFT}}` |
| System checks | `{{CMD_CHECK}}` |
| Apply migrations | `{{CMD_MIGRATE}}` |
| Install deps | `{{CMD_INSTALL}}` |

**Standard verification order:** focused tests, then migration drift, then
checks, then the full suite. Cheapest, most specific feedback first; drift
comes before the full suite because a missing migration makes test failures
misleading. (Skip any step marked n/a.)

---

## Feature workflow

Every change goes through five stages: **SPEC → PLAN → BUILD & VERIFY →
REVIEW → DONE**. A **gate** is an explicit human approval. Claude never
approves its own spec or plan, and never moves past a gate on its own.

| # | Stage | Command | Output | Gate to leave the stage |
|---|---|---|---|---|
| 1 | Spec | `/spec` | `.claude/specs/NN-slug.md` | User runs `/spec NN approve` |
| 2 | Plan | `/plan` | `.claude/plans/NN-slug.md` | User runs `/plan NN approve` |
| 3 | Build & Verify | `/build` | Code, migrations, tests, and verification in the standard order | Everything green, or the user accepts the failures |
| 4 | Review | `/review` | One concise review (correctness, security/access control, data integrity, important maintainability), logged in the plan | User decides which findings to fix |
| 5 | Done | `/done` | Spec and plan marked done; CLAUDE.md architecture and history updated | — |

**Status lifecycle** (front-matter `status:`):
- Spec: `draft` → `approved` → `done`
- Plan: `draft` → `approved` → `built` → `reviewed` → `done`

Each command checks the status it needs first and refuses with a clear
message if it is wrong.

**Numbering:** two-digit, sequential (`01`, `02`, …). Spec and plan share the
same `NN-slug` filename.

**Why this workflow:**
- Specs hold *what* and *why*; plans hold *how*. Keeping them apart stops
  implementation details being debated before the goal is agreed.
- Acceptance criteria are numbered (`AC-1`, …) so tests, plan steps and
  review findings can point to them. "Done" becomes checkable.
- Tests are derived from the **spec**, not the code; tests written from code
  repeat the code's bugs.
- Small numbered steps map cleanly onto future CI pipeline runs.

**Finding "the diff":** {{if not git: "the project is not a git repository
yet. The plan's 'Files changed' section, kept up to date by /build, is the
official list of what a step touched."}} {{if git: "use git diff / git status
and cross-check the plan's 'Files changed' list."}}

### Token-efficient execution
Optimise for correctness, learning value and progress per token.
- **Specs stay concise:** goal and context; user-visible behaviour; numbered
  acceptance criteria; out of scope; only open questions that matter. Point
  to CLAUDE.md instead of restating it.
- **Plans stay concise:** key technical decisions; real files affected;
  migrations/data changes; meaningful risks; test and verification approach.
  Don't re-explain settled architecture.
- Reuse established patterns rather than rediscovering them.
- Don't paste large parts of CLAUDE.md, a spec or a plan into agent prompts.
- Prefer one implementation-and-verification pass and one concise review.
- No review → fix → recheck cycles for minor clean-up.
- Token efficiency means less repetition, not less correctness. Never change
  architecture just to save tokens.

### Sub-agents
Optional tools, not workflow stages. Use one only when an independent
context really improves correctness.
- **`test-author`:** complex or security-sensitive ACs where independent
  test design adds value.
- **`test-runner`:** only when independent verification matters.
- **`security-reviewer`:** changes touching authentication, authorization,
  permissions, secrets, uploads, payments, external APIs, sensitive data or
  production security settings.
- **`quality-reviewer`:** substantial architecture changes, major refactors,
  technically risky work.

### Review findings
- **High:** normally fixed before the step closes.
- **Medium:** fixed when it materially affects correctness, security, access
  control, data integrity, accessibility, architecture or maintainability.
- **Low:** accepted by default unless it affects one of the above.

Never reopen a build or start another review cycle only for cosmetic
clean-up, wording, duplicated test data, minor comments or optional
refactors. Low findings that may matter later go into Known limitations.

---

## Stack constraints

### Use:
- **{{LANGUAGE_VERSION}}.** {{why}}
- **{{FRAMEWORK_VERSION}}.** {{why; how it is pinned}}
- **{{DATABASE}}.** {{why; e.g. "write only ORM code that works on any
  database — no raw SQL, nothing backend-specific"}}
- **{{FRONTEND}}.** {{why; known trade-offs}}
- **{{TEST_FRAMEWORK}}.** {{why}}
- **{{DEPENDENCY_FILE}}** for dependencies.

### Do NOT add without being asked:
{{DENY_LIST as bullets}}

**Why so strict:** every dependency should be a deliberate, approved step
with its own spec. If a feature seems to need one, say so in the spec's
"Open questions" and let the user decide.

---

## Architecture

*`/done` adds to this as each step lands. Record only what was actually
built, plus the reasoning behind any structural choice.*

(empty)

### Known limitations (deliberately deferred)
(none yet)

### Steps landed
(none yet)

---

## Testing

- `/build` writes tests directly; use `test-author` only when independent
  test design genuinely helps.
- **Tests come from the approved spec**, not the implementation. Every
  important AC gets coverage, and the test names its AC (`AC-3` in a comment
  or docstring).
- Test behaviour; avoid brittle markup or source-inspection tests.
- Tests live in {{TEST_LOCATION, e.g. <app>/tests/ as a package}}.
- **Test permissions, not just the happy path:** for every protected
  resource, test that an unauthorised user is denied and an anonymous user is
  redirected/rejected.
- Tests must not touch the network or depend on test order.
- When a test exposes an application bug, fix the application within the
  plan's scope. Never weaken the test to make the suite pass.

---

## Frontend and UI work
{{If UI_SKILL_OR_NONE is set: "Load the {{UI_SKILL}} skill before writing
any markup. Read the persisted design system first; reuse existing
components; run searches only for genuinely new patterns. The skill works
inside the stack, never around it." Otherwise: "Keep one visual language;
accessibility (labels, visible focus, contrast, heading order, inline
errors) is part of done."}}

---

## Conventions

- Authorization is enforced in the query (scope lookups to what the user may
  access), not by fetching then checking — so a forgotten check fails closed.
- Every non-public endpoint requires login. State changes use POST (or the
  correct non-GET method) with CSRF protection; never GET.
- Validate all input through the framework's forms/validators; never write
  raw request data straight into a model.
- Business rules live on models/services, not in templates.
- Commit every model change with its migration; never edit an applied
  migration.
- Keep each change within its plan. If something outside the plan needs to
  change, stop and say so.
- Never commit secrets; read them from the environment, with a local
  fallback clearly labelled insecure.

---------------------------------------------------------------------
FILE: .claude/commands/spec.md
---------------------------------------------------------------------
---
description: Stage 1 — draft, revise, or approve a feature spec in .claude/specs/
argument-hint: <NN> <slug> "<what you want>"  |  <NN> revise "<feedback>"  |  <NN> approve
---

# /spec — Stage 1: Specification

Arguments: `$ARGUMENTS`

Read `CLAUDE.md` first. The spec says **what** and **why**, never **how**.
Leave file names, class names and code out of the spec.

## Modes

### `draft` — `<NN> <slug> "<description>"`
1. Check that `.claude/specs/` has no file starting with `NN-`. If one
   exists, stop and suggest `revise`.
2. Check that the previous step (`NN-1`) is `status: done`, unless NN is
   `01`. If it isn't, warn the user and stop.
3. If the description is too thin to write clear acceptance criteria, ask up
   to 3 short clarifying questions and wait. Never invent product decisions.
4. Write `.claude/specs/NN-slug.md` from the template with `status: draft`.

### `revise` — `<NN> revise "<feedback>"`
1. Find `.claude/specs/NN-*.md`. If its status is not `draft`, stop: an
   approved spec only changes when the user explicitly asks to reopen it; in
   that case set it back to `draft` and say so.
2. Apply the feedback. Renumber ACs only when necessary.

### `approve` — `<NN> approve`
Only the user runs this mode. Never run it on your own initiative.
1. Check `status: draft`, every AC is testable, and "Open questions" is
   empty or answered. If not, stop and list what's blocking.
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
- Include access rules: who can and who cannot.

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
Status: <new status>  (<one-line note>)
Next:   <exact command>
```

After draft or revise: `/spec NN approve` (or `/spec NN revise "…"`); after
approve: `/plan NN`.

---------------------------------------------------------------------
FILE: .claude/commands/plan.md
---------------------------------------------------------------------
---
description: Stage 2 — draft, revise, or approve the implementation plan for an approved spec
argument-hint: <NN>  |  <NN> revise "<feedback>"  |  <NN> approve
---

# /plan — Stage 2: Implementation plan

Arguments: `$ARGUMENTS`

Read `CLAUDE.md` and `.claude/specs/NN-*.md` first. The plan says **how**.
It must follow CLAUDE.md's stack constraints and conventions and must not
re-argue them.

## Modes

### `draft` — `<NN>`
1. The spec must be `status: approved`; otherwise stop and point to
   `/spec NN approve`.
2. No plan may exist yet for NN; if one does, suggest `revise`.
3. Read the existing code relevant to the step so the plan fits what is
   actually there.
4. Write `.claude/plans/NN-slug.md` (same slug) with `status: draft`.
5. Any new dependency or CLAUDE.md-breaking change goes under "Decisions
   needing approval", never straight into the steps.

### `revise` — `<NN> revise "<feedback>"`
Only while `status: draft`. Apply the feedback; keep the AC mapping complete.

### `approve` — `<NN> approve`
Only the user runs this mode. Never run it on your own initiative.
1. Check `status: draft`, every spec AC appears in the test plan, and every
   "Decisions needing approval" item has an answer.
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
Short design summary, and why this rather than the obvious alternative.

## Data model & migrations
Models/fields added or changed; migrations expected.

## Routes, handlers, views
| Route name | Handler | Template/Output | Access rule |

## Implementation steps
- [ ] 1. …
- [ ] 2. …

## Test plan
| AC | Test module | What it asserts |
Every spec AC has a row, including access-denied cases.

## Risks
Security, data and migration risks, plus what is done about each.

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

After draft or revise: `/plan NN approve` (or `/plan NN revise "…"`); after
approve: `/build NN`.

---------------------------------------------------------------------
FILE: .claude/commands/build.md
---------------------------------------------------------------------
---
description: Stage 3 — Build & Verify an approved plan (implement, write tests, run verification)
argument-hint: <NN>  |  <NN> resume  |  <NN> retest
---

# /build — Stage 3: Build & Verify

Arguments: `$ARGUMENTS`

Read `CLAUDE.md`, the approved spec and the approved plan for NN first.

## Modes

- **`<NN>` (implement):** plan must be `status: approved`. Run the full flow.
- **`<NN> resume`:** plan is `approved` and some steps are ticked. Continue
  from the first unticked step.
- **`<NN> retest`:** plan is `built`, `approved` or `reviewed`, and named
  findings or failures need fixing. Fix only those, re-run verification for
  the changed area (and the full suite when appropriate), set the plan back
  to `built`.

If the status doesn't match the mode, stop and name the right command.

## Flow

1. **Implement only what the approved plan allows.** Work through
   "Implementation steps" in order and tick each (`- [x]`).
   - If the **technical** approach must change, stop and recommend
     `/plan NN revise "…"`.
   - If **product behaviour** would change, stop and recommend reopening the
     spec (`/spec NN revise "…"`).
2. **Migrations:** if models changed, create and apply them using the
   commands in CLAUDE.md → Common commands.
3. **Write or update tests yourself:** derived from the spec's ACs, not the
   implementation; each names its AC; behaviour-focused; never weaken an
   existing test unless the spec deliberately changes that behaviour (say so).
4. **Verify directly** in CLAUDE.md's standard order: focused tests →
   migration drift → checks → full suite.
5. **If a test exposes an app bug:** fix the app within the plan; don't
   weaken the test; if the fix goes beyond the plan, stop and report.
   Environment failures: stop and report.
6. **Manual/browser checks** the plan requires: if tools aren't available,
   stop once and give the user a concise checklist; resume when they report
   back. Keep user-reported results apart from measured ones.
7. **Record concisely in the plan:** "Files changed", important decisions
   and deviations, "Test results" (commands, pass/fail counts, unresolved).
8. **Set `status: built`** only when verification is green or the user has
   accepted the failures.

## Optional sub-agents

`test-author` / `test-runner` only when independent test design or
verification materially improves correctness (complex authorization, races,
security-sensitive rules). Never invoke them automatically.

## Token efficiency

Don't send large copies of CLAUDE.md/spec/plan to sub-agents. Keep reports
short when checks pass. Don't repeat passed checks unless affected code
changed.

## Final report

End with exactly this and nothing after it:

```
File:   .claude/plans/NN-slug.md
Mode:   implement | resume | retest
Status: built | approved (blocked: <reason>)
Tests:  <passed>/<total>; drift: clean|DRIFT; check: ok|issues
Next:   <exact command>
```

If built: `/review NN` (or `/done NN` after a retest needing no further
review); if blocked: the exact fix command.

---------------------------------------------------------------------
FILE: .claude/commands/review.md
---------------------------------------------------------------------
---
description: Stage 4 — one concise review of a built step; log findings by severity
argument-hint: <NN>  |  <NN> recheck
---

# /review — Stage 4: Review

Arguments: `$ARGUMENTS`

Read `CLAUDE.md`, the approved spec and the plan for NN first.

## Modes

- **`<NN>`:** plan must be `status: built`. One concise review.
- **`<NN> recheck`:** plan is `built` and already has a review log entry.
  Re-review **only** the fixed findings and their files. Only after a High or
  important Medium fix, never for Lows alone.

## Flow

1. **Scope:** the plan's "Files changed" list, plus `git diff` if git exists.
2. **Review against the spec, the plan and CLAUDE.md**, mainly for:
   1. Correctness — ACs really implemented; no regressions or wrong edges.
   2. Security and access control where relevant — scoping, authn/authz,
      CSRF and state-changing methods, escaping/injection, secrets.
   3. Data integrity — constraints, relationships, transactions, races.
   4. Accessibility — for changed UI.
   5. Architecture/maintainability — only issues that materially affect
      future work.
3. **Rank findings High / Medium / Low**, each with `file:line`, evidence and
   a plain-language fix. No long lists of cosmetic Lows.
4. **Log the review** as a dated entry under "Review log" in the plan, IDs
   continuing the existing numbering (`S-n` security, `Q-n` other), label
   `open`.
5. **Don't fix anything.** The user decides (via `/build NN retest`).
6. **Set `status: reviewed`** when no High finding is open; otherwise leave
   `built`.

## Optional specialist reviewers

`security-reviewer` only for auth/permissions/secrets/uploads/payments/
external APIs/sensitive data; `quality-reviewer` only for substantial
architecture changes or risky refactors. Summarise only their actionable
findings.

## Final report

Print the ranked findings table (or "No findings"), then end with exactly:

```
File:   .claude/plans/NN-slug.md
Mode:   review | recheck
Status: reviewed | built (<n> High open)
Found:  High <n> · Medium <n> · Low <n>
Next:   <exact command>
```

If reviewed: `/done NN` (or `/build NN retest` when recommending an
important Medium fix); if High open: `/build NN retest` once the user says
which to fix.

---------------------------------------------------------------------
FILE: .claude/commands/done.md
---------------------------------------------------------------------
---
description: Stage 5 — close a reviewed step, settle findings, and update CLAUDE.md
argument-hint: <NN>
---

# /done — Stage 5: Done

Arguments: `$ARGUMENTS`

## Flow

1. **Confirm before closing:** plan is `status: reviewed` and spec is
   `approved`; verification recorded green; no High finding unresolved; every
   important Medium fixed, accepted or deliberately deferred.
2. **Verify only if needed.** If no code changed since the last green full
   suite, don't re-run. Otherwise re-run focused tests + full suite in the
   standard order. If anything fails, stop and recommend `/build NN retest`.
3. **Settle open findings.** Ask the user once, listing them; label each:
   High must be resolved; Medium fixed/accepted/deferred; Low accepted by
   default.
4. **Update `CLAUDE.md` with lasting knowledge only:** structural decisions
   with reasons, important conventions, genuinely useful known limitations,
   and a "Steps landed" line `NN — <title>: <one-sentence summary>` with the
   correct test count. No cosmetic findings, no file lists.
5. **Set the spec and plan to `status: done`.**
6. If git exists, suggest a commit message (`NN: <title>`) but **don't
   commit** unless asked.

## Final report

End with exactly this and nothing after it:

```
File:   .claude/specs/NN-slug.md, .claude/plans/NN-slug.md, CLAUDE.md
Mode:   close
Status: done  (tests <passed>/<total>)
Next:   /spec <NN+1> <slug> "<description>"
```

---------------------------------------------------------------------
FILE: .claude/agents/test-author.md
---------------------------------------------------------------------
---
name: test-author
description: Writes tests derived from a spec's acceptance criteria. Edits TEST FILES ONLY; reports application defects instead of fixing them.
tools: Read, Grep, Glob, Edit, Write, Bash
---

You write tests for a {{FRAMEWORK_VERSION}} project using only
{{TEST_FRAMEWORK}}. You are given a spec, a plan and a list of changed
files. Read `CLAUDE.md` → Testing first.

## Hard rules
- Only create or edit files inside {{TEST_LOCATION}}. Never touch app code,
  migrations, templates, settings or dependencies.
- Tests come from the spec's ACs, not the implementation. Write down what
  each AC requires first; only then read code for names you need.
- If an AC can't be satisfied because the app is wrong, write the correct
  test, let it fail, and report the defect. Never weaken the test.
- Don't install anything.

## How to write them
- One module per concern; tag every test with its AC (`AC-2: …`).
- For each protected endpoint: anonymous → login/reject; unauthorised →
  denied (404/403 per spec); authorised → succeeds; POST-only rejects GET.
- Deterministic, independent tests; use named routes, never hard-coded paths.
- You may run the tests you wrote with `{{CMD_TEST_FOCUSED}}`.

## Output
1. Files written, each with the ACs it covers.
2. AC coverage table `AC | test(s)`; flag uncovered ACs and why.
3. Suspected app defects: `file:line`, expected (with AC), observed, failing
   test. Or "none".

---------------------------------------------------------------------
FILE: .claude/agents/test-runner.md
---------------------------------------------------------------------
---
name: test-runner
description: Runs verification in fixed order — focused tests, migration drift, checks, full suite — and classifies every failure. Modifies nothing.
tools: Read, Grep, Glob, Bash
---

You run verification for this project. Always use {{INTERPRETER}}.

## Hard rules
- Never edit, create or delete files, and never run commands that do (no
  migration creation except dry-run checks, no migrate, no installs).
- Run the steps in order; keep going after a failure unless the environment
  is broken — then stop and report.

## Order
1. Focused tests: `{{CMD_TEST_FOCUSED}}` with the modules given (skip if none)
2. Migration drift: `{{CMD_DRIFT}}`
3. Checks: `{{CMD_CHECK}}`
4. Full suite: `{{CMD_TEST_ALL}}`

## Classify every failure
- **app-defect** (app doesn't meet the cited AC; name suspected `file:line`)
- **test-defect** (wrong test or assumption contradicting the spec)
- **drift** (models changed without a migration)
- **environment** (missing package, wrong interpreter, path/OS issue)

## Output
```
Focused:  <pass>/<total> | skipped
Drift:    clean | DRIFT (<apps>)
Check:    ok | <n> issues
Full:     <pass>/<total>
```
Then: `Test / check | Class | Evidence | Suspected location`. Trim
tracebacks to the lines that matter.

---------------------------------------------------------------------
FILE: .claude/agents/security-reviewer.md
---------------------------------------------------------------------
---
name: security-reviewer
description: Reviews a step's changed files for practical security issues — authorization gaps, injection, secrets, unsafe defaults. Evidence-based, plain language. Read-only.
tools: Read, Grep, Glob, Bash
---

You are a security reviewer for {{PROJECT_NAME}} ({{FRAMEWORK_VERSION}}). You
get a spec, a plan and changed files. Read `CLAUDE.md`; its authorization
convention matters most.

## Hard rules
- Never edit, create or delete files. Bash only for read-only commands.
- Every finding needs evidence: `file:line`, the exact code, and a concrete
  scenario ("user B, not a member of X, requests … and …"). No code, no
  finding.
- Plain language; no generic lectures.

## Look for, in priority order
1. Authorization/ownership gaps: lookups by ID not scoped to the user;
   missing login protection; role checks only in templates/UI; forms letting
   users set ownership/parent fields; IDOR via hidden fields.
2. State-changing GET, missing CSRF, CSRF exemptions.
3. Injection: raw/string-built queries, unescaped user content, unvalidated
   redirects.
4. Secrets and unsafe defaults: hard-coded keys, debug on in prod, wildcard
   hosts, credentials in code, sensitive data in logs.
5. Mass assignment: forms/serializers exposing all or sensitive fields.

Accepted decisions listed in CLAUDE.md (e.g. {{ACCEPTED_TRADEOFFS}}) are not
findings.

## Output
`ID | Severity | file:line | Issue | Scenario | Suggested fix`.
High = another user's data readable/changeable or code execution. Medium =
exploitable under conditions. Low = hardening. If none: "No security
findings" plus what you checked.

---------------------------------------------------------------------
FILE: .claude/agents/quality-reviewer.md
---------------------------------------------------------------------
---
name: quality-reviewer
description: Reviews a step's changed files for clarity, maintainability, and adherence to CLAUDE.md conventions and the approved plan. Read-only.
tools: Read, Grep, Glob, Bash
---

You are a code-quality reviewer for {{PROJECT_NAME}}. `CLAUDE.md` is your
rulebook; its constraints are settled — report deviations, don't argue.

## Hard rules
- Never edit, create or delete files. Bash only for read-only commands.
- Every finding needs `file:line` and why it matters. Skip pure style
  preferences CLAUDE.md doesn't cover.

## Check
1. Plan adherence: built-but-unplanned, planned-but-unbuilt, disallowed
   dependencies.
2. Conventions from CLAUDE.md (scoped queries, validated input, logic out of
   templates, naming, test location).
3. Clarity: misleading names, multi-purpose functions, duplicated logic, dead
   code, comments contradicting code.
4. Maintainability: hard-coded config, backend-specific code that blocks a
   planned migration, hand-edited or out-of-sync migrations.
5. Templates/UI: repeated markup that should be shared; missing CSRF tokens
   (flag for security).

## Output
`ID | Severity | file:line | Issue | Why it matters | Suggested fix`.
High = breaks a CLAUDE.md constraint or the plan. Medium = real maintenance
pain. Low = polish. End with one sentence on overall quality.

=====================================================================
AFTER CREATING THE FILES
=====================================================================
1. Do not create any spec or plan yet.
2. Print the file tree.
3. Print this "how to start" note:
   - Start a feature:   /spec 01 <slug> "<what you want>"
   - Approve gates:     /spec 01 approve → /plan 01 → /plan 01 approve
   - Build to close:    /build 01 → /review 01 → /done 01
