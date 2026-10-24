---
step: 02
slug: workspace-membership
status: done
created: 2026-10-05
approved: 2026-10-05
---

# 02 — Workspaces and membership

## Goal
A signed-in user can create a workspace, becomes its owner, and can add other
registered users to it by username. Everyone in a workspace can see its name
and who belongs to it. Nobody outside it can see it at all.

## Context / why now
Step 01 delivered accounts, login and logout, and a signed-in dashboard that
only greets the user. Projects and tasks come next, and they need a shared
space with known members that decides who may see them. This step builds that
space and its access rules on their own, before any projects or tasks depend
on them. The "members only, everyone else is kept out" behaviour gets proved
here, and later steps reuse it.

## User stories
- As a signed-in user, I want to create a workspace with a name, so that my
  team has a shared place to work in.
- As a workspace owner, I want to add registered users by username, so that
  the people I work with can join the workspace.
- As a workspace member, I want to see the workspace name and its member list,
  so that I know who I am working with.
- As a user who belongs to several workspaces, I want to see all of them and
  open each one, so that I can move between my teams.
- As any user, I want workspaces I don't belong to kept hidden from me, and
  mine kept hidden from others, so that each team's information stays private.

## Acceptance criteria

### Creating a workspace
- **AC-1** Given a signed-in user, when they open the "create workspace" page,
  then they see a form asking for a workspace name.
- **AC-2** Given a valid name, when the user submits the form, then a
  workspace with that name is created. The user becomes its owner and is
  listed as one of its members. They land on the new workspace's page and see
  a confirmation message.
- **AC-3** Given a name that is empty or contains only spaces, when the user
  submits, then no workspace is created and the form shows an error on the
  name field. Spaces at the start and end of a valid name are removed before
  it is saved (see OQ-1).
- **AC-4** Given a name longer than the maximum length (see OQ-1), when the
  user submits, then no workspace is created and the form shows an error on
  the name field that states the limit. The name the user typed stays in the
  form.
- **AC-5** Given a workspace that already has a certain name, when any user
  (including the same user) creates another workspace with that name, then
  the new workspace is created as a separate workspace (see OQ-1).

### Viewing a workspace
- **AC-6** Given the owner or a member of a workspace, when they open its
  page, then they see the workspace name and the list of its current members.
  Members are shown by username, with the casing each person chose at
  registration.
- **AC-7** Given a workspace's member list, then the owner is labelled
  "Owner" and everyone else is labelled "Member". The owner appears first.
  The other members follow in alphabetical order by username, ignoring letter
  case (see OQ-5).
- **AC-8** Given a workspace name or username that contains text that looks
  like HTML or script, when the page is shown, then it is displayed as plain
  text and not run or rendered as markup.

### Finding my workspaces
- **AC-9** Given a signed-in user, when they open the dashboard, then they see
  a list of every workspace they own or belong to, each linking to its page,
  and a link to create a new workspace (see OQ-4).
- **AC-10** Given a signed-in user who belongs to no workspaces, when they
  open the dashboard, then they see a short message saying they have no
  workspaces yet, and the link to create one.
- **AC-11** Given a user who belongs to several workspaces, including some
  they own and some they were added to, then all of them appear on their
  dashboard, and they can open each one's page. Workspaces they don't belong
  to never appear.

### Adding members (owner only)
- **AC-12** Given the owner of a workspace, when they open its page, then they
  see a form to add a member by username.
- **AC-13** Given the username of an active registered user who is not yet a
  member, when the owner submits it, then that user becomes a member. The
  owner sees a confirmation message naming the user, and the user appears in
  the member list labelled "Member".
- **AC-14** Given a username typed in a different letter case from the one
  registered (for example "BOB" for "Bob"), when the owner submits it, then
  the right user is added. The member list shows the casing chosen at
  registration (see OQ-2).
- **AC-15** Given a username that belongs to someone who is already a member,
  or the owner's own username, when the owner submits it, then no duplicate
  membership is created. The member list is unchanged, and the owner sees a
  clear message saying that user is already a member of the workspace.
- **AC-16** Given a username that matches no account, or matches an account
  that has been deactivated, when the owner submits it, then nobody is added,
  and the form shows an error on the username field saying no user with that
  username was found (see OQ-3). The username the owner typed stays in the
  form.
- **AC-17** Given an empty username field, when the owner submits, then
  nobody is added and the form shows an error on the username field.
- **AC-18** Given a user who has just been added to a workspace, when they
  next open their dashboard, then the workspace is listed. When they open its
  page, they see it as a member.

### Access rules
- **AC-19** Given a workspace member who is not the owner, when they open its
  page, then they can see the name and the member list, but no add-member
  form is shown.
- **AC-20** Given a workspace member who is not the owner, when they send an
  add-member request directly (for example a hand-crafted form submission),
  then it is refused, nobody is added, and the membership stays unchanged
  (see OQ-6).
- **AC-21** Given a signed-in user who does not belong to a workspace, when
  they try to open its page or send an add-member request for it, then they
  get a "not found" response. That response is the same one they would get
  for a workspace that doesn't exist, so it doesn't reveal that the workspace
  exists, its name or its members. A request to add a member has no effect
  (see OQ-6).
- **AC-22** Given an anonymous visitor, when they open the create-workspace
  page or a workspace's page, then they are redirected to login, and that
  redirect remembers the page they asked for. When they then log in
  successfully, they land on that page, and the usual access rules apply
  there: a non-member still gets "not found" (AC-21).
- **AC-23** Given an anonymous visitor, when they submit a create-workspace or
  add-member action, then nothing is created or changed, and they are sent to
  login. When they then log in successfully, the original submission is
  **not** carried out, either automatically or by any later step, and they
  are not sent back to the submit action itself. They land on the dashboard
  instead. If they still want to create the workspace or add the member, they
  do it again from there.
- **AC-24** Given a create-workspace or add-member form submitted from outside
  the site (without the site's anti-forgery token), then the request is
  rejected and has no effect.
- **AC-25** Given a request to create a workspace or add a member made as a
  simple link visit or page load instead of submitting the form, then nothing
  is created or changed.

### Data integrity
- **AC-26** Given any workspace, then each user appears in its member list at
  most once. This holds even if the same add-member request is sent twice at
  the same moment.
- **AC-27** Given any workspace, then it has exactly one owner, and that owner
  is always one of its members.

## Out of scope
- Projects and tasks
- Any workspace roles other than owner and member (for example admins or
  viewers)
- Changing or transferring ownership
- Removing members, or members leaving a workspace
- Email invitations, or any email at all
- Inviting people who don't have an account yet
- Teams or departments inside a workspace
- Workspace settings, descriptions, logos or other details beyond the name
- Renaming or deleting a workspace
- Searching for users, autocomplete, or listing all registered users. The
  owner must already know the username.
- Telling a user that they have been added to a workspace (notifications)
- What happens to a workspace's ownership or membership when an account that
  already owns or belongs to it is deactivated later. AC-16 only decides
  whether a deactivated account can be newly added.
- Admin-site tooling for workspaces, beyond whatever the framework gives by
  default
- Visual design beyond a clean layout that matches the existing pages

## Decisions
These were open questions. The user accepted the proposed answers on
2026-10-05.

- **OQ-1 Workspace names.** A name is required. Spaces at the
  start and end are removed, and a name of only spaces counts as empty. The
  maximum length is 100 characters. Names do **not** need to be unique, even
  for the same owner, because workspaces are told apart by their page and not
  by their name. → AC-3, AC-4, AC-5
- **OQ-2 Matching the username to add.** Letter case is ignored, the
  same way login does in step 01. Usernames are already unique ignoring case,
  so this always finds at most one person. → AC-14
- **OQ-3 Adding deactivated or unknown accounts.** Deactivated
  accounts cannot be added. The owner sees the same "no user with that
  username" message as for a name that doesn't exist. Registration already
  shows whether a username is taken, so this message reveals nothing new
  about which usernames exist. → AC-16
- **OQ-4 Where users find their workspaces.** The dashboard lists the user's
  workspaces and links to "create workspace". This fills the dashboard space
  that step 01 kept free for later content. A separate "all workspaces" page
  can wait until it's needed. → AC-9, AC-10, AC-11
- **OQ-5 Member list order and labels.** Owner first, labelled
  "Owner". Everyone else follows alphabetically by username, ignoring case,
  labelled "Member". Join dates are not shown. → AC-7
- **OQ-6 What refused requests look like.** A non-member gets
  "not found" for everything about the workspace, so its existence stays
  hidden. A member who is not the owner and sends an add-member request
  directly gets a "forbidden" response: they already know the workspace
  exists, and a clear refusal is more honest than pretending it is missing.
  → AC-20, AC-21

## Open questions
- (none)

No new dependencies are needed. Everything above can be built with what
CLAUDE.md already allows.
