---
step: 04
slug: projects
status: done
created: 2026-10-06
approved: 2026-10-06
---

# 04 — Projects

## Goal
Workspace members can create projects inside their workspace, see the
workspace's projects, and open each project's page. Nobody outside the
workspace can see that its projects exist.

## Context / why now
Step 02 delivered workspaces with members-only access. A non-member gets the
same "not found" whether a workspace is real or not. Step 03 gave every page
one design system. Projects are the next layer of the product. They are what
tasks will belong to later, and they must sit inside a workspace's access
boundary from the start. This step adds them with the smallest useful set of
details (name and description) and reuses step 02's access pattern rather than
inventing a new one.

## User stories
- As a workspace member, I want to create a project in my workspace, so that
  my team has a place to organise a piece of work.
- As a workspace member, I want to see all of the workspace's projects on the
  workspace page, so that I know what the team is working on.
- As a workspace member, I want to open a project's page and read its name
  and description, so that I understand what the project is for.
- As anyone outside a workspace, I want its projects to stay invisible to me,
  so that each team's information stays private.

## Acceptance criteria

### Creating a project
- **AC-1** Given a member of a workspace (the owner included), when they
  choose the create-project action from that workspace's page, then they see
  a form asking for a project name and an optional description. The form
  makes clear which workspace the project will be created in (see OQ-1).
- **AC-2** Given a valid name, with or without a description, when the member
  submits the form, then:
  - a project is created in that workspace, and **only** that workspace;
  - the member lands on the new project's page;
  - they see a confirmation message.
- **AC-3** Given a name that is empty or only spaces, when the member submits,
  then no project is created and the form shows an error on the name field.
  Spaces at the start and end of the name are removed before it is saved
  (see OQ-2).
- **AC-4** Given a name or description longer than its maximum length (see
  OQ-2), when the member submits, then no project is created, and the form
  shows an error on that field stating the limit. What the member typed stays
  in the form.
- **AC-5** Given a workspace that already has a project with a certain name,
  compared without regard to letter case, when a member submits a project
  with that name in the **same** workspace, then no project is created and
  the name field shows an error saying the workspace already has a project
  with that name. The same name in a **different** workspace is allowed (see
  OQ-3).
- **AC-6** Given an empty description, or one of only spaces, when the member
  submits an otherwise valid form, then the project is created with no
  description.

### Seeing a workspace's projects
- **AC-7** Given a workspace member, when they open the workspace page, then
  it has a projects section showing:
  - the number of projects;
  - every project in that workspace, each linking to its page, in
    alphabetical order of name, ignoring letter case (see OQ-4);
  - a create-project action (see OQ-1).

  The existing members section and the owner's add-member section stay as
  they are.
- **AC-8** Given a workspace with no projects, when a member opens the
  workspace page, then the projects section shows a clear empty-state
  message, with a create-project action inside the empty state itself.
- **AC-9** Given a workspace page, then it never lists projects that belong to
  another workspace.

### Viewing a project
- **AC-10** Given a workspace member, when they open a project in that
  workspace, then the project page shows:
  - the project's name;
  - its description, keeping the line breaks the author typed, or a short
    "No description" note when there is none;
  - which workspace it belongs to, with a way back to that workspace's page
    (see OQ-5).
- **AC-11** Given a project name or description that contains text that looks
  like HTML or script, when it is shown anywhere (the workspace page, the
  project page, the confirmation message or the page title), then it is
  displayed as plain text and never run or rendered as markup.

### Access rules
- **AC-12** Given a signed-in user who is **not** a member of a workspace,
  when they try to open:
  - that workspace's create-project page;
  - any of its project pages;
  - or submit a create-project request for it,

  then they get a "not found" response, the same one they would get if the
  workspace or project didn't exist. Nothing reveals a project's name,
  description or existence, and a create request creates nothing.
- **AC-13** Given a project that belongs to one workspace, when a project page
  is requested as though the project belonged to a different workspace, even
  one the user is a member of, then the response is "not found". A project
  can only be reached through the workspace it belongs to.
- **AC-14** Given a project ID or workspace ID that doesn't exist, when a
  signed-in user requests it, then they get the same "not found" response as
  in AC-12.
- **AC-15** Given an anonymous visitor, when they open a create-project page
  or a project page, then they are redirected to login, the redirect
  remembers the page they asked for, and after logging in they land on that
  page. The usual access rules still apply there: a non-member still gets
  "not found".
- **AC-16** Given an anonymous visitor, when they submit a create-project
  form, then nothing is created and they are sent to login. After logging
  in, the submission is **not** replayed, and they land on the dashboard
  (step 02's rule).
- **AC-17** Given a create-project form submitted from outside the site
  (without the site's anti-forgery token), then it is rejected and nothing
  is created.
- **AC-18** Given a request to create a project made as a simple link visit or
  page load instead of submitting the form, then nothing is created.

### Data integrity
- **AC-19** Given any project, then it belongs to exactly one workspace, and
  that never changes in this step.
- **AC-20** Given two members who submit projects with the same name (ignoring
  letter case) in the same workspace at the same moment, then at most one is
  created. The other member sees the duplicate-name error, not a server
  error (see OQ-3).

### Design and behaviour preserved
- **AC-21** Given the new and changed pages (the workspace page's projects
  section, the create-project page and the project page), then they follow
  the step 03 design system and meet its accessibility rules:
  - semantic colour tokens only;
  - one main heading and a correct heading order;
  - labelled fields with linked errors;
  - visible focus;
  - targets of at least 24px;
  - no sideways scrolling at 320px, with long names and descriptions
    wrapping;
  - reduced motion respected;
  - no new scripts, fonts or icon packages.

  The ui-ux-pro-max workflow is applied and recorded, as CLAUDE.md requires.
- **AC-22** Given the finished step, then all existing behaviour from steps 01
  to 03 is unchanged and every existing test still passes.

## Out of scope
- Tasks and task assignment
- Project-specific members, roles, or a project owner separate from workspace
  membership
- Editing, renaming, deleting or archiving projects
- Project status, priority, due dates, labels or progress
- Comments, attachments, notifications and activity history
- Search, filtering and user-controlled sorting of projects
- Listing projects on the dashboard or anywhere other than the workspace page
  (see OQ-6)
- Recording or showing who created a project, or when (see OQ-5)
- Rich text, Markdown or links in descriptions. They are plain text only.
- Changing workspace membership or ownership
- New dependencies or JavaScript

## Decisions
These were open questions. The user accepted the proposed answers on
2026-10-06, including OQ-3 (names unique within a workspace, ignoring letter
case).

- **OQ-1 Who can create projects, and where the action lives.** Any workspace
  member can create projects, not only the owner, because the description
  says "a workspace member".
  - The create-project action appears in the projects section
    header and inside its empty state. Every member sees it.
  - The create page names the workspace ("New project in <workspace>"), and
    its Cancel action returns to the workspace page. → AC-1, AC-7, AC-8
- **OQ-2 Field limits.**
  - the name is required, at most 100 characters, with leading and trailing
    spaces removed (the same as workspace names);
  - the description is optional, plain text, at most 2,000 characters, with
    leading and trailing spaces removed. → AC-3, AC-4, AC-6
- **OQ-3 Name uniqueness.** The description leaves this to review.
  - **Decision:** names are **unique within a workspace, ignoring letter
    case**, and the same name may be used in different workspaces.
    Two projects called "Website" and "website" in one team's list would be
    confusing, and the rule matches how usernames already behave.
  - The rejected alternative was no uniqueness at all, which is the same rule
    as workspace names in step 02. → AC-5, AC-20
- **OQ-4 Project list order.** Alphabetical by name, ignoring
  letter case, with no sorting controls. This matches the dashboard's
  workspace list. → AC-7
- **OQ-5 Project page details.**
  - the page shows the name, the description, and the parent workspace with
    a back link;
  - it shows no creator or creation date, because neither was asked for.
    They can be added with activity history later. → AC-10
- **OQ-6 Dashboard.** The dashboard doesn't change in this step.
  Projects are reached through their workspace page. A dashboard overview can
  come later. → Out of scope

## Open questions
- (none)

No new dependencies are needed. Everything above can be built with what
CLAUDE.md already allows.
