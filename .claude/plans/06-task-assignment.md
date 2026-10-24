---
step: 06
slug: task-assignment
spec: .claude/specs/06-task-assignment.md
status: done
created: 2026-10-07
approved: 2026-10-07
---

# Plan 06 — Task assignment

Token-efficient workflow (CLAUDE.md). The access chain, no-replay, CSRF and
design-system rules are reused as documented, not re-explained.

## Approach

| Concern | Decision | Why |
|---|---|---|
| Data | `Task.assignee = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=SET_NULL, related_name='assigned_tasks')` | A single nullable FK makes "at most one assignee" structural (AC-4). `SET_NULL`: see D-1. |
| Who can be chosen | A new `Workspace.assignable_users()` on `workspaces/models.py`: active users with a membership in this workspace, ordered owner first, then `Lower(username)`, using the same `Case`/`When` as `member_list()` | The rule lives on the model (CLAUDE.md), with one source for both the choices and the validation (AC-2, OQ-1). |
| Validation | `TaskAssignForm(ModelForm)` with `fields = ('assignee',)`. The field is a `ModelChoiceField` with `queryset = workspace.assignable_users()`, `required=False` and `empty_label='Unassigned'`. | Django rejects any ID outside the queryset with an "invalid choice" error on the field. That covers another workspace's user, an inactive user and a missing ID (AC-7, AC-8) without custom checks. The workspace comes from the authorised scope, never from the request. |
| Endpoint | `TaskAssignView(LoginRequiredNoReplayMixin, MemberProjectMixin, SingleObjectMixin, FormView)` at `tasks:assign`, `…/tasks/<pk>/assign/`, with `http_method_names = ['post']` and `get_queryset() = self.project.tasks.all()` | The step 02 `AddMemberView` pattern: a scoped lookup first (wrong or missing scope → 404, AC-9), POST only (a GET gets 405, AC-11), anonymous POST → no replay (AC-10), CSRF from the form (AC-11). |
| Saving | Compare the old and new assignee. **Same** → no write, `messages.info` ("<username> is already assigned." / "This task is already unassigned.", AC-6). **Different** → `task.assignee = new; task.save(update_fields=['assignee'])`, then `messages.success` ("Task assigned to <username>." / "Task is now unassigned.", AC-3, AC-5). Redirect to `tasks:detail` (Post/Redirect/Get). | `update_fields` writes only the assignee, so title and description can't be overwritten. |
| Invalid submission | Show `task_detail.html` again, status 200, with the bound form and its field error. The assignee is unchanged (AC-7). | Same as `AddMemberView.form_invalid`. |
| Shared page context | `TaskPageMixin.get_context_data` adds `assign_form` (an unbound one, unless the view passes a bound one). Both `TaskDetailView` and `TaskAssignView` use it. | One place builds the task page, just as `WorkspacePageMixin` builds the workspace page. |
| UI (task page only) | A new `.card` `<section aria-labelledby="assignee-heading">` after Description: `h2` "Assignee", the current value (the `user` icon and username in `wrap-anywhere`, or a muted "Unassigned"), then a POST form with `{% csrf_token %}`, the select through `partials/form_body.html` (label "Assignee", shared `.form-field select` styling) and a `.btn-secondary` "Save assignee". | Reuses the existing components, icon and form partial (CLAUDE.md, Frontend). No new pattern, so no skill searches unless a design question comes up. MASTER gets a one-line note. |

Deactivated assignees: an assignment made earlier stays visible. That user
isn't offered again, so re-submitting them gives the invalid-choice error
(consistent with AC-7). Spec 06 leaves later deactivation out of scope.

## Data model & migrations
- `tasks/models.py`: `Task.assignee`, as above.
- `tasks/migrations/0002_task_assignee.py`, from `makemigrations tasks`.
  Existing tasks become unassigned (`NULL`). No data migration is needed.
- `workspaces/models.py`: `Workspace.assignable_users()`. It's a method, so
  there's no migration.

## Files
- **Modified:**
  - `tasks/models.py`;
  - `tasks/forms.py`: `TaskAssignForm`;
  - `tasks/views.py`: `TaskPageMixin`, `TaskAssignView`, and
    `TaskDetailView` using the mixin;
  - `tasks/urls.py`: `assign`;
  - `tasks/templates/tasks/task_detail.html`: the Assignee section;
  - `workspaces/models.py`: `assignable_users()`;
  - `design-system/project-management-system/MASTER.md`: a one-line
    "Assignee section" note.
- **Created:**
  - `tasks/migrations/0002_task_assignee.py`;
  - `tasks/tests/test_assignment.py`.

## Implementation steps
- [x] 1. Model field, `assignable_users()`, then `makemigrations tasks` and `migrate`.
- [x] 2. `TaskAssignForm`, `TaskPageMixin`, `TaskAssignView` and the `assign` URL.
- [x] 3. The task page Assignee section (read MASTER first; reuse the components).
- [x] 4. Tests in `tasks/tests/test_assignment.py`, written directly from the spec (below).
- [x] 5. Verify: focused (`tasks`), drift, `check`, then the full suite.
- [x] 6. Manual check (D-2) of the Assignee section at 320 and 1280px: the select and button sizes, focus, a long username wrapping, and the error display.
- [x] 7. Record "Files changed" and "Test results" concisely, then set `built`.

## Test plan
Written directly in `/build`, behaviour-focused, in
`tasks/tests/test_assignment.py`, reusing `tasks/tests/data.py`.

**Test data:**
- Alice owns Apollo; Bob is a member.
- Erin is a member of Apollo, but inactive.
- Carol owns Hermes; Dave belongs to nothing.
- Task T is in Apollo/Roadmap.

| AC | Asserts |
|---|---|
| AC-1 | A new task's page shows "Unassigned". After assigning, it shows the username. |
| AC-2 | The select's options are exactly ["Unassigned", Alice, Bob], with the owner first, then alphabetical. Erin, Carol and Dave are absent. |
| AC-3 | Bob POSTs Alice → 302 to `tasks:detail`, `T.assignee == Alice`, and a success message names Alice. |
| AC-4 | Reassigning to Bob replaces Alice. The model has a single FK. |
| AC-5 | POSTing an empty value → `assignee is None`, with the message "Task is now unassigned." |
| AC-6 | Re-POSTing the current assignee, or empty when already unassigned → no change, with an info message. Title and description are untouched. |
| AC-7 / AC-8 | POSTing Carol's ID, Erin's ID or a missing ID → 200, a field error on `assignee`, and the previous assignee unchanged. Only allowed users ever end up stored. |
| AC-9 | A non-member POST, wrong workspace or project in the URL, or a missing task → 404, with nothing changed. |
| AC-10 | Anonymous POST → 302 to exactly the login URL (no `next`), nothing changed. |
| AC-11 | A POST without the CSRF token → 403, and a GET of `assign` → 405. Nothing changes in either case. |
| AC-12 | The select has a `<label>`, the error is linked through `aria-describedby`/`aria-invalid` (the existing partial), the button is `.btn-secondary`, and the username has `wrap-anywhere`. Layout comes from the step 6 manual check. |
| AC-13 | The full suite (378 existing tests) passes. |

## Risks
- **Assigning outside the workspace:** the queryset-limited choice field
  plus the server-set workspace, tested with altered IDs (AC-7).
- **IDOR through the URL:** the scoped `get_queryset` from
  `MemberProjectMixin` (AC-9).
- **Overwriting other fields:** `update_fields=['assignee']`.
- **The database can't enforce workspace membership across tables:** the
  form is the only write path, and there's no admin registration. Accepted,
  the same as the other form-only rules.

## Decisions needing approval
The user answered these on 2026-10-07.
- **D-1:** *Answer:* **(a) `SET_NULL`.** Deleting an assignee's account
  leaves their tasks unassigned.
- **D-2:** *Answer:* **(a) the same visual check as before.** Claude uses the
  browser tools if they're connected; otherwise `/build` stops once with a
  short manual checklist.

## Files changed
By `/build`, 2026-10-07:
- **Modified:**
  - `tasks/models.py`: `Task.assignee` (nullable FK to the user model,
    `SET_NULL`, `related_name='assigned_tasks'`).
  - `workspaces/models.py`: `Workspace.assignable_users()` (active members,
    owner first, then by username ignoring case).
  - `tasks/forms.py`: `TaskAssignForm` (choices limited to
    `assignable_users()`, empty label "Unassigned", not required).
  - `tasks/views.py`: `TaskPageMixin` (scoped `get_queryset` and the task-page
    context with `assign_form`); `TaskDetailView` now uses it;
    `TaskAssignView` (POST only, previous assignee captured before
    validation, no-op info message, `update_fields=['assignee']`).
  - `tasks/urls.py`: `assign` (`<pk>/assign/`).
  - `tasks/templates/tasks/task_detail.html`: the Assignee card.
  - `design-system/project-management-system/MASTER.md`: the "Assignee
    section (step 06)" note.
  - `tasks/tests/test_views.py`: `test_no_creator_or_date_shown` now checks
    member names everywhere **except** the Assignee section. Spec 06 AC-2
    deliberately lists members in that control; the no-creator and no-date
    rules are unchanged.
- **Created:**
  - `tasks/migrations/0002_task_assignee.py` (applied);
  - `tasks/tests/test_assignment.py` (13 tests, written directly from the
    spec; no sub-agents).

**Decisions:** no new UI pattern, so no skill searches (CLAUDE.md:
design-system first). The Assignee card reuses `.card`, the `user` icon,
`form_body.html` and `.btn-secondary`.

## Test results
Run directly by `/build` on 2026-10-07 (Python 3.12.10, Django 5.2.17):
- Focused: `manage.py test tasks.tests.test_assignment`: 13/13 OK.
- Drift: no changes detected. `check`: no issues.
- Full suite: 391/391 OK (378 existing + 13 new).
- One existing test adjusted on purpose (listed above).
- Manual visual check (D-2): the browser tools weren't used. The user
  checked the Assignee card at 320px and 1280px and reported "all pass" on
  2026-10-07. Sizes weren't measured.

## Review log

### 2026-10-07: review (one concise pass, no sub-agents)

**Scope:** the "Files changed" list above.

**Checked, no issues:**
- **Access:** `TaskAssignView` resolves workspace → project → task through
  `MemberProjectMixin` and `TaskPageMixin.get_queryset()` before the form
  runs, so a wrong or missing scope gives 404 (AC-9). It's POST-only, so a
  GET gets 405. Anonymous POSTs aren't replayed (AC-10). CSRF is in the form
  (AC-11).
- **Validation:** choices come only from `Workspace.assignable_users()`, so
  other-workspace, inactive and missing IDs are invalid choices (AC-7,
  AC-8).
- **Writes:** `update_fields=['assignee']` can't overwrite other fields.
  Detecting the same assignee uses the value captured before validation
  (AC-6).
- **Escaping:** messages and the username are escaped, with no `|safe`.
- **Accessibility:** the label and error links come from `form_body.html`,
  the button is `.btn-secondary`, the username has `wrap-anywhere`, and no
  new tokens or icons were added.

| ID | Sev | file:line | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| Q-70 | Low | `tasks/templates/tasks/task_detail.html:27-33`; `tasks/forms.py:44` | If a task's current assignee was **deactivated after** being assigned, the card shows their name, but they aren't in the select. The browser then preselects "Unassigned", so pressing "Save assignee" without changing anything silently unassigns the task. It's an edge case, because later deactivation is out of scope in spec 06. | Accept for now. When deactivation handling is specified, show the current inactive assignee as a disabled option or add a note above the select. | accepted (user, 2026-10-07); recorded in CLAUDE.md Known limitations |
| Q-71 | Low | CLAUDE.md "Deferred to step 06 (step 05 review)" | Spec and plan 06 didn't include the items deferred to step 06 (Q-54 to Q-61, Q-69), so they're still open. Q-69 (`WorkspaceCreateView` accepts PUT) is the only one with any security angle, and it isn't exploitable. | At `/done`, re-label the list "Deferred to a later step" (or to step 07), so CLAUDE.md doesn't claim step 06 handled them. | accepted (user, 2026-10-07); CLAUDE.md list relabelled |

**Result:** High 0 · Medium 0 · Low 2. No High findings are open, so the
status is `reviewed`.
