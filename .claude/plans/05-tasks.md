---
step: 05
slug: tasks
spec: .claude/specs/05-tasks.md
status: done
created: 2026-10-06
approved: 2026-10-06
---

# Plan 05 — Tasks

## Starting state (checked 2026-10-06)
- Steps 01–04 are `done`, and 269 tests pass.
- **Members-only access lives in two places today** (CLAUDE.md, step 04's Q-35):
  - `workspaces/views.py`: `WorkspacePageMixin.get_queryset()` →
    `Workspace.objects.for_user(user)`, used for the workspace's own pages.
  - `projects/views.py`: `ProjectWorkspaceMixin.dispatch()` →
    `get_object_or_404(Workspace.objects.for_user(user), pk=kwargs['workspace_pk'])`,
    used for nested resources. It sits after `LoginRequiredNoReplayMixin`
    in each view's bases.
- **`projects` app:**
  - `Project` (`workspace` FK, CASCADE, `related_name='projects'`; `name`
    100; `description` 2000; the per-workspace case-insensitive
    `UniqueConstraint`);
  - `ProjectForm`;
  - `ProjectCreateView` (an atomic save, with `IntegrityError` caught outside
    the block) and `ProjectDetailView` (GET only, `self.workspace.projects`);
  - URLs `projects:create` and `projects:detail` nested at
    `workspaces/<workspace_pk>/projects/`.
- **`project_detail.html`:**
  - the back link shows only the workspace name, inside a `<span>` (Q-40);
  - the `h1` name;
  - a Description `.card` using `linebreaksbr`.
- **`workspace_detail.html`'s projects section:** the header "New project"
  shows only when projects exist (accepted, step 04 Q-33). The empty state
  says "Create a project", and the create page's submit says "Create
  project" (Q-41).
- **Tests that pin the step 04 wording AC-22 changes:**
  - `projects/tests/test_ui.py:170` (`['Create a project']`);
  - `projects/tests/test_views.py:268` (`'Create a project'`).

  The back-link tests (`test_views.py:311-316`, `test_ui.py:276`) only
  require a link containing "Apollo", so "Back to Apollo" still satisfies
  them.
- **Test helpers:** `projects/tests/test_ui.py:20-30` imports nine helpers
  from `core.tests.test_ui`. `core/tests/test_ui.py:475` hard-codes the apps
  whose templates the token check scans as
  `('accounts', 'core', 'workspaces')` (Q-46).
- **Admin stubs:** `projects/admin.py` and `workspaces/admin.py` still say
  "# Register your models here." (Q-44).

## Approach

The step has three parts, built in this order so that tasks never copy the
old pattern:

1. **Consolidate the nested-access pattern (Q-35).** It becomes one small
   chain of mixins, each scope resolved strictly inside its parent:
   - `MemberWorkspaceMixin` in `workspaces/mixins.py` resolves the
     workspace;
   - `MemberProjectMixin` in `projects/mixins.py` extends it and resolves
     the project.

   Projects switch to the first mixin, with no behaviour change. Tasks use
   the second.
2. **Add tasks:** a new `tasks` app with URLs nested under the project,
   `/workspaces/<workspace_pk>/projects/<project_pk>/tasks/…`, namespace
   `tasks:`.
3. **Clear the remaining step 04 deferred items:**
   - two wording changes, AC-22;
   - comments, admin stubs and test hygiene, AC-23.

| Concern | Choice | Why not the obvious alternative |
|---|---|---|
| Shared scoped lookup (Q-35, AC-23) | `workspaces/mixins.py`: `MemberWorkspaceMixin` with `dispatch()` → `self.resolve_scope(**kwargs)` → `super().dispatch()`. Its `resolve_scope` sets `self.workspace = get_object_or_404(Workspace.objects.for_user(self.request.user), pk=kwargs['workspace_pk'])`. `get_context_data` adds `workspace`. `projects/mixins.py`: `MemberProjectMixin(MemberWorkspaceMixin)` overrides `resolve_scope` to call `super()` first and **then** set `self.project = get_object_or_404(self.workspace.projects.all(), pk=kwargs['project_pk'])`, adding `project` to the context. Both docstrings say: list them **after** `LoginRequiredNoReplayMixin` in the bases. | A `resolve_scope` hook makes "workspace → project → task" an explicit chain, where each level can only see inside the one above. Overriding `dispatch` twice would hide the order. A copy in `tasks` would be a third lookup site. Feature apps already import from `workspaces`, and `tasks` imports from `projects`, so imports only point down the hierarchy. `ProjectWorkspaceMixin` is deleted and the project views use `MemberWorkspaceMixin`, with identical behaviour; the existing 80 project tests prove it. |
| Where tasks live | A new **`tasks`** app, registered after `projects` | CLAUDE.md says `projects` is its own app "because tasks will belong to projects". Later features (assignment, status) attach to tasks. |
| One project per task (AC-19) | `Task.project = ForeignKey('projects.Project', on_delete=CASCADE, related_name='tasks')`, not null. It is set **only** on the server: `form.instance.project = self.project`. `TaskForm` has no `project` or `workspace` field. | A posted `project` or `workspace` value can't move a task. The workspace comes through the project. There's no separate `workspace` foreign key, which avoids two sources of truth that could disagree. On CASCADE, see D-2. |
| Access order (AC-12–AC-14) | `TaskCreateView(LoginRequiredNoReplayMixin, MemberProjectMixin, CreateView)` and `TaskDetailView(LoginRequiredNoReplayMixin, MemberProjectMixin, DetailView)`, whose `get_queryset()` is `self.project.tasks.all()`. | Workspace (members only), then project (inside that workspace), then task (inside that project). A wrong workspace ID, a project from another workspace, a project from the same workspace but the wrong one for the task, and a missing ID all hit `Http404` from the same chain. No unscoped `Task` lookup exists. |
| Who may create | Any member. The members-only workspace lookup is the whole permission, as for projects. | Spec 05 says any member who can access the project. |
| Anonymous GET vs POST (AC-15, AC-16) | `LoginRequiredNoReplayMixin` comes first in the bases, so login is checked before any scope lookup. | It's the existing pattern. An anonymous visitor learns nothing about which IDs exist. |
| Fields (OQ-2, AC-3–AC-5) | `title = CharField(max_length=200)`. `description = TextField(max_length=2000, blank=True)`. `ModelForm` strips both. Labels are "Task title" and "Description (optional)". Widgets: title `autocomplete="off"`; description `Textarea(rows=5)`. | The same mechanism as projects. |
| No title uniqueness (OQ-3, AC-6) | No constraint and no `clean_title` check. The save needs no `IntegrityError` handling, because no uniqueness can be violated. | Spec 05 allows duplicates. Adding the step 04 race code here would be dead code. |
| Stable oldest-first order (OQ-4, AC-7) | `TaskQuerySet.in_creation_order()` → `order_by('pk')`. **No timestamp field, and nothing is shown to users.** | The auto-increment primary key already records insertion order and never changes, so it is the "internal record" spec 05 allows. A `created_at` field would add a column that spec 05 says not to show, for no extra stability. See D-3 and Risks for the one edge case. |
| Project page integration (AC-7–AC-9) | `ProjectDetailView.get_context_data` adds `tasks = self.object.tasks.in_creation_order()`. `projects` doesn't import `tasks`; it uses the reverse relation, a runtime dependency recorded in CLAUDE.md as in Q-45. The tasks section is a new `.card` placed **after** the Description card. | Only this project's tasks can appear (AC-9). The project's own content stays first and unchanged (AC-7). |
| Create flow (AC-1, AC-2) | `TaskCreateView`: `get_form_kwargs` is standard. `form_valid`: `form.instance.project = self.project`, `self.object = form.save()`, `messages.success(f'Task "{title}" was created.')`, redirect to `tasks:detail`. The context has `workspace` and `project`, for the heading "New task", the line "in <project> · <workspace>", and Cancel going back to the project page. | It's Django's standard `CreateView`, plus the scoped parent. |
| Task page (AC-10) | `TaskDetailView` (GET/HEAD/OPTIONS). A back link "Back to <project name>" (`arrow-left`) goes to the project page. A muted context line shows "<workspace> · <project>". Then the `h1` title (`wrap-anywhere`) and a Description `.card` using `linebreaksbr`, or "No description". | `linebreaksbr` escapes before adding `<br>` (AC-11). The back link names its destination, which also fixes Q-40's problem on the new page. |
| Wording (AC-22, D-4) | **Q-40:** the project page's back link becomes "Back to <workspace name>", with the name still in its own `<span>`. **Q-41:** the action that **opens** a create form is labelled "New project" both in the workspace page header and in its empty state. The create page's `h1` is already "New project". The submit button keeps "Create project", because confirming is a different action, as in "New task" / "Create task". | Matches spec 05's OQ-5 rule for tasks ("New task" everywhere for the action). See D-4 for how "one label" is read. |
| Remaining deferred items (AC-23) | **Q-34:** `projects/forms.py` comment corrected (form validation never runs the `F('workspace')` constraint). **Q-43:** `projects/models.py` comment corrected (the constraint is the race backstop, and its message only appears through `full_clean()`). **Q-42:** a one-line comment at `projects/views.py`'s `except IntegrityError` saying the name constraint is the only expected cause, so revisit it if fields or constraints are added. **Q-44:** `projects/admin.py`, `workspaces/admin.py` and the new `tasks/admin.py` each say why they register nothing. **Q-46, Q-47, Q-48:** test-only work, handed to `test-author` (Test plan). | Comment and structure changes only, so behaviour stays the same and the existing suite proves it. |
| Admin | Tasks are not registered. | Consistent with workspaces and projects. |

### UI (spec 05 AC-20; CLAUDE.md "Frontend and UI work")
`/build` loads ui-ux-pro-max, reads MASTER.md (Project adjustments, including
"Project pages (step 04)"), runs the searches below, retries empty or
off-topic ones once and records any fallback. It adds a "Task pages
(step 05)" note to MASTER. It reuses the existing components; the only new
shared piece is one icon.

| Page | Layout | Searches (domain) |
|---|---|---|
| **Project page: tasks section** (new, **after** the Description card) | A `.card` `<section aria-labelledby="tasks-heading">`. The header has a `list-bullet` icon, `h2` "Tasks", a count badge, and, when tasks exist, a `.btn-primary` "New task" with `plus`. Rows are full-width `min-h-11` links (title with `min-w-0 wrap-anywhere`, then `chevron-right`), oldest first. The empty state is the dashed panel: "No tasks yet.", one supporting line, and its own `.btn-primary` "New task". Only one create action shows at a time (OQ-5). | `"empty state call to action"` (ux), `"todo list items"` (ux), `"list item link"` (ux; empty last time, so retry, then fall back), `"checklist task list"` (style) |
| **Create task** | The centred `max-w-md` `.card`: `h1` "New task", the muted line "in <project> · <workspace>", the form (title, description textarea), then secondary Cancel (→ project page) and primary "Create task". | `"form single field"` (ux), `"textarea optional"` (ux) |
| **Task page** | A back link "Back to <project>" (`min-h-11`), the muted context line "<workspace> · <project>", the `h1` title, and a `.card` with `h2` "Description" (`max-w-prose leading-relaxed wrap-anywhere`) or "No description". | `"breadcrumb context hierarchy"` (ux), `"long text readability"` (ux) |

**New icon:** `list-bullet` (Heroicons v2 outline, MIT) for tasks. CLAUDE.md
gives each icon one meaning: `folder` = workspace, `clipboard-document-list`
= project, `list-bullet` = tasks. `check-circle` stays reserved for success
messages.

## Data model & migrations
**`tasks.Task`**
- `project`: `ForeignKey('projects.Project', on_delete=CASCADE, related_name='tasks')`
- `title`: `CharField(max_length=200)`
- `description`: `TextField(max_length=2000, blank=True)`
- `objects = TaskManager.from_queryset(TaskQuerySet)()`, with
  `in_creation_order()` on the queryset
- `__str__` returns `title`
- No constraints, and no timestamp field.

**Migrations:**
- `tasks/migrations/0001_initial.py`, depending on `projects.0001_initial`.
- `projects` and `workspaces` have **no** model changes (moving the mixins
  is code only).
- No raw SQL.

## URLs, views, templates
`config/urls.py` gains
`path('workspaces/<int:workspace_pk>/projects/<int:project_pk>/tasks/', include('tasks.urls'))`,
placed **before** the projects include, which in turn stays before
`workspaces/`.

| URL name | Path | View | Template | Access rule |
|---|---|---|---|---|
| `tasks:create` | `/workspaces/<workspace_pk>/projects/<project_pk>/tasks/new/` | `TaskCreateView` | `tasks/task_form.html` | Any member. Non-member, a missing workspace or project, or a project from another workspace → 404 (GET and POST). Anonymous GET → login with `?next=`. Anonymous POST → login without `next`, nothing created. CSRF required. A GET never creates anything. |
| `tasks:detail` | `/workspaces/<workspace_pk>/projects/<project_pk>/tasks/<pk>/` | `TaskDetailView` (GET/HEAD/OPTIONS) | `tasks/task_detail.html` | Any member. A wrong workspace, project or task scope, or a missing ID → the same 404. Anonymous → login with `?next=`. |
| `projects:detail` | (existing) | `ProjectDetailView`, now using `MemberWorkspaceMixin` and adding `tasks` | `projects/project_detail.html` (gains the tasks section and Q-40's wording) | Unchanged |
| `projects:create` | (existing) | `ProjectCreateView`, now using `MemberWorkspaceMixin` | `projects/project_form.html` | Unchanged |
| `workspaces:detail` | (existing) | unchanged | `workspace_detail.html` (Q-41 wording only) | Unchanged |

**Files:**
- **Created:**
  - `workspaces/mixins.py`, `projects/mixins.py`;
  - the `tasks` app: `__init__`, `apps`, `admin`, `models`, `forms`,
    `views`, `urls`, `migrations/0001_initial.py`;
  - `tasks/templates/tasks/task_form.html` and `task_detail.html`;
  - `templates/partials/icons/list-bullet.html`.
- **Modified:**
  - `config/settings.py` and `config/urls.py`;
  - `projects/views.py`: uses the shared mixin, adds `tasks` to the context,
    and gets the Q-42 comment;
  - `projects/forms.py` (Q-34), `projects/models.py` (Q-43), and
    `projects/admin.py` and `workspaces/admin.py` (Q-44);
  - `projects/templates/projects/project_detail.html`: the tasks section and
    Q-40;
  - `workspaces/templates/workspaces/workspace_detail.html` (Q-41);
  - `design-system/project-management-system/MASTER.md`: the "Task pages
    (step 05)" note, plus a line on the action-label rule.

## Implementation steps
- [x] 1. **Consolidate access (Q-35):**
  - Create `workspaces/mixins.py` (`MemberWorkspaceMixin`) and
    `projects/mixins.py` (`MemberProjectMixin`).
  - Switch `ProjectCreateView` and `ProjectDetailView` to
    `MemberWorkspaceMixin`, and delete `ProjectWorkspaceMixin`.
  - Run `manage.py test projects workspaces`: all must pass unchanged. This
    is the "no behaviour change" proof for AC-23.
- [x] 2. **Remaining non-visible cleanup:** Q-34, Q-43, Q-42 comments, and
  Q-44 in both `admin.py` files. Run `manage.py check`.
- [x] 3. `startapp tasks`:
  - delete `tasks/tests.py`;
  - `tasks/admin.py` gets a one-line reason for not registering;
  - add `'tasks'` to `INSTALLED_APPS` after `'projects'`.
- [x] 4. `tasks/models.py`: `TaskQuerySet.in_creation_order()`, `TaskManager`
  and `Task`. Run `makemigrations tasks`, check the foreign key is `CASCADE`
  and `max_length` is 200 / 2000, then `migrate`.
- [x] 5. `tasks/forms.py`: `TaskForm` (`fields = ('title', 'description')`,
  with labels and widgets).
- [x] 6. `tasks/views.py` (`TaskCreateView`, `TaskDetailView`) and
  `tasks/urls.py` (`app_name='tasks'`, `create` and `detail`). Add the
  nested include to `config/urls.py`, before the projects include.
- [x] 7. `projects/views.py`: `ProjectDetailView.get_context_data` adds
  `tasks`.
- [x] 8. **UI workflow** before any markup:
  - load ui-ux-pro-max;
  - read MASTER (Project adjustments, including step 04's note) and
    `pages/workspace.md` *(at `/done`: `pages/workspace.md` was **not** read
    in this build; see the build notes, review Q-65/Q-66)*;
  - run the UI table's searches plus `--stack html-tailwind`
    `"list row hover"`;
  - retry once and record any fallback.
- [x] 9. Templates:
  - the tasks section in `project_detail.html`, plus Q-40;
  - Q-41 in `workspace_detail.html`;
  - `task_form.html` and `task_detail.html`;
  - the `list-bullet` icon;
  - the MASTER "Task pages (step 05)" note, recording the action-label rule
    (D-4) and the icon meanings.
- [x] 10. **Self-check:** `check`, then drift, then `manage.py test`.
  - **Expected:** exactly the two step 04 tests that pin "Create a project"
    fail (AC-22's deliberate wording).
  - **Any other failure** is treated as an application mistake.
- [x] 11. **Visual and responsive check (D-1):** check the project page (with
  tasks, without tasks, a long unbroken task title), create task (empty,
  with errors, a long description) and the task page (with and without a
  description), plus the workspace page and project page wording changes,
  at **320, 768 and 1280px**:
  - no sideways scrolling;
  - wrapping works;
  - focus is visible;
  - the target size of every new interactive element is checked.
- [x] 12. **Pre-delivery checklist** for the changed and new pages. Record
  only what was actually checked, and keep "designed" and "user-reported"
  apart from "measured" (lessons from step 04's Q-36).
- [x] 13. **Build notes:**
  - for each page, the MASTER rules applied, the searches (query, domain,
    result and effect, or the fallback), and the checklist outcome;
  - a target-size table with **320, 768 and 1280px** columns;
  - how step 11 was done.
- [x] 14. Fill in "Files changed". Hand off to `test-author`, then to
  `test-runner`, following `/build`.

## Test plan
**Changes to existing tests (spec 05 AC-21 and AC-23), all done by
`test-author` and listed in Files changed:**
- **AC-22 wording:** update `projects/tests/test_ui.py:170` and
  `projects/tests/test_views.py:268` from "Create a project" to "New
  project". Add assertions that the project page's back link reads "Back to
  Apollo".
- **Q-46:**
  - move the shared HTML and CSS helpers (`parse`, `by_id`, `main_of`,
    `component_rules`, `css_block`, `effective_min_h`, `tailwind_css`,
    `BASE_TEMPLATE`, `TAILWIND_CDN` and the colour regexes) out of
    `core/tests/test_ui.py` into `core/tests/helpers.py`, a module that isn't
    collected as tests;
  - `core/tests/test_ui.py`, `projects/tests/test_ui.py` and the new
    `tasks/tests/test_ui.py` import from it;
  - core's token check loops over **every** local app's `templates` folder
    (worked out from `INSTALLED_APPS`), so `projects` and `tasks` are
    scanned.
- **Q-47:** `projects/tests/test_ui.py` calls `pages()` once per test, and
  the textarea test asserts on `component_rules()` tokens.
- **Q-48:** add the "spec 04" prefix to the projects divider comments, and
  note in a docstring that spec 04 AC-22 is met by the full suite.
- **No behaviour assertion is removed or weakened.**

**New tests:** `tasks/tests/` (`data.py`, `test_models.py`, `test_forms.py`,
`test_views.py`, `test_ui.py`), plus `workspaces/tests/test_mixins.py` and
`projects/tests/test_mixins.py` for the shared mixins. All are tagged
"spec 05 AC-n".

**Test data:**
- Alice owns "Apollo", and Bob is a member of it.
- Carol owns "Hermes".
- Dave belongs to nothing.
- Apollo has the projects "Roadmap" and "Launch". Hermes has "Hermes Plan".
- All names are ASCII.

| AC | Test module | What it asserts |
|---|---|---|
| AC-1 | tasks/test_views | Alice and Bob each GET `tasks:create` for Roadmap → 200, with `title` and `description` fields. The page names "Roadmap" and "Apollo", and Cancel links to Roadmap's `projects:detail`. Roadmap's page links to `tasks:create`. |
| AC-2 | tasks/test_views, test_models | Bob POSTs "Write brief" plus a description → exactly 1 task, with `project = Roadmap`, and none on Launch or Hermes Plan. Redirects to its `tasks:detail`. Following it shows the message containing "Write brief". It also works with no description. |
| AC-3 | tasks/test_forms, test_views | `""` and `"   "` → error on `title`, and the count doesn't change. `"  Write brief  "` is saved trimmed. |
| AC-4 | tasks/test_forms, test_views | A 201-character title and a 2,001-character description each give an error on their field that mentions the limit; nothing is created; the typed values are shown again. Exactly 200 and 2,000 are accepted. |
| AC-5 | tasks/test_forms, test_views | A description of `"   "` → created with `description == ''`. |
| AC-6 | tasks/test_views, test_models | Two tasks titled "Review" in Roadmap → 2 tasks. A title differing only in letter case is also allowed. |
| AC-7 | tasks/test_views, test_models, test_ui | Roadmap's page shows the `tasks-heading` section with a count badge, and links in **creation order**. Three tasks created "Zeta", "alpha", "Mid" are listed in that order, **not** alphabetically. After a fourth is added, the first three keep their positions. The header "New task" appears when tasks exist. The name, the description card and the back link are still present. No date or time text appears in the section. `in_creation_order()` returns them ordered by pk. |
| AC-8 | tasks/test_views, test_ui | Launch with no tasks → "No tasks yet." **and** its own "New task" link to `tasks:create` inside the empty state, no header create link, and no task rows. |
| AC-9 | tasks/test_views | Launch's tasks never appear on Roadmap's page, and Hermes Plan's never appear on either. |
| AC-10 | tasks/test_views | The task page has the title as `h1` and a "line1\nline2" description as `line1<br>line2` ("No description" when it's empty). The context line names "Apollo" and "Roadmap", and the back link to Roadmap's `projects:detail` reads "Back to Roadmap". |
| AC-11 | tasks/test_views | A title of `<script>alert(1)</script>` and a description of `<b>x</b>\n<i>y</i>` are escaped on the project page, the task page (including `<title>`) and in the creation message, with `<br>` still present. The raw tags never appear. |
| AC-12 | tasks/test_views | Dave and Carol (non-members of Apollo): GET `create`, GET and HEAD `detail`, and POST `create` → all 404, never 403. Responses don't contain the task title or description, and the POST creates nothing. |
| AC-13 | tasks/test_views | Task T is in Roadmap (Apollo). **Viewing an existing task under the wrong parent → 404:** (a) `workspace_pk=Hermes`, `project_pk=Roadmap`, `pk=T` (Carol, and Bob after being added to Hermes); (b) `workspace_pk=Apollo`, `project_pk=Launch`, `pk=T` (Bob: the right workspace, the wrong project); (c) `workspace_pk=Apollo`, `project_pk=Hermes Plan`, `pk=T`. **Creating a task → 404 only when the URL scope itself is invalid, and nothing is created:** a GET or POST of `create` with (d) `workspace_pk=Hermes`, `project_pk=Roadmap` (a mismatched project, even for a member of both), (e) `workspace_pk=Apollo`, `project_pk=Hermes Plan` (a project from another workspace), (f) Dave or Carol under Apollo/Roadmap (inaccessible), or (g) a missing workspace or project ID. **Valid create scope:** Bob POSTs under `workspace_pk=Apollo`, `project_pk=Launch` → 302; exactly 1 new task, in **Launch**; none in Roadmap. |
| AC-14 | tasks/test_views | A missing `workspace_pk`, `project_pk` or task `pk` → 404, the same status and body as AC-12. |
| AC-15 | tasks/test_views | Anonymous GET of `create` and `detail` → `login?next=<path>`. Logging in as Bob → 200. Logging in as Dave → 404. |
| AC-16 | tasks/test_views | Anonymous POST `create` → exactly `reverse('accounts:login')`, nothing created. Logging in afterwards → `core:dashboard`, and the count still doesn't change. |
| AC-17 | tasks/test_views | `Client(enforce_csrf_checks=True)`, logged in as Bob, POSTs `create` without a token → 403 and nothing created. |
| AC-18 | tasks/test_views | GET `create` with `?title=X` creates nothing. A POST to `detail` → 405. |
| AC-19 | tasks/test_views, test_models | **The posted IDs can't override the URL scope:** Bob POSTs to Roadmap's create URL (`Apollo/Roadmap`) with extra `project=<Launch pk>` and `workspace=<Hermes pk>`, and again with `project=<Hermes Plan pk>`. Each time, the task is created in **Roadmap**, with none in Launch or Hermes Plan. `project` is required at the model level (`IntegrityError`). Deleting a project deletes only its own tasks (CASCADE, D-2). |
| AC-20 | tasks/test_ui; build notes; the step 11 record | On the project page (tasks section), create task and the task page: one `h1`, no skipped heading levels, a unique `<title>`, `main#main`, every SVG `aria-hidden`, new links and buttons at `min-h-11` or `.btn-*`, fields labelled and errors linked, `wrap-anywhere` on user text, tokens only, and no new `<script>` or stylesheet. The layout and target sizes come from step 11. The build notes are checked at review. |
| AC-21 | full suite | All 269 existing tests pass, **except** the two pinned-wording tests, which `test-author` updates under AC-22 (listed). No other existing assertion is changed. |
| AC-22 | projects/test_views, test_ui (updated) | The workspace page's empty state and header use "New project". The project page's back link text is "Back to Apollo" and still links to Apollo's page. |
| AC-23 | workspaces/test_mixins, projects/test_mixins, the full suite, core/test_ui | `MemberWorkspaceMixin` (a minimal view, `RequestFactory`) → 404 for a non-member and a missing ID, and sets `workspace` for a member. `MemberProjectMixin` → 404 for a project in another workspace and a missing project, and resolves the workspace **before** the project. The existing project access tests pass unchanged. Core's token check now scans `projects` and `tasks` templates. A grep-style test asserts that no `ProjectWorkspaceMixin` remains and that `for_user` is used for views only in `WorkspacePageMixin` and `MemberWorkspaceMixin`. |

**Verification** (`/build` runs these through `test-runner`, in this order):
- [x] Focused: `.venv/Scripts/python.exe manage.py test tasks projects workspaces core`
- [x] Drift: `.venv/Scripts/python.exe manage.py makemigrations --check --dry-run` → "No changes detected"
- [x] Checks: `.venv/Scripts/python.exe manage.py check` → no issues
- [x] Full suite: `.venv/Scripts/python.exe manage.py test`. All pass.
- [x] Build notes, the step 11 record (320/768/1280) and the checklist
  record are all present, with checked and unchecked items told apart.

## Risks

| Risk | Mitigation |
|---|---|
| **Cross-scope access (IDOR)** through any of the three IDs | Lookups are chained: `for_user` workspace → `self.workspace.projects` → `self.project.tasks`. No unscoped `Task` or `Project` lookup exists in any view. AC-13 tests every wrong-parent combination, including the same workspace with the wrong project. |
| Moving the mixin changes project behaviour | Step 1 runs the existing `projects` and `workspaces` suites before any task code exists. The mixin tests pin the chain. |
| A posted `project` or `workspace` moves a task | The form has neither field, and `form.instance.project` is set on the server (AC-19 test). |
| XSS through the title or description | Autoescaping, plus `linebreaksbr`, which escapes first. No `|safe` (AC-11 test). |
| **Creation order on PostgreSQL:** with two transactions at once, a lower `pk` can commit after a higher one, so a just-created task could appear one place earlier than the other's | Rare (two tasks in the same project within milliseconds), and after that the order is stable. SQLite serialises writes, so it can't happen locally. Recorded under Known limitations for the PostgreSQL step. A `created_at` column would have the same issue. |
| Wording changes break tests unexpectedly | Only the two listed tests should fail (step 10). `test-author` updates exactly those and lists them. Any other failure is treated as an app mistake. |
| The project page grows another section and breaks the step 04 page tests | The tasks section is appended after Description. The existing structure tests (one `h1`, heading order, back link) still hold. Full-suite run. |
| URL include order | The tasks include comes first, then projects, then workspaces. The patterns don't overlap anyway; the order just makes that explicit. |
| The description limit is enforced by the form only | The same accepted limitation as projects (CLAUDE.md). The only write path is `TaskForm`. |
| The browser tools aren't connected | D-1. |

## Decisions needing approval

The user answered these on 2026-10-06.

- **D-1: Visual and responsive check (step 11).** *Answer:* **(a)**.
  - Claude uses the Chrome browser tools if they're connected.
  - Otherwise `/build` stops at step 11 and gives the manual checklist.
  - The record says plainly what was user-reported and what was measured.
- **D-2: What happens to a project's tasks if the project is deleted?**
  *Answer:* **(a) `CASCADE`.** A task can't exist without its project.
- **D-3: How is the oldest-first order stored?** *Answer:* **(a)** the
  existing auto-increment primary key, `order_by('pk')`, with **no** new
  timestamp field. The PostgreSQL edge case is recorded under Risks.
- **D-4: How is AC-22's "one label" read?** *Answer:* **(a)**.
  - Links and actions that **open** the create form read "New project", in
    the workspace page header and in its empty state.
  - The form's **submit** button keeps "Create project".
  - Tasks follow the same rule: "New task" opens the form, "Create task"
    submits it.

**Spec alignment (2026-10-06):** spec 05 was reopened and re-approved with a
clarified AC-13 and AC-19.
- An existing task under the wrong parent → 404.
- Creating → 404 only when the URL's workspace and project scope is
  invalid, missing, inaccessible or mismatched.
- A create under a valid, accessible project creates the task there, and
  posted IDs are ignored.

The AC-13 and AC-19 test rows above match this.

## Files changed
Application, templates and design system (by `/build`, 2026-10-06; steps 1–10):
- **Q-35, shared access:**
  - created `workspaces/mixins.py`: `MemberWorkspaceMixin` (`dispatch` → `resolve_scope` → workspace via `for_user`, or 404; context `workspace`);
  - created `projects/mixins.py`: `MemberProjectMixin(MemberWorkspaceMixin)` (`resolve_scope`: workspace first, then `self.workspace.projects`, or 404; context `project`);
  - modified `projects/views.py`: `ProjectWorkspaceMixin` deleted and both views use `MemberWorkspaceMixin`; `ProjectDetailView` adds `tasks` to the context; Q-42 comment on `except IntegrityError`.
- modified `projects/forms.py`: Q-34 comment corrected.
- modified `projects/models.py`: Q-43 comment corrected.
- modified `projects/admin.py`, `workspaces/admin.py`: Q-44, a one-line reason for not registering.
- created the `tasks` app: `tasks/__init__.py`, `apps.py`, `migrations/__init__.py` (startapp), `tasks/admin.py` (a reason for not registering); deleted `tasks/tests.py` (stub).
- modified `config/settings.py`: `'tasks'` added after `'projects'`.
- created `tasks/models.py`: `TaskQuerySet.in_creation_order()` (`order_by('pk')`, D-3), `TaskManager`, and `Task` (`project` FK `CASCADE` with `related_name='tasks'`, D-2; `title` 200; `description` `TextField` 2000, `blank=True`; no constraints, no timestamp).
- created `tasks/migrations/0001_initial.py` (depends on `projects.0001_initial`; applied).
- created `tasks/forms.py`: `TaskForm` (`title`, `description`; labels; `autocomplete="off"`; a 5-row textarea).
- created `tasks/views.py`: `TaskCreateView` (the project comes from the URL scope, then the message and redirect) and `TaskDetailView` (GET only, `self.project.tasks`).
- created `tasks/urls.py`: `app_name='tasks'`, with `create` and `detail`.
- modified `config/urls.py`: `workspaces/<workspace_pk>/projects/<project_pk>/tasks/` → `tasks.urls`, before the projects include.
- modified `projects/templates/projects/project_detail.html`:
  - Q-40: the back link reads "Back to <workspace>", with the name in its own `wrap-anywhere` span;
  - a tasks section after Description: heading, count, "New task" when tasks exist, rows in creation order, and an empty state with its own "New task".
- modified `workspaces/templates/workspaces/workspace_detail.html`: Q-41, the empty-state action reads "New project".
- created `tasks/templates/tasks/task_form.html` and `task_detail.html`.
- created `templates/partials/icons/list-bullet.html` (Heroicons v2 outline, MIT).
- modified `design-system/project-management-system/MASTER.md`: a "Task pages (step 05)" note (the action-label rule from D-4, icon meanings, layouts, back-link wording).

Differences from the plan text:
- **Back-link markup:** the plan's "with the name still in its own `<span>`" is met as `Back to <span class="wrap-anywhere">{name}</span>`. A first attempt put "Back to" inside the name's span. That broke step 04's `test_user_text_can_wrap`, which expects an element holding exactly the name with `wrap-anywhere`, and it was corrected before handing over. The task page uses the same markup.
- *(Not a deviation; moved here as a design note at `/done`, review Q-64.)* Task rows have no leading icon. `list-bullet` is used only in the section header and the empty state, which keeps rows uncluttered. MASTER now records this.

**Existing tests after step 10:** 266 of the 269 pass. The 3 failures are exactly the two tests that pin the old "Create a project" wording, as the plan expected:
- `projects/tests/test_ui.py::test_header_action_only_when_projects_exist`;
- `projects/tests/test_views.py::test_empty_state_has_own_create_action` (2 subtests).

They go to `test-author` under AC-22.

Review fixes (`/build 05 retest`, 2026-10-06: S-5, Q-50, Q-51, Q-65 only):
- modified `tasks/views.py`, `projects/views.py`: S-5, `http_method_names = ['get', 'head', 'post', 'options']` on `TaskCreateView` and `ProjectCreateView`, so PUT, PATCH and DELETE now get 405.
- modified `design-system/project-management-system/MASTER.md`:
  - Q-50: the step 04 note now says "New project" and "Back to <workspace name>", each marked as a step 05 change;
  - Q-51: the action-label rule is scoped to projects, tasks and new item types, with the workspace wording (dashboard "Create workspace") recorded as a known exception.
- modified this plan's build notes (Q-65):
  - `pages/workspace.md` recorded as not read, and why that made no difference;
  - the single stack search explained;
  - the checklist now covers four pages, the workspace page included.
- tests: see Test results (S-5 regression tests by `test-author`).
- no template markup changed, so the UI skill workflow and the visual check weren't needed; no migration.

### UI build notes (spec 05 AC-20; plan steps 8, 11–13)

**Workflow followed:**
1. Loaded ui-ux-pro-max (2026-10-06, this build).
2. Read MASTER.md's Project adjustments, including "Project pages
   (step 04)", which override everything else. **`pages/workspace.md` was not
   read in this build**, although plan step 8 listed it. Its generated
   "1200px, responsive grid" override was already rejected in MASTER, so it
   couldn't have changed anything. *(Corrected in the review-fix round,
   review Q-65.)*
3. Ran the planned searches, plus **one** `--stack html-tailwind` search
   ("list row hover"), for the list on the project page only, and retried
   empty ones once, recording the fallbacks. The create-task and task pages
   had **no stack search**. They reuse step 04's form and detail markup
   unchanged, whose stack guidance (input sizing, textarea) was already
   searched and recorded in plan 04. *(Clarified, review Q-65.)*
4. Recorded the new patterns in MASTER's "Task pages (step 05)".

**How step 11 was done:** the Chrome browser tools weren't connected, so it
was **the user's manual check** (D-1). On 2026-10-06 the user answered "all
pass" to a checklist covering:
- (1) the project page tasks section, the empty state and the back-link
  text;
- (2) the workspace page empty-state label;
- (3) the create-task page: heading, context line, empty-title error;
- (4) the task page: back link, context line, a long title wrapping, line
  breaks or "No description";
- no sideways scrolling and a visible focus ring everywhere;
- every new target at least 24 × 24;

at **320, 768 and 1280px**. **No sizes were reported**, so the results below
are user-reported passes, not measurements. Anything that wasn't on that
list is marked **not checked**.

**Design-system rules and skill guidance for each page.** Searches are given
as query (domain) → result and effect.

| Page | MASTER rules applied | Skill searches → effect |
|---|---|---|
| Project page: tasks section | The step 04 projects-section pattern: `.card` with `aria-labelledby`, `h2` with a count `.badge`, `.btn-primary` "New task" with `plus`, full-width `min-h-11` row links, the dashed empty state, `wrap-anywhere`, tokens only; placed after the Description card | "empty state call to action" (ux) → "show helpful message and action": "No tasks yet." with its own "New task". "todo list items" (ux) → no result; retried as "list ordering" (ux) → no result. **Fallback:** spec 05's decided order (creation, oldest first), with nothing shown about it. "list item link" (ux) → no result; retried as "clickable row" (ux) → no result. **Fallback:** MASTER's step 03/04 row rules. "checklist task list" (style) → no result; retried as "minimal list" (style) → "Minimalism & Swiss Style", consistent with MASTER: a plain divided list. "list row hover" (html-tailwind) → "hover with a transition" (`motion-safe:transition-colors`); "card hover shadow" was **not applied**, because cards aren't clickable (MASTER) |
| Create task | The auth-card pattern; form-field spec; required mark on the title only; the button row (secondary Cancel, primary "Create task", stacked on mobile) | "form single field" (ux) → "inline error linked by aria-describedby", already provided by `form_field.html`. "textarea optional" (ux) → no result; retried as "optional field" (ux) → error placement and an error summary: inline errors kept; the focusable summary was **rejected** (needs JavaScript; existing accepted limit) |
| Task page | Back-link pattern ("Back to <project>", `min-h-11`); a muted location line; `h1` with `wrap-anywhere`; the Description `.card` | "breadcrumb context hierarchy" (ux) → "use breadcrumbs for 3+ levels" and "sequential headings". The task page is three levels deep, so a plain-text "<workspace> · <project>" location line was added. A **linked** breadcrumb wasn't built in this step (recorded in MASTER), and the back link is the way out. Headings run `h1` → `h2`. "long text readability" (ux) → "dark text on light backgrounds" (ink on surface, 17.85:1) and "truncate with expand", **rejected** because expanding needs JavaScript; full text in `max-w-prose` |

**Colour and typography:** no new colours or tokens. All three pages use
MASTER's tokens and type scale. The description paragraph uses
`leading-relaxed`, as on the project page.

**Target sizes (AC-20; step 11).** "Size from CSS" is what the CSS is
designed to produce; it was **not measured**. The width columns are the
user's "all pass" report.

| Target category | Where | Size from CSS (designed, not measured) | 320px | 768px | 1280px | Result |
|---|---|---|---|---|---|---|
| "New task" header button | project page | `.btn-primary`, `min-h-11` | user-reported pass | user-reported pass | user-reported pass | pass (not measured) |
| "New task" empty-state button | project page | `.btn-primary`, `min-h-11` | user-reported pass | user-reported pass | user-reported pass | pass (not measured) |
| Task row links | project page | full width, `min-h-11` | user-reported pass | user-reported pass | user-reported pass | pass (not measured) |
| Back links ("Back to <workspace>", "Back to <project>") | project page, task page | `inline-flex min-h-11` | user-reported pass | user-reported pass | user-reported pass | pass (not measured) |
| Cancel link | create task | `.btn-secondary`, `min-h-11` | user-reported pass | user-reported pass | user-reported pass | pass (not measured) |
| "Create task" button | create task | `.btn-primary`, `min-h-11` | user-reported pass | user-reported pass | user-reported pass | pass (not measured) |
| Title input and description textarea | create task | `min-h-11`; textarea `min-h-28` | user-reported pass | user-reported pass | user-reported pass | pass (not measured) |

**Pre-delivery checklist (step 12).** This is the skill's canonical
checklist plus MASTER's, applied to the **four** changed or new pages:
- the project page (tasks section);
- create task;
- the task page;
- the workspace page, where only the empty-state label changed (Q-41). It
  was on the step 11 list as item (2).

No item had a page-specific result. *(Corrected from "three pages", review
Q-65.)* "User-reported" means it was on the step 11
list. "Not checked" means it wasn't on that list and wasn't tested.

| Item | Result |
|---|---|
| *Process:* only relevant searches; empty ones retried once, with any fallback stated | pass (table above) |
| *Process:* quick-reference §1–§3 final pass | pass from the code: tokens only; shared focus ring; labels; targets designed at 44px (not measured); no images; no layout shift |
| *Process:* small phone and landscape | 320/768/1280 user-reported pass; **landscape: not checked** |
| *Process:* reduced motion | pass from the code (`motion-safe` only, plus the base rule) |
| *Process:* largest text size or zoom | **not checked** (not on the step 11 list) |
| *Process:* dark mode | N/A (not built; spec 03, OQ-1) |
| *Visual:* no emoji; one icon family | pass (Heroicons v2 outline; new `list-bullet`) |
| *Visual:* pressed state doesn't shift layout | pass from the code (colour-only states) |
| *Visual:* semantic tokens only | pass from the code (new and changed templates checked for palette classes, raw hex, `|safe` and scripts) |
| *Interaction:* hover and focus feedback | focus ring: user-reported pass. Hover: pass from the code |
| *Interaction:* disabled states; gestures | N/A |
| *Interaction:* reading order and descriptive labels | DOM order from the code: header, back link, location line, `h1`, Description, Tasks. Labels describe the action. **Visual reading order: not checked separately** |
| *Light/dark:* contrast | light: pass (existing tokens, checked by tests). Dark: N/A |
| *Layout:* no sideways scrolling; long text wraps | user-reported pass at 320/768/1280 |
| *Layout:* gutters, spacing rhythm, readable measure | pass from the code |
| *A11y:* decorative icons hidden; no icon-only controls | pass from the code |
| *A11y:* labels, hints, inline errors linked | pass from the code (`form_field.html` IDs). Empty-title error: user-reported pass |
| *A11y:* colour isn't the only indicator | pass from the code |
| *A11y:* error summary focus | not done: needs JavaScript (accepted limit) |
| *MASTER list:* `cursor-pointer`, hover transitions 150–300ms | pass from the code |

## Test results
Run on 2026-10-06 by `test-runner`. Python 3.12.10, Django 5.2.17.

| Check | Command | Result |
|---|---|---|
| Focused | `manage.py test tasks projects workspaces core` | 314/314 OK |
| Drift | `manage.py makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | No issues (0 silenced) |
| Full suite | `manage.py test` | 372/372 OK (269 existing + 103 new) |

**Tests by `test-author`** (all tagged "spec 05 AC-n"; every AC from AC-1 to AC-23 is cited):
- **New:**
  - `tasks/tests/` (`data.py` plus the models, forms, views and ui modules);
  - `workspaces/tests/test_mixins.py` and `projects/tests/test_mixins.py`;
  - the shared non-test module `core/tests/helpers.py`.
- **Existing tests whose behaviour assertions changed:** only the two AC-22 wording tests:
  - `projects/tests/test_ui.py::test_header_action_only_when_projects_exist`;
  - `projects/tests/test_views.py::test_empty_state_has_own_create_action`, which now also asserts "Create a project" is gone.

  `test-runner` checked the modified files and found nothing weakened.
- **Other existing-test edits** (step 04 deferred, AC-23):
  - **Q-46:** the helpers moved to `core/tests/helpers.py`. Core's token check now scans every local app's templates, `projects` and `tasks` included.
  - **Q-47:** `pages()` is called once per test, and the textarea test asserts on parsed tokens.
  - **Q-48:** "spec 04" prefixes added, and a docstring notes that spec 04 AC-22 is met by the full suite.
- **New AC-22 tests:** the back link reads "Back to Apollo", and the create-project label is "New project" everywhere.

**Fix rounds:** none on the application. One **test defect** round: `test-runner` found no test naming spec 05 AC-21. `test-author` added a docstring note and the test `StepFourBehaviourKeptTests.test_project_page_still_renders_step_04_content`. The re-run is green (372/372).

**Application defects:** none. One app mistake was caught **before** the hand-off, during step 10's self-check: the "Back to" markup broke a step 04 wrapping test. It was fixed to match the plan, as recorded in Files changed.

**Correction to the plan's AC-23 test row:** it said views use `for_user` only in `WorkspacePageMixin` and `MemberWorkspaceMixin`. `core/views.py` `DashboardView` also calls `for_user`, to **list** the signed-in user's own workspaces (step 02); it doesn't look anything up from the URL. The source-check test allows `DashboardView` by name (with its reason in the docstring), so any new caller still fails. The URL-scope lookup rule is unchanged.

**Manual check (D-1):** the user did step 11 by hand and reported "all pass" on 2026-10-06 (sizes not measured; landscape, text zoom and visual reading order not checked; see the build notes).

Nothing is unresolved.

Retest after the review fixes (`/build 05 retest`, 2026-10-06, run by `test-runner`):

| Check | Command | Result |
|---|---|---|
| Focused | `manage.py test tasks.tests.test_views projects.tests.test_views` | 104/104 OK |
| Drift | `manage.py makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | No issues (0 silenced) |
| Full suite | `manage.py test` | 378/378 OK (372 + 6 new S-5 tests) |

- **New tests:** `test-author` added `CreateMethodRestrictionTests` (3 tests each) to `tasks/tests/test_views.py` and `projects/tests/test_views.py`:
  - members' PUT, PATCH and DELETE (sent with a real form body) → 405, nothing created;
  - GET and POST controls still work;
  - a non-member's PUT → hidden 404, not 405, so the scope is still checked before the method.
- **No existing assertions changed.** Only the two `test_views.py` files changed, and only by appending these classes. `test-runner` confirmed that from file modification times, with the caveat that there's no git diff.
- 0 application defects and 0 fix rounds.

## Review log

### 2026-10-06: full review (security-reviewer + quality-reviewer)

**Scope:**
- the "Files changed" list above (not a git repo);
- the test files listed in Test results.

**Security: no High or Medium findings.**
- The chain is sound: `for_user` workspace → `self.workspace.projects` → `self.project.tasks`.
- `LoginRequiredNoReplayMixin` comes first everywhere, so anonymous visitors never trigger a lookup.
- Every ID change (wrong workspace, a project from another workspace, a task from a different project in the same workspace, a missing ID) gives the same 404, never a 403.
- The create scope follows the clarified AC-13. Posted `project` and `workspace` are ignored (AC-19).
- CSRF is in place; GET never creates anything.
- `linebreaksbr` and autoescaping are used, with no `|safe`, no raw SQL and no new external resources.
- The Q-35 refactor kept project access intact. S-1 to S-4 are not made worse.

**Quality:** no High findings. Every step 04 deferred item (Q-34, Q-40 to Q-44, Q-46 to Q-48) is confirmed resolved in code, with file:line evidence; Q-41's MASTER text, Q-43's wording and Q-44's import are noted below. IDs: the security finding is S-5, continuing CLAUDE.md's S-numbering after S-4. The quality reviewer numbered its findings from Q-50, and Q-49 is unused.

| ID | Sev | file:line | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| Q-50 | Medium | `design-system/project-management-system/MASTER.md:405-406`, `:414` | The step 04 "Project pages" note still says the empty state reads "Create a project" and the back link just names the workspace. Step 05 changed both, and MASTER's adjustments override everything, so a later UI step could undo Q-40/Q-41. | Update those lines, or mark them "superseded by step 05". | fixed |
| Q-51 | Medium | `MASTER.md:433-437` vs `core/templates/core/dashboard.html:12`, `:37`; `workspaces/templates/workspaces/workspace_form.html:3`, `:7` | The D-4 action-label rule is written as global ("New <thing>"), but the dashboard and workspace form still say "Create workspace" / "Create a workspace" (out of scope by spec OQ-7). The rule doesn't describe the app as it is. | Limit the rule to projects and tasks, or defer renaming the workspace labels. Record the choice in MASTER and CLAUDE.md. | fixed (rule scoped to projects and tasks; workspace wording recorded as a known exception) |
| Q-52 | Medium | `workspaces/views.py:13-20`, `workspaces/mixins.py:6-30`, `core/views.py:24` | It's not literally "one mechanism". `WorkspacePageMixin.get_queryset()` (the workspace's own pages) and the `MemberWorkspaceMixin` chain (nested resources) are two URL-scope lookup sites, and `DashboardView` is a listing-only caller. Matches the plan, but the docs must say it exactly. | At `/done`, describe exactly those sites. Optionally move `WorkspacePageMixin` into `workspaces/mixins.py` later (needs a plan). | accepted (user, 2026-10-06); CLAUDE.md wording corrected at /done |
| Q-53 | Medium | `projects/templates/projects/project_detail.html:22-51` vs `workspaces/templates/workspaces/workspace_detail.html:12-41`; back links in 3 templates | The list section (header, count, "New X", rows, empty state) is copied almost line for line, and the back link is copied three times and has already drifted (the workspace one lacks `max-w-full`/`min-w-0`). | In a later approved step, extract `partials/back_link.html` and a section-header/empty-state include. | deferred to the next UI step (user, 2026-10-06) |
| S-5 | Low | `tasks/views.py:11`; also `projects/views.py:13` | The create views accept PUT (Django's default). Not exploitable: a PUT has no form data, so the required field fails and nothing is created, and CSRF still applies. But it's a second write path if form handling changes later. | Set `http_method_names = ['get', 'head', 'post', 'options']` on both create views. | fixed |
| Q-54 | Low | `tasks/admin.py:1`, `projects/admin.py:1`, `workspaces/admin.py:1` | `from django.contrib import admin` is imported but never used. | Remove it, or keep it with the comment. Cosmetic. | deferred to step 06 (user, 2026-10-06) |
| Q-55 | Low | `workspaces/mixins.py:14-15` | The docstring says "the chain runs workspace → project → task", but `resolve_scope` stops at the project; the task comes from the view's `get_queryset()`. | Reword it. | deferred to step 06 (user, 2026-10-06) |
| Q-56 | Low | `projects/models.py:5-7` | The Q-43 comment is accurate but grammatically muddled ("it" refers to the message, but the sentence is about the constraint). | Reword it clearly. | deferred to step 06 (user, 2026-10-06) |
| Q-57 | Low | `projects/tests/test_mixins.py:225-244` | The `for_user` source check tracks only class names, though its docstring says class or function. Any new `for_user` call inside an allowed class passes. | Track (class, method) pairs, or fix the docstring. | deferred to step 06 (user, 2026-10-06) |
| Q-58 | Low | `projects/tests/test_mixins.py:283-297` | The unscoped-lookup check uses a hard-coded file list and substring matching, so it misses new apps and a comment can trip it. | Reuse `_app_python_files()` with an AST check. | deferred to step 06 (user, 2026-10-06) |
| Q-59 | Low | `projects/tests/test_mixins.py:115`, `:306-307` | A `projects` test module imports `tasks.views`, which reverses the app hierarchy in tests. | Move `SharedAccessSourceTests` to `core/tests/` or `tasks/tests/`. | deferred to step 06 (user, 2026-10-06) |
| Q-60 | Low | `tasks/tests/data.py:36-65` vs `projects/tests/data.py:23-49`; `missing_pk` in 3 places | The test data and `missing_pk` are copied three times. | `TaskTestData` extends `ProjectTestData`; move `missing_pk` to `core/tests/helpers.py`. | deferred to step 06 (user, 2026-10-06) |
| Q-61 | Low | `tasks/tests/test_ui.py:261`, `:288` | `.parent.parent.parent` depends on nesting depth, and `NEW_OR_CHANGED_TEMPLATES[-1]` depends on list order. | Use the `section_of()` helper (move it to helpers), and look the icon up by name. | deferred to step 06 (user, 2026-10-06) |
| Q-62 | Low | `tasks/templates/tasks/task_form.html:8` vs `task_detail.html:10`; `task_detail.html:3` | The location order differs: "in <project> · <workspace>" on create, "<workspace> · <project>" on detail. The task `<title>` omits the workspace. | Pick one order (workspace → project) in the next UI step, and note it in MASTER. | deferred to the next UI step (user, 2026-10-06) |
| Q-63 | Low | `task_detail.html:9-10`; `MASTER.md:454-457` | The linked breadcrumb the skill recommends for 3+ levels is deferred, but that's recorded only in MASTER. | Add it to CLAUDE.md Known limitations at `/done`. | accepted (user, 2026-10-06); breadcrumb deferral recorded in CLAUDE.md at /done |
| Q-64 | Low | plan "Differences"; `MASTER.md:445` | "Task rows have no leading icon" is listed as a deviation, but the plan never asked for one. MASTER doesn't actually say the rows have no icon. | Move it to a design note, and add "no leading icon" to MASTER. | accepted (user, 2026-10-06); plan note and MASTER corrected at /done |
| Q-65 | Low | plan build notes and checklist; plan step 8 | The build notes don't say whether `pages/workspace.md` was read. The checklist says "three changed or new pages", but the workspace page also changed (Q-41). Only the list page had a `--stack html-tailwind` search. | Record the read (or that it was skipped), say "four pages (workspace page: label only)", and explain why the other pages had no stack search. | fixed |

**For `/done`:** the quality reviewer listed CLAUDE.md text to update.
- **Apps:** add `tasks`, nested with its include first; the project page depends on tasks at runtime; imports point down the hierarchy.
- **Access pattern:** Q-52's wording; the `resolve_scope` extension rule; `form.instance.project`.
- **Templates:**
  - `list-bullet` = tasks, `check-circle` = success only;
  - the action-label rule, worded per Q-51;
  - "Back to <destination>".
- **Known limitations:**
  - remove the step 04 deferred list;
  - extend the form-only description limit to tasks;
  - the PostgreSQL concurrent-insert caveat for `pk` order;
  - the Q-63 breadcrumb deferral, and anything deferred from this review.
- **Testing:**
  - shared helpers in `core/tests/helpers.py`;
  - per-app `data.py` base classes;
  - the token check covers every app.
- **Steps landed:** step 05, 103 tests (372 in total).

**Result:** High 0 · Medium 4 · Low 13. There are no open High findings, so
the status is `reviewed`.


### 2026-10-06: recheck after review fixes (security-reviewer + quality-reviewer)

**Scope:**
- S-5, Q-50, Q-51, Q-65;
- the files under "Review fixes" in Files changed;
- the new `CreateMethodRestrictionTests`.

Each reviewer re-ran the S-5 tests (104/104 focused, and 6/6) and `manage.py check`.

**Security: no new findings.** S-5 is confirmed resolved:
- members get 405 for PUT, PATCH and DELETE;
- non-members still get the hidden 404 before the method check;
- an anonymous PUT still goes to login without `next`, so nothing can be replayed;
- CSRF is unchanged.

Optional gap: no test sends an anonymous PUT to the create views. Expected result: 302 to login, no `next`.

**Quality:** S-5, Q-50, Q-51 and Q-65 are confirmed resolved, with file:line evidence. The fixes added four Low items, numbered here after Q-65:

| ID | Sev | file:line | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| Q-66 | Low | plan step 8 (`:186-188`) | Step 8 is still ticked and still says to read `pages/workspace.md`, but the corrected build notes say it wasn't read. | Add a note to step 8 pointing to the build notes (Q-65). | accepted (user, 2026-10-06); plan step 8 annotated at /done |
| Q-67 | Low | plan, review log "For `/done`" line | It still says "103 tests (372 in total)". After the retest it's 109 new tests, 378 in total, and `/done` copies this line into CLAUDE.md. | Use "109 tests (378 in total)" at `/done`. | accepted (user, 2026-10-06); CLAUDE.md uses 109 / 378 at /done |
| Q-68 | Low | `design-system/project-management-system/MASTER.md:468-469` vs `:415-417` | The "Back links" bullet credits the project page wording to "(step 04, Q-40)", but the corrected note says step 05 made the change. Line 417 is also very long. | Change it to "(step 05, review Q-40)", and re-wrap line 417. | accepted (user, 2026-10-06); MASTER attribution corrected at /done |
| Q-69 | Low | `workspaces/views.py:33-45` | `WorkspaceCreateView` has no `http_method_names`, so it's now the only create view that still accepts PUT. This predates step 05 and isn't exploitable (same reasoning as S-5), but it's inconsistent with CLAUDE.md's POST-only rule. | Record it as a follow-up, or apply the same one-line restriction in a later approved step (outside step 05's scope). | deferred to step 06 (user, 2026-10-06) |

The plan's "Colour and typography" line still says "All three pages". That's accurate for the task pages, but reads oddly next to the four-page checklist.

**Result:** High 0 · Medium 0 · Low 4 (new). No High findings are open, so
the status is `reviewed`. Q-52 to Q-64, from the full review, are still open
for `/done`.
