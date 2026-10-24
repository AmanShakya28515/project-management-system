---
step: 06
slug: task-assignment
status: done
created: 2026-10-07
approved: 2026-10-07
---

# 06 — Task assignment

## Goal
A task can be assigned to one member of its workspace, reassigned, or left
unassigned, so the team can see who is responsible for it.

## Context / why now
Tasks exist (step 05) and can be reached only through their workspace and
project. "Assign tasks" is the next core product capability, and it needs no
new access model: anyone who can see a task may assign it. The access, CSRF,
no-replay and design-system rules in CLAUDE.md apply unchanged.

## Acceptance criteria

### Showing the assignee
- **AC-1** Given a task page, then it clearly shows the current assignee by
  username, or "Unassigned" when there is none. A new task starts unassigned.

### Assigning
- **AC-2** Given a member who can access a task, when they open its page, then
  they see a control to choose the assignee. It offers "Unassigned" plus
  every **active** member of the task's workspace, the owner included, and
  nobody else (see OQ-1).
- **AC-3** Given a chosen member, when the form is submitted, then the task is
  assigned to them, the member returns to the task page, and a confirmation
  message names the new assignee.
- **AC-4** Given an assigned task, when a different member is chosen and
  submitted, then the assignee is replaced. A task never has more than one
  assignee.
- **AC-5** Given an assigned task, when "Unassigned" is chosen and submitted,
  then the task has no assignee, and a confirmation message says it is now
  unassigned.
- **AC-6** Given a submission that names the task's current assignee, or
  "Unassigned" for an unassigned task, then nothing changes, and a message
  confirms the current state (see OQ-3).

### Rejecting invalid assignees
- **AC-7** Given a submission naming someone who isn't a member of the
  task's workspace (for example by altering the submitted data), whether an
  existing user from another workspace, an inactive user or a user ID that
  doesn't exist, then the assignment is rejected. The assignee is unchanged,
  and the page shows a clear error next to the assignee control.
- **AC-8** Given any task, then its assignee is always either nobody or an
  active member of the task's workspace at the moment of assignment.

### Access rules (existing patterns, applied to assignment)
- **AC-9** Given a non-member, or a URL that puts the task under the wrong
  workspace or project, or any missing ID, when an assignment is submitted,
  then the response is the same "not found" as for viewing the task, and
  nothing changes.
- **AC-10** Given an anonymous visitor who submits an assignment, then nothing
  changes and they are sent to login without the submission being replayed
  (the existing no-replay rule).
- **AC-11** Given an assignment submitted without the site's anti-forgery
  token, or as a link visit or page load instead of a form submission, then
  nothing changes.

### Preserved behaviour and design
- **AC-12** Given the changed task page, then the assignee display and control
  follow the design system and accessibility rules in CLAUDE.md: a labelled
  control, errors linked to it, a visible focus state, targets of at least
  24px, and wrapping at 320px.
- **AC-13** Given the finished step, then all existing behaviour from steps
  01–05 is unchanged and every existing test passes.

## Out of scope
- Multiple assignees, teams or groups
- Task status, priority, due dates, labels, comments, notifications and
  activity history
- Editing anything about a task other than its assignee
- Search and filtering, for example "my tasks"
- Showing assignees anywhere other than the task page (see OQ-2)
- Choosing an assignee while creating a task (see OQ-4)
- What happens to existing assignments if a member is later deactivated or
  removed (no such feature exists; see CLAUDE.md S-4)

## Decisions
The user accepted the proposed answers on 2026-10-07.

- **OQ-1 How the assignee is chosen.** A single drop-down list
  with "Unassigned" first, then the workspace's active members in the
  member-list order (owner first, then alphabetical). No typed usernames, so
  there is nothing to mistype. → AC-2
- **OQ-2 Show the assignee on the project page's task rows too?**
  No, not in this step. Keep the change to the task page. A list
  view can show it later, together with status. → Out of scope
- **OQ-3 Submitting the same assignee again.** Nothing changes,
  and an informational message states the current assignee, or
  "Unassigned". → AC-6
- **OQ-4 Assign while creating a task?** No. Tasks are created
  unassigned and assigned from the task page, which keeps one assignment
  path to secure and test. → AC-1, Out of scope

## Open questions
- (none)
