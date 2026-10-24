---
step: 05
slug: tasks
status: done
created: 2026-10-06
approved: 2026-10-06
---

# 05 — Tasks

## Goal
Workspace members can add tasks to a project they can access, see the
project's tasks, and open each task's page. A task is only ever visible
through the project and workspace it belongs to.

## Context / why now
Step 02 gave workspaces members-only access. Step 04 added projects nested
inside workspaces, with one rule: resolve the workspace for a member first,
then look children up only inside it. Tasks are the next layer down and
the unit of work the product exists for. This step adds them with the
smallest useful set of details (a title and a description) and extends the
same nesting one more level.

Step 04's review deferred several clean-up items to this step (listed in
CLAUDE.md, "Known limitations"). They are handled here too; see OQ-1.

## User stories
- As a workspace member, I want to add a task to a project, so that the
  team can record a piece of work that needs doing.
- As a workspace member, I want to see all of a project's tasks on the
  project page, so that I know what work the project contains.
- As a workspace member, I want to open a task and read its title and
  description, so that I understand what needs doing.
- As anyone outside a workspace, I want its tasks to stay invisible to me,
  so that each team's work stays private.

## Acceptance criteria

### Creating a task
- **AC-1** Given a member of a workspace (the owner included), when they
  choose the create-task action on one of its projects' pages, then they see
  a form asking for a task title and an optional description. The form
  makes clear which project, and which workspace, the task will be created
  in.
- **AC-2** Given a valid title, with or without a description, when the
  member submits the form, then:
  - a task is created in that project, and **only** that project;
  - the member lands on the new task's page;
  - they see a confirmation message.
- **AC-3** Given a title that is empty or only spaces, when the member
  submits, then no task is created and the form shows an error on the title
  field. Spaces at the start and end of the title are removed before it is
  saved (see OQ-2).
- **AC-4** Given a title or description longer than its maximum length (see
  OQ-2), when the member submits, then no task is created, and the form shows
  an error on that field stating the limit. What the member typed stays in
  the form.
- **AC-5** Given an empty description, or one of only spaces, when the member
  submits an otherwise valid form, then the task is created with no
  description.
- **AC-6** Given a project that already has a task with a certain title,
  when a member creates another task with the same title in that project,
  then a second, separate task is created (see OQ-3).

### Seeing a project's tasks
- **AC-7** Given a workspace member, when they open a project page that has
  tasks, then it has a tasks section showing:
  - the number of tasks;
  - every task in that project, each linking to its page, in a **stable
    creation order, oldest first**. A task never changes position when other
    tasks are added; new tasks always appear after existing ones. No creation
    date or time is shown (see OQ-4);
  - a create-task action (see OQ-5).

  The project's existing name, description and back link stay as they are.
- **AC-8** Given a project with no tasks, when a member opens its page, then
  the tasks section shows a clear empty-state message, with a create-task
  action inside the empty state itself (see OQ-5).
- **AC-9** Given a project page, then it never lists tasks that belong to
  another project, including other projects in the same workspace.

### Viewing a task
- **AC-10** Given a workspace member, when they open a task, then the task
  page shows:
  - the task's title;
  - its description, keeping the line breaks the author typed, or a short
    "No description" note when there is none;
  - which project, and which workspace, it belongs to, with a way back to
    the project's page (see OQ-6).
- **AC-11** Given a task title or description that contains text that looks
  like HTML or script, when it is shown anywhere (the project page, the task
  page, the confirmation message or the page title), then it is displayed as
  plain text and never run or rendered as markup.

### Access rules
- **AC-12** Given a signed-in user who is **not** a member of a workspace,
  when they try to open:
  - the create-task page of one of its projects;
  - any of its task pages;
  - or submit a create-task request there,

  then they get a "not found" response, the same one they would get if the
  workspace, project or task didn't exist. Nothing reveals a task's title,
  description or existence, and a create request creates nothing.
- **AC-13** Wrong-parent requests are "not found" in two ways:
  - **Viewing an existing task.** Given a task that belongs to one project in
    one workspace, when it is requested as though it belonged to a different
    workspace (even one the user is a member of) or a different project (even
    another project in the same workspace), then the response is "not found".
    An existing task can only be reached through the project and workspace it
    really belongs to.
  - **Creating a task.** When a create-task page is opened, or a create-task
    form is submitted, under a workspace and project combination that is
    itself invalid or inaccessible, then the response is "not found" and
    nothing is created. That covers:
    - a project that isn't in that workspace;
    - a workspace the user isn't a member of;
    - a missing workspace or project.

    A brand-new task has no earlier parent. So when an authorised member
    submits the form under a valid project they can access, the task is
    created in **that** project, as in AC-2 and AC-19.
- **AC-14** Given a workspace, project or task ID that doesn't exist, when a
  signed-in user requests it, then they get the same "not found" response as
  in AC-12.
- **AC-15** Given an anonymous visitor, when they open a create-task page or
  a task page, then they are redirected to login, the redirect remembers the
  page they asked for, and after logging in they land on that page. The
  usual access rules still apply there: a non-member still gets "not found".
- **AC-16** Given an anonymous visitor, when they submit a create-task form,
  then nothing is created and they are sent to login. After logging in, the
  submission is **not** replayed, and they land on the dashboard.
- **AC-17** Given a create-task form submitted from outside the site (without
  the site's anti-forgery token), then it is rejected and nothing is created.
- **AC-18** Given a request to create a task made as a simple link visit or
  page load instead of submitting the form, then nothing is created.

### Data integrity
- **AC-19** Given any task, then it belongs to exactly one project, and so to
  that project's workspace, and that never changes in this step. A new task
  is always created in the project identified by the authorised page the
  member used, its workspace and project. Any project or workspace IDs posted
  with the form are ignored and can't place the task anywhere else.

### Design and behaviour preserved
- **AC-20** Given the new and changed pages (the project page's tasks
  section, the create-task page and the task page), then they follow the
  step 03 design system and meet its accessibility rules:
  - semantic colour tokens only;
  - one main heading and a correct heading order;
  - labelled fields with linked errors;
  - visible focus;
  - targets of at least 24px;
  - no sideways scrolling at 320px, with long titles and descriptions
    wrapping;
  - reduced motion respected;
  - no new scripts, fonts or icon packages.

  The ui-ux-pro-max workflow is applied and recorded, as CLAUDE.md requires.
- **AC-21** Given the finished step, then all existing behaviour from steps 01
  to 04 is unchanged and every existing test still passes, except for the
  two deliberate wording changes in AC-22.

### Carried-over clean-up (see OQ-1)
- **AC-22** Given the project page and the workspace page, then:
  - the project page's back link reads "Back to <workspace name>" instead of
    just the workspace name (step 04 Q-40);
  - the create-project action uses one label wherever it appears, on the
    workspace page header, its empty state and the create page (step 04
    Q-41).
- **AC-23** Given the rest of the step 04 deferred items (Q-35, Q-34, Q-42,
  Q-43, Q-44, Q-46, Q-47, Q-48), then each is resolved with **no change to
  any user-visible behaviour**. The workspace and project access rules from
  steps 02 and 04 behave exactly as before.

## Out of scope
- Assigning tasks to users
- Task status, priority, due dates, labels or progress
- Subtasks or task dependencies
- Editing, deleting or archiving tasks
- Comments, attachments, notifications, activity history and time tracking
- Search, filtering and user-controlled sorting of tasks
- Showing task counts or tasks anywhere other than the project page (for
  example on the workspace page or the dashboard) (see OQ-7)
- Showing who created a task, or when it was created (see OQ-4 and OQ-6)
- Rich text, Markdown or links in descriptions. They are plain text only.
- Project editing, and project-specific roles or membership
- Changing workspace membership or ownership
- New dependencies or JavaScript

## Decisions
These were open questions. The user accepted the proposed answers on
2026-10-06, and clarified OQ-4.

- **OQ-1 Include step 04's deferred clean-up?** The user deferred these items
  "to step 05" when closing step 04. They are:
  - Q-35: one shared workspace-lookup mechanism instead of two, which tasks
    would otherwise copy a third time;
  - Q-40 and Q-41: the two wording changes;
  - code comments, an admin stub and test-quality items.
  - Yes. Include them, with only the two wording items visible to
    users (AC-22). Everything else must leave behaviour unchanged (AC-23).
    Q-35 especially should land before tasks reuse the access pattern.
    → AC-21, AC-22, AC-23
- **OQ-2 Field limits.**
  - the title is required, at most 200 characters, with leading and trailing
    spaces removed. Task titles tend to be short sentences, so the limit is
    longer than project names' 100;
  - the description is optional, plain text, at most 2,000 characters, with
    leading and trailing spaces removed, the same as projects. → AC-3, AC-4,
    AC-5
- **OQ-3 Title uniqueness.** **No uniqueness rule.** Tasks
  often repeat ("Review", "Follow up"), unlike project names, which identify
  a project within a workspace. → AC-6
- **OQ-4 Task list order.** Sorting controls are out of scope, so the list
  needs one fixed order. **Decision:** a **stable creation order, oldest
  first**, so new tasks appear at the bottom like a to-do list.
  - The order never shifts as tasks are added, and it is the same every time
    the page loads.
  - **No creation timestamp or date is shown to users.** The step may keep
    whatever internal record it needs to make the order reliable, but
    nothing about it appears on any page.
  - The rejected alternative was alphabetical by title, like projects.
  → AC-7
- **OQ-5 Where the create action lives, and its label.** This follows the
  pattern the user accepted in step 04 (Q-33).
  - when the project has tasks, a "New task" action appears in the tasks
    section header;
  - when it has none, the empty state carries its own "New task" action, so
    only one create action shows at a time;
  - one label, "New task", is used for the action everywhere, as AC-22 asks
    for projects;
  - Cancel on the create page returns to the project page. → AC-7, AC-8
- **OQ-6 Task page details.**
  - the page shows the title, the description, and the project and
    workspace it belongs to;
  - the back link goes to the project page ("Back to <project name>"), and
    the workspace name appears as context;
  - no creator or creation date is shown, as for projects. → AC-10
- **OQ-7 Task counts elsewhere.** No. The workspace page's
  project list and the dashboard don't change in this step, apart from
  AC-22's wording. → Out of scope

## Open questions
- (none)

No new dependencies are needed. Everything above can be built with what
CLAUDE.md already allows.
