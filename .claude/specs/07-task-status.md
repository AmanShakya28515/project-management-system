---
step: 07
slug: task-status
status: done
created: 2026-10-07
approved: 2026-10-07
---

# 07 — Task status

## Goal
Each task has a status (To do, In progress or Done) that any workspace member
can change, so the team can track progress from the project page.

## Context / why now
Tasks exist (step 05) and can be assigned (step 06). "Track progress" is the
next core capability. It needs no new access model: anyone who can see a task
may change its status. The access, CSRF, no-replay and design-system rules in
CLAUDE.md apply unchanged. Changing a status follows the same flow as
assignment (step 06).

## Acceptance criteria

### Showing the status
- **AC-1** Given a task page, then it clearly shows the task's current status.
  A new task starts as **To do** (see OQ-1).
- **AC-2** Given a project page with tasks, then each task row shows that
  task's status as **text**, not by colour alone. The rows keep their
  existing order, oldest first.

### Changing the status
- **AC-3** Given a member who can access a task, when they open its page, then
  they see a control offering exactly the three statuses, in this order: To
  do, In progress, Done. The current one is preselected.
- **AC-4** Given a different status, when the form is submitted, then the
  task's status changes, the member returns to the task page, and a
  confirmation message names the new status.
- **AC-5** Given the task's current status, when it is submitted again, then
  nothing changes and an informational message confirms the current status
  (see OQ-2).
- **AC-6** Given a submitted value that isn't one of the three statuses (for
  example from altered submitted data), then it is rejected with an error
  next to the control, and the status is unchanged.
- **AC-7** Given a status change, then only the status changes. The title,
  description, assignee and project stay as they were.

### Access rules (existing patterns, applied to status)
- **AC-8** Given a non-member, a URL that puts the task under the wrong
  workspace or project, or any missing ID, when a status change is submitted,
  then the response is the same "not found" as for viewing the task, and
  nothing changes.
- **AC-9** Given an anonymous visitor who submits a status change, then
  nothing changes and they are sent to login without the submission being
  replayed.
- **AC-10** Given a status change submitted without the anti-forgery token,
  or as a link visit or page load instead of a form submission, then nothing
  changes.

### Preserved behaviour and design
- **AC-11** Given the changed pages (the task page's status control and the
  project page's task rows), then they follow the design system and
  accessibility rules in CLAUDE.md:
  - a labelled control, with errors linked to it;
  - status shown as text (a badge may add colour, but never colour alone);
  - a visible focus state;
  - interactive controls follow the existing 44px target rule from      CLAUDE.md;
  - wrapping at 320px.
- **AC-12** Given the finished step, then all existing behaviour from steps
  01–06 is unchanged and every existing test passes, except where AC-2
  deliberately adds the status to the task rows.

## Out of scope
- Custom or extra statuses, workflows or transition rules (any status can
  change to any other)
- Filtering, sorting or grouping tasks by status, and progress counts or
  charts
- Showing status anywhere other than the task page and the project page's
  task rows (for example the workspace page or the dashboard)
- Status history, timestamps, "completed by" or notifications
- Setting a status while creating a task
- Priority, due dates, labels, comments and editing other task fields

## Decisions
The user accepted the proposed answers on 2026-10-07.

- **OQ-1 The status of existing and new tasks.** Every task,
  including all tasks that already exist, starts as **To do**. → AC-1
- **OQ-2 Submitting the current status again.** Nothing changes,
  and an informational message confirms the current status, the same as
  step 06's assignment behaviour. → AC-5
- **OQ-3 How the status is changed.** A drop-down with the three
  statuses and a "Save status" button, in its own card on the task page next
  to the Assignee card. This mirrors the assignment control, so users learn
  one pattern. → AC-3, AC-11

## Open questions
- (none)
