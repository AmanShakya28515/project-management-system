---
step: 04
slug: projects
spec: .claude/specs/04-projects.md
status: done
created: 2026-10-06
approved: 2026-10-06
---

# Plan 04 — Projects

## Starting state (checked 2026-10-06)
- Steps 01–03 are `done`, and 189 tests pass.
- **`workspaces` app:**
  - **Models:**
    - `Workspace` uses `WorkspaceQuerySet.for_user(user)`, which filters on
      `memberships__user`.
    - `create_with_owner()` creates the workspace and the owner's membership
      together.
    - `member_list()` lists the members.
  - **Views:**
    - `WorkspacePageMixin` holds the **only** members-only `get_queryset()`
      and builds the page context: `members`, `viewer_is_owner` and
      `add_member_form`.
    - `WorkspaceDetailView` (GET only) and `AddMemberView` (POST only, shows
      the detail page again on invalid input) both use it.
  - **URLs:** `workspaces:create`, `detail`, `add_member` at `/workspaces/…`.
- **`core/mixins.py`:** `LoginRequiredNoReplayMixin`.
  - An anonymous GET or HEAD → login with `?next=`.
  - Any other anonymous request → login with **no** `next`.
- **Templates:**
  - `workspace_detail.html` has a back link to the dashboard, the `h1`
    name, a `.card` members `<section aria-labelledby="members-heading">`,
    and the owner-only "Add a member" card.
  - Forms render through `partials/form_body.html` and `form_field.html`.
  - Icons live in `templates/partials/icons/` (11 Heroicons outline).
  - The design system is `design-system/project-management-system/MASTER.md`.
    Its "Project adjustments" section overrides everything else.
- **Existing UI tests that the workspace page must keep passing**
  (`core/tests/test_ui.py`):
  - exactly **one** link to `core:dashboard` in `<main>` on the detail page;
  - the `members-heading` section keeps its count badge and its
    "Alice Owner" / "Bob Member" rows;
  - every main-area link and button has a minimum height of at least 24px;
  - templates use only tokens, with no palette classes or raw hex;
  - one `h1` and a heading order that never skips a level;
  - every SVG is `aria-hidden`.
- **Django 5.2 facts used below:**
  - ~~`ModelForm` excludes fields that already failed validation from
    `validate_constraints()`, so a `clean_name` error stops the constraint.~~
    *(Corrected at `/done`, 2026-10-06, review Q-34.)* The project constraint uses `F('workspace')`, and `workspace` isn't
    a form field, so form validation **never** runs this constraint, whatever
    `clean_name` does. `clean_name` is the only friendly check. The database
    constraint and the view's `IntegrityError` path (D-3) catch races.
  - `linebreaksbr` escapes its input when autoescaping is on, then turns line
    breaks into `<br>`.

## Approach

A new **`projects`** app owns the `Project` model, its form, views and
templates. Its URLs are **nested under the workspace**
(`/workspaces/<workspace_pk>/projects/…`, namespace `projects:`). Every
project request resolves **the user's workspace first**, through the existing
members-only queryset, and then looks the project up **inside that
workspace**. The workspace page gets a projects section through the existing
`WorkspacePageMixin`.

| Concern | Choice | Why not the obvious alternative |
|---|---|---|
| Where the code lives | A new `projects` app, registered after `workspaces` | CLAUDE.md already says `workspaces` is its own app "because projects will belong to a workspace". Tasks will later hang off projects, so projects get their own app too. `projects` may import from `workspaces` (it depends on it); `workspaces` never imports `projects` (see the workspace-page row). |
| One workspace per project (AC-19) | `Project.workspace = ForeignKey(Workspace, on_delete=CASCADE, related_name='projects')`, not null. No form or view exposes it: it is set from the URL's **already-authorised** workspace. | Setting it on the server means a user can't move a project by posting another workspace ID. There's no editing in this step, so it never changes. On `CASCADE`, see D-2. |
| Access: workspace first, then project (AC-12–AC-14) | `ProjectWorkspaceMixin.dispatch()` sets `self.workspace = get_object_or_404(Workspace.objects.for_user(request.user), pk=kwargs['workspace_pk'])`. **Views then look projects up only through `self.workspace.projects`.** The mixin sits **after** `LoginRequiredNoReplayMixin` in each view's bases, so login is checked before the workspace lookup. | A `Project.objects.get(pk=…)` followed by a check is the pattern CLAUDE.md forbids. Scoping through the member's workspace means a non-member, a missing workspace, a missing project, and a project under the **wrong** workspace ID (AC-13) all hit the same `Http404` from the same query. Nothing can leak, and there's no role check to forget. |
| Who may create (OQ-1) | Any member, so there's **no** owner check. The members-only workspace lookup is the whole permission. | The spec says any member, owner included. |
| Anonymous GET vs POST (AC-15, AC-16) | Both views use `LoginRequiredNoReplayMixin`, as in step 02. | It already gives "GET remembers the page; POST goes to login without `next`, no replay". |
| Name uniqueness (OQ-3, AC-5, AC-20) | **Three layers, as in step 02's memberships:** (1) a database `UniqueConstraint(F('workspace'), Lower('name'), name='projects_project_name_ci_unique_per_workspace')`; (2) a field-level `ProjectForm.clean_name` that checks `workspace.projects.filter(name__iexact=…)` and raises the friendly error; (3) the view's `form_valid` saves inside a short `transaction.atomic()` block, with the `except IntegrityError` **outside** that block. The block rolls back first, and the race is then shown as the **same** field error (D-3). | The form check alone loses a race between two members. Without the form check, a duplicate would surface only as an `IntegrityError` from the database. Form validation never runs this `F('workspace')` constraint *(Corrected at `/done`, 2026-10-06, review Q-34.)*. `Lower()` constraints work on SQLite and PostgreSQL. The SQLite ASCII-only case folding is the known, accepted limitation from CLAUDE.md, so tests use ASCII names. |
| Name and description rules (OQ-2, AC-3, AC-4, AC-6) | `name = CharField(max_length=100)`. `description = TextField(max_length=2000, blank=True)`. In the `ModelForm`, both fields strip spaces, so an all-space name fails as required and an all-space description saves as `''` (AC-6). `max_length` on the `TextField` becomes the form's limit, with Django's "at most N characters" error (AC-4). Labels are "Project name" and "Description (optional)". Widgets: name `autocomplete="off"`; description a `Textarea(rows=5)`. | The same mechanism as workspace names, so there's no new validation code. |
| Ordering (OQ-4, AC-7) | `ProjectQuerySet.alphabetical()` → `order_by(Lower('name'), 'pk')`. The manager is `ProjectManager.from_queryset(ProjectQuerySet)`, so `workspace.projects.alphabetical()` works through the related manager. | The business rule lives on the model (CLAUDE.md). It's the same rule as the dashboard's workspace order. |
| Workspace page integration (AC-7–AC-9) | `WorkspacePageMixin.get_context_data` adds `projects = workspace.projects.alphabetical()`, using the reverse relation. **`workspaces` doesn't import `projects`.** The template links with `{% url 'projects:create' workspace.pk %}` and `{% url 'projects:detail' workspace.pk project.pk %}`. `AddMemberView` shares the mixin, so the page still shows projects when it is redrawn after an add-member error. | One context method serves both views. Only this workspace's projects are listed, which covers AC-9 by construction. |
| Create flow (AC-1, AC-2) | `ProjectCreateView(LoginRequiredNoReplayMixin, ProjectWorkspaceMixin, CreateView)`, with `form_class = ProjectForm(workspace=self.workspace)`. `form_valid`: `form.instance.workspace = self.workspace`, atomic save, `messages.success(f'Project "{name}" was created.')`, redirect to `projects:detail`. Context: `workspace`, for the heading "New project", the subtitle "in <workspace>" and Cancel going back to the workspace page. | It's Django's standard `CreateView`, plus the scoped workspace. |
| Project page (AC-10) | `ProjectDetailView(LoginRequiredNoReplayMixin, ProjectWorkspaceMixin, DetailView)` with `get_queryset() = self.workspace.projects.all()` and `http_method_names = ['get', 'head', 'options']`. It shows a back link "← <workspace name>", the `h1` name, and a Description card with `{{ project.description|linebreaksbr }}`, or "No description" in muted text. | `linebreaksbr` keeps line breaks (AC-10) and escapes first (AC-11). No `|safe` anywhere. |
| No creator or date (OQ-5) | **No** `created_by` and no timestamp field. | Spec 04 rules out recording or showing who created a project, or when. They're added when a spec asks. |
| Admin | Not registered. | Consistent with workspaces. No admin tooling is in scope. |
| Escaping (AC-11) | Autoescaping everywhere. The success message is plain text, which `base.html` shows escaped. The `<title>` uses `{{ project.name }} · {{ workspace.name }}`. | It's the same proven path as step 02 and step 03. |

### UI (spec 04 AC-21; CLAUDE.md "Frontend and UI work")
`/build` loads the ui-ux-pro-max skill, **reads MASTER.md and its "Project
adjustments"**, then runs the per-page searches below. It applies the
existing tokens and components (`.card`, `.btn-*`, `.badge`, `.link`,
`.form-field`, icons), adds no new shared CSS unless the searches show a
real need, and records everything in the build notes.

| Page | Layout | Searches (domain) |
|---|---|---|
| **Workspace page: projects section** (new, placed **between the `h1` and the members card**, because projects are the page's main content) | A `.card` `<section aria-labelledby="projects-heading">`. The header row has `h2` "Projects", a count badge, and on the right a `.btn-primary` "New project" with the `plus` icon. Rows are full-width links (`min-h-11`, hover `bg-subtle`, focus ring) with an icon, the name (`min-w-0 wrap-anywhere`) and `chevron-right`. The **empty state** sits inside the section: an icon, "No projects yet.", one supporting line, and its own `.btn-primary` "Create a project". | `"empty state call to action"` (ux), `"section header action button"` (ux), `"list row clickable"` (ux; empty last time, so retry, then fall back), `"project list scan"` (style) |
| **Create project** | The centred `max-w-md` `.card` pattern: `h1` "New project", the muted line "in <workspace>", the form (name, description textarea), then secondary "Cancel" (→ workspace page) and primary "Create project" in the step 03 button row. | `"textarea optional field label"` (ux), `"form optional required marking"` (ux), `"textarea"` (html-tailwind) |
| **Project page** | A back link "← <workspace>" (`arrow-left`, `min-h-11`), the `h1` name (`wrap-anywhere`), then a `.card` with `h2` "Description" and the text (`whitespace` handled by `<br>`, `wrap-anywhere`, readable measure `max-w-prose`) or a muted "No description". | `"long text readability measure"` (typography or ux), `"empty value placeholder"` (ux), `"back link breadcrumb"` (ux) |

**New shared pieces (minimal):**
- one new icon partial, `clipboard-document-list` (Heroicons v2 outline,
  MIT), for project rows, so projects are told apart from workspaces'
  `folder`;
- a `.form-field textarea` rule: the existing input rule already covers
  `textarea`, so only `min-h-28` and `py-2` are added, in
  `@layer components`.

## Data model & migrations
**`projects.Project`**
- `workspace`: `ForeignKey('workspaces.Workspace', on_delete=CASCADE, related_name='projects')`
- `name`: `CharField(max_length=100)`
- `description`: `TextField(max_length=2000, blank=True)`
- `objects = ProjectManager.from_queryset(ProjectQuerySet)()`, with
  `alphabetical()` on the queryset
- `Meta.constraints`: `UniqueConstraint(F('workspace'), Lower('name'), name='projects_project_name_ci_unique_per_workspace', violation_error_message=DUPLICATE_NAME_MESSAGE)`
- `__str__` returns `name`.
- `DUPLICATE_NAME_MESSAGE = 'This workspace already has a project with that name.'`
  lives in `projects/models.py`. The form, the constraint and the view's race
  path share it (as `accounts/models.py` does for its messages).

**Migrations:**
- `projects/migrations/0001_initial.py` from `makemigrations projects`. It
  depends on `workspaces.0001_initial`.
- No changes to the other apps' models.
- No raw SQL.

## URLs, views, templates
`config/urls.py` gains
`path('workspaces/<int:workspace_pk>/projects/', include('projects.urls'))`,
**before** `path('workspaces/', include('workspaces.urls'))`.

| URL name | Path | View | Template | Access rule |
|---|---|---|---|---|
| `projects:create` | `/workspaces/<workspace_pk>/projects/new/` | `ProjectCreateView` | `projects/project_form.html` | Any member, owner included. Non-member or missing workspace → 404 (GET and POST). Anonymous GET → login with `?next=`. Anonymous POST → login without `next`, nothing created. CSRF required. A GET never creates anything. |
| `projects:detail` | `/workspaces/<workspace_pk>/projects/<pk>/` | `ProjectDetailView` (GET/HEAD/OPTIONS) | `projects/project_detail.html` | Any member. Non-member, missing workspace or project, or a project under a different workspace → the same 404. Anonymous → login with `?next=`. |
| `workspaces:detail` | (existing) | `WorkspaceDetailView` and `AddMemberView` via `WorkspacePageMixin` (`projects` added to the context) | `workspaces/workspace_detail.html` (gains a projects section) | Unchanged |

**Files:**
- `projects/__init__.py`, `apps.py`, `admin.py`, `migrations/__init__.py`
  (startapp, with no admin registration), `models.py`, `forms.py`,
  `views.py`, `urls.py`, `templates/projects/project_form.html` and
  `project_detail.html`, `migrations/0001_initial.py`.
- `config/settings.py` (`INSTALLED_APPS`), `config/urls.py`.
- `workspaces/views.py`: `WorkspacePageMixin` adds `projects`.
- `workspaces/templates/workspaces/workspace_detail.html`: the projects
  section.
- `templates/partials/icons/clipboard-document-list.html`.
- `templates/base.html`: the `.form-field textarea` rule only.
- `design-system/project-management-system/MASTER.md`: a short
  "Project pages (step 04)" note in the adjustments section (the projects
  section, the create and detail page layouts, the new icon and the textarea
  rule), so later steps keep these patterns. Changing MASTER this way is
  allowed: it's an approved step.

## Implementation steps
- [x] 1. `.venv/Scripts/python.exe manage.py startapp projects`.
  - Delete `projects/tests.py`; `test-author` creates `projects/tests/`.
  - Leave `admin.py` without registrations.
  - Add `'projects'` to `INSTALLED_APPS` after `'workspaces'`.
- [x] 2. `projects/models.py`: `DUPLICATE_NAME_MESSAGE`, `ProjectQuerySet`
  (`alphabetical`), `ProjectManager` and `Project` with the constraint.
- [x] 3. `makemigrations projects`. Check that `0001_initial.py` has the FK
  with `CASCADE`, `max_length=2000` on the description, and the
  `projects_project_name_ci_unique_per_workspace` constraint. Then `migrate`.
- [x] 4. `projects/forms.py`: `ProjectForm(ModelForm)` with `fields = ('name', 'description')`, labels, widgets, `__init__(…, workspace)` and `clean_name()` using `DUPLICATE_NAME_MESSAGE`.
- [x] 5. `projects/views.py`:
  - `ProjectWorkspaceMixin`: `dispatch` sets `self.workspace` through
    `Workspace.objects.for_user()`; `get_context_data` adds `workspace`.
  - `ProjectCreateView`: `get_form_kwargs` passes `workspace`. In
    `form_valid`:
    1. Set `form.instance.workspace = self.workspace`.
    2. Save in a short atomic block, with the `try` **outside** it:

       ```
       try:
           with transaction.atomic():
               self.object = form.save()
       except IntegrityError:
           form.add_error('name', DUPLICATE_NAME_MESSAGE)
           return self.form_invalid(form)
       ```

       The atomic block exits and rolls back before the `except` runs, so no
       query is ever made inside a broken transaction (D-3). `form_invalid`
       only renders the template from the already-loaded `self.workspace`,
       and runs no further queries in the failed block.
    3. On success: `messages.success(...)` and redirect to `projects:detail`.
  - `ProjectDetailView`: `get_queryset` returns `self.workspace.projects.all()`.

  `projects/urls.py`: `app_name = 'projects'`, with `create` and `detail`.
  In `config/urls.py`, add the nested include **before** the `workspaces/`
  include.
- [x] 6. `workspaces/views.py`: `WorkspacePageMixin.get_context_data` adds
  `projects`.
- [x] 7. **UI workflow, before writing any markup:**
  - load ui-ux-pro-max;
  - read MASTER.md (Project adjustments) and `pages/workspace.md`;
  - run the searches in the UI table, plus `--stack html-tailwind` for
    "textarea" and "list row";
  - retry empty searches once and record any fallback.
- [x] 8. Templates and assets:
  - the projects section in `workspace_detail.html`;
  - `project_form.html` and `project_detail.html`;
  - the `clipboard-document-list` icon partial;
  - the `.form-field textarea` rule in `base.html`;
  - the "Project pages (step 04)" note in MASTER.

  Keep the existing members and add-member markup unchanged, and keep
  exactly one dashboard link in `<main>` on the workspace page.
- [x] 9. **Self-check:** `manage.py check`, `makemigrations --check --dry-run`,
  then `manage.py test`. All 189 existing tests must pass. Any failure is
  treated as an application mistake first.
- [x] 10. **Visual and responsive check (D-1):** check the workspace page
  (projects and empty state, as owner and as member), create project (empty,
  with errors, with a long description) and the project page (with and
  without a description, with a long unbroken name) at 320, 768 and 1280px:
  - no sideways scrolling;
  - wrapping works;
  - focus is visible;
  - the target size of every new interactive element is checked (the
    "New project" button, the empty-state button, project row links, the
    back link, Cancel, the textarea).

  Record the results by target category.
- [x] 11. **Pre-delivery checklist** (the skill's canonical list, plus MASTER's)
  for the three changed or new pages. Record each item as pass, or N/A with a
  reason.
- [x] 12. **Build notes (AC-21):** for each page, the MASTER rules applied,
  the searches (query, domain, result and effect, or fallback), the
  checklist outcome, the target-size table, and how step 10 was done.
- [x] 13. Fill in "Files changed". Hand off to `test-author` (spec 04, this
  plan, Files changed), then `test-runner`, following `/build`.

## Test plan
Test modules (all tagged "spec 04 AC-n"):
- `projects/tests/test_models.py`: the constraint, `alphabetical`, CASCADE,
  the FK being required
- `projects/tests/test_forms.py`: `ProjectForm` validation, trimming, limits,
  per-workspace duplicates
- `projects/tests/test_views.py`: create and detail flows, the workspace
  page's projects section, access rules, the race, CSRF, escaping
- `projects/tests/test_ui.py`: the HTML-visible parts of AC-21 for the three
  pages, reusing the approach of `core/tests/test_ui.py`. A shared helper may
  be imported from `core.tests.test_ui` or copied; `test-author` decides.

Test data: Alice (owner) and Bob (member) of workspace "Apollo"; Carol is
signed in and owns workspace "Hermes"; Dave belongs to no workspace. All
names are ASCII (the SQLite case-folding limitation). Workspaces are created
with `create_with_owner` and `add_member`.

| AC | Test module | What it asserts |
|---|---|---|
| AC-1 | test_views | Alice and Bob each GET `projects:create` for Apollo → 200. The form has `name` and `description`. The page names "Apollo", and Cancel links to Apollo's `workspaces:detail`. Apollo's page has a link to `projects:create`. |
| AC-2 | test_views, test_models | Bob POSTs "Roadmap" plus a description → exactly 1 project, `workspace = Apollo`, no project in Hermes. Redirects to its `projects:detail`. Following the redirect shows the message containing "Roadmap". It also works with no description. |
| AC-3 | test_forms, test_views | `""` and `"   "` → error on `name`, and the count doesn't change. `"  Roadmap  "` is saved as "Roadmap". |
| AC-4 | test_forms, test_views | A 101-character name and a 2,001-character description each give an error on their field that mentions the limit; nothing is created; the typed values are shown again. Exactly 100 and 2,000 are accepted. |
| AC-5 | test_forms, test_views | "Roadmap" exists in Apollo. "roadmap" and "ROADMAP" in Apollo → a name-field error with `DUPLICATE_NAME_MESSAGE`, and the count doesn't change. "Roadmap" in Hermes (by Carol) → created. A direct duplicate `Project.objects.create` in Apollo → `IntegrityError`. |
| AC-6 | test_forms, test_views | A description of `"   "` → the project is created with `description == ''`. |
| AC-7 | test_views | Apollo's page as Alice and as Bob shows the projects section (`projects-heading`) with a count badge, links to each project's `detail` in case-insensitive alphabetical order ("alpha", "Beta", "gamma"), and the create link. The members and add-member sections are still present and unchanged. |
| AC-8 | test_views | Apollo with no projects → the section holds "No projects yet." **and** its own link to `projects:create`, with no project rows. |
| AC-9 | test_views | Hermes' project names never appear on Apollo's page, and the reverse. |
| AC-10 | test_views | The project page shows the name as `h1`, a description of "line1\nline2" rendered as `line1<br>line2`, a back link to Apollo's `workspaces:detail` naming "Apollo", and "No description" when it's empty. |
| AC-11 | test_views | A project named `<script>alert(1)</script>` with description `<b>x</b>\n<i>y</i>` is escaped on Apollo's page, the project page (including `<title>`) and in the creation message, while `<br>` still appears between the escaped lines. The raw tags never appear. |
| AC-12 | test_views | Dave and Carol (non-members of Apollo): GET `create`, GET `detail` of an Apollo project, and POST `create` → all 404 (not 403). The responses don't contain the project's name or description. The POST creates nothing. |
| AC-13 | test_views | Carol owns Hermes. A GET of `projects:detail` with `workspace_pk=Hermes` and `pk=<Apollo project>` → 404. Bob (a member of Apollo only) requesting an Apollo project under Hermes' ID → 404. A project's page is reachable only under its own workspace. |
| AC-14 | test_views | A missing `workspace_pk` (GET `create`, GET `detail`) and a missing project `pk` under Apollo → 404, the same status and template as AC-12. |
| AC-15 | test_views | Anonymous GET of `create` and `detail` → 302 to `login?next=<path>`. Logging in with that `next` as Bob → 200. Logging in as Dave → 404. |
| AC-16 | test_views | Anonymous POST to `create` → 302 to exactly `reverse('accounts:login')` with no `next`, and nothing created. A login afterwards lands on `core:dashboard`, and the count still doesn't change. |
| AC-17 | test_views | `Client(enforce_csrf_checks=True)`, logged in as Bob, POSTs `create` without a token → 403 and nothing created. |
| AC-18 | test_views | GET `create` with `?name=X&description=Y` → shows the form and creates nothing. A POST to `detail` → 405 and nothing created. |
| AC-19 | test_models | `workspace` is required (`IntegrityError` without it). A form POST that includes an extra `workspace=<Hermes pk>` to Apollo's create URL still creates the project in **Apollo**. |
| AC-20 | test_views, test_models | **Race path (view):** with "Roadmap" already in Apollo, patch `ProjectForm.clean_name` so its duplicate check passes, then POST "roadmap" as Bob. The test asserts:<br>- status 200, **not** 500 and not a redirect;<br>- the form's `name` field errors are exactly `[DUPLICATE_NAME_MESSAGE]`, with no non-field error;<br>- the Apollo project count is still 1 (**no extra project**);<br>- no success message;<br>- the page still shows the form with "roadmap" typed in.<br>Because the test uses `TestCase`, which wraps each test in a transaction, the assertions run **after** the request. That proves the view's atomic block rolled back cleanly: the test's own queries would raise `TransactionManagementError` if the view had kept using the broken transaction. **Model:** inside `transaction.atomic()`, a direct duplicate `Project.objects.create` (different letter case, same workspace) raises `IntegrityError`. |
| AC-21 | projects/test_ui; build notes; the step 10 manual or browser record | On all three pages: one `h1`, no skipped heading levels, a unique `<title>`, `main#main`. Templates use only tokens (no palette or raw hex). Every SVG is `aria-hidden`. New links and buttons carry `min-h-11` or `.btn-*`. Fields have labels, and errors are linked (`aria-invalid` plus `<id>_error`). User text has `wrap-anywhere`. No new `<script>` or `<link rel=stylesheet>`. The layout at 320, 768 and 1280px and the target sizes come from step 10's record. The build-notes completeness is checked at review. |
| AC-22 | full suite | All 189 existing tests pass unchanged, including `core/tests/test_ui.py`'s workspace-page checks (one dashboard link, members-section rows, minimum heights, tokens). |

**Verification** (`/build` runs these through `test-runner`, in this order):
- [x] Focused: `.venv/Scripts/python.exe manage.py test projects`
- [x] Drift: `.venv/Scripts/python.exe manage.py makemigrations --check --dry-run` → "No changes detected"
- [x] Checks: `.venv/Scripts/python.exe manage.py check` → no issues
- [x] Full suite: `.venv/Scripts/python.exe manage.py test`. Everything passes:
  the 189 existing tests plus the new ones.
- [x] Build notes, the step 10 visual and target-size record, and the
  checklist record are all present.

## Risks

| Risk | Mitigation |
|---|---|
| **Cross-workspace access (IDOR):** reading or creating a project by changing `workspace_pk` or `pk` | The workspace comes only from `Workspace.objects.for_user()`, and the project only from `self.workspace.projects`. No unscoped `Project` lookup exists in any view. AC-12, AC-13 and AC-14 have tests, including a member of a *different* workspace. |
| A posted `workspace` field moves a project | The form has no `workspace` field; `form.instance.workspace` is set on the server (AC-19 test). |
| A duplicate-name race causes a 500, or the view keeps using a broken transaction | A short atomic block around the save, with `IntegrityError` caught **outside** it, so the rollback happens before the field error is added (D-3). The AC-20 test (patched form check) asserts 200, the field error, no extra project, and that the database is still usable afterwards. |
| A non-field duplicate error alongside the field error | Form validation never runs the `F('workspace')` constraint (`workspace` isn't a form field), so it can't add a second, non-field error. A test asserts that only the field error appears. *(Corrected at `/done`, 2026-10-06, review Q-34.)* |
| XSS through the name or description, especially with line breaks | Autoescaping, plus `linebreaksbr`, which escapes before adding `<br>`. No `|safe` (AC-11 test). |
| The workspace page change breaks step 02 or step 03 tests | The projects section adds no dashboard link and no `<li>` rows ending in "Owner" or "Member", uses only tokens and `min-h` classes, and leaves the members and add-member markup untouched. Full-suite run in step 9. |
| URL ordering: `workspaces/<pk>/projects/` is shadowed by the `workspaces/` include | The nested include goes **before** `workspaces/`. The `workspaces` patterns (`new/`, `<pk>/`, `<pk>/members/add/`) wouldn't match it anyway; ordering just makes that explicit. |
| SQLite folds only ASCII letters for the case-insensitive name rule | The existing accepted limitation (CLAUDE.md). Tests use ASCII names, and PostgreSQL handles Unicode later. |
| The 2,000-character limit is enforced only by the form | Every write goes through `ProjectForm`, since there's no admin or API. Django never enforces `TextField.max_length` in the database, on **any** backend, PostgreSQL included. Database enforcement would need a `CheckConstraint` on `Length('description')`, as its own decision. Acceptable for this step. *(Corrected at `/done`, review Q-43.)* |
| The browser tools still aren't connected for the visual check | D-1 below, the same fallback as step 03. |

## Decisions needing approval

The user answered these on 2026-10-06.

- **D-1: How is the visual and responsive check (step 10) done?**
  - *Answer:* **(a)**, the same as step 03:
    - Claude uses the Chrome browser tools if they're connected.
    - Otherwise `/build` stops at step 10 and gives you the manual checklist
      covering the new pages and every new target.
    - The record says plainly which method was used, and that user-reported
      results aren't measurements.
- **D-2: What happens to a workspace's projects if the workspace is deleted?**
  - *Answer:* **(a) `CASCADE`.** A project can't exist on its own without
    its workspace (AC-19). Nothing deletes workspaces today, because
    workspace owners are protected (step 02, D-1).
- **D-3: Duplicate-race handling (user clarification).**
  - `ProjectCreateView` catches `IntegrityError` **outside** a short
    `transaction.atomic()` block around the save. The block exits and rolls
    back first; only then does the view add `DUPLICATE_NAME_MESSAGE` to the
    `name` field and return the invalid form.
  - It never catches and carries on using the database while still inside
    the broken atomic transaction (implementation step 5; AC-20 test).

## Files changed
Application, templates and design system (by `/build`, 2026-10-06; steps 1–9):
- created `projects/__init__.py`, `projects/apps.py`, `projects/admin.py`, `projects/migrations/__init__.py` (startapp; `admin.py` registers nothing)
- deleted `projects/tests.py` (startapp stub; `test-author` creates `projects/tests/`)
- modified `config/settings.py`: `'projects'` added to `INSTALLED_APPS` after `'workspaces'`
- created `projects/models.py`:
  - `DUPLICATE_NAME_MESSAGE`;
  - `ProjectQuerySet.alphabetical()` and `ProjectManager`;
  - `Project`: `workspace` FK with `CASCADE` and `related_name='projects'`; `name` max 100; `description` `TextField` max 2000, `blank=True`;
  - `UniqueConstraint(F('workspace'), Lower('name'))`, named `projects_project_name_ci_unique_per_workspace`.
- created `projects/migrations/0001_initial.py` (depends on `workspaces.0001_initial`; applied)
- created `projects/forms.py`: `ProjectForm` (`name` and `description`, labels, `autocomplete="off"`, a 5-row textarea, a `workspace` keyword argument, a `clean_name` per-workspace case-insensitive duplicate check)
- modified `projects/views.py` (startapp stub replaced):
  - `ProjectWorkspaceMixin`: `dispatch` resolves `self.workspace` through `Workspace.objects.for_user()`, or 404.
  - `ProjectCreateView`: atomic save, with `IntegrityError` caught **outside** the block (D-3), then the success message and redirect.
  - `ProjectDetailView`: GET only, queryset `self.workspace.projects.all()`.
- created `projects/urls.py`: `app_name='projects'`, with `create` (`new/`) and `detail` (`<int:pk>/`)
- modified `config/urls.py`: `workspaces/<int:workspace_pk>/projects/` → `projects.urls`, placed before `workspaces/`
- modified `workspaces/views.py`: `WorkspacePageMixin.get_context_data` adds `projects = workspace.projects.alphabetical()`
- modified `workspaces/templates/workspaces/workspace_detail.html`: a projects section (heading, count, "New project" when projects exist, row links, an empty state with its own "Create a project"), placed before the members card. The members and add-member markup is unchanged.
- created `projects/templates/projects/project_form.html` and `project_detail.html`
- created `templates/partials/icons/clipboard-document-list.html` (Heroicons v2 outline, MIT)
- modified `templates/base.html`: `.form-field textarea { @apply min-h-28 py-2; }` in `@layer components`
- modified `design-system/project-management-system/MASTER.md`: a "Project pages (step 04)" subsection in the Project adjustments

Differences from the plan text:
- **"New project" header button:** it shows only when the workspace has projects. In the empty state, the empty panel's own "Create a project" is the action, so the page never shows two identical create buttons. AC-7 and AC-8 are both still met.

**Existing tests:** all 189 still pass with no test changes (step 9).

### UI build notes (spec 04 AC-21; plan steps 7, 10–12)

**Workflow followed:**
1. Loaded ui-ux-pro-max.
2. Read MASTER.md, whose "Project adjustments" override everything, and
   `pages/workspace.md`. The page file's 1200px/grid override was already
   rejected in MASTER; one width is kept.
3. Ran the planned searches, then retried the empty or off-topic ones once.
4. Recorded the new patterns in MASTER's "Project pages (step 04)".

**How step 10 is done:** the Chrome browser tools weren't connected, so the
visual and responsive check was **the user's manual check** (D-1). The user
reported **"all pass"** on 2026-10-06 for every page at 320, 768 and 1280px
and every new target category. **No individual sizes were reported**, so the
rows below confirm a pass, not a measurement.

**Design-system rules and skill guidance for each page.** Searches are given
as query (domain) → result and effect.

| Page | MASTER rules applied | Skill searches → effect |
|---|---|---|
| Workspace page: projects section | `.card` section with `aria-labelledby`; `h2` with a count `.badge`; `.btn-primary` with `plus`; full-width row links `min-h-11`, hover `bg-subtle`, `motion-safe` 150ms; the dashboard's empty-state panel; `wrap-anywhere` on names; tokens only | "empty state call to action" (ux) → "show helpful message and action": "No projects yet." with its own "Create a project". "section header action button" (ux) → off-topic (back button, active state); retried as "primary action placement" (ux) → off-topic (error placement). **Fallback** to MASTER's existing dashboard header pattern (title left, primary action right). "list row clickable" (ux) → no result; retried as "list item link" (ux) → no result. **Fallback** to step 03's general rules: a full-row link, 44px minimum, hover background, focus ring. "project list scan" (style) → no result; retried as "minimal list" (style) → "Minimalism & Swiss Style", consistent with MASTER: a plain divided list, no cards per row. "hover state" (html-tailwind) → hover with a transition, applied as `motion-safe:transition-colors` |
| Create project | The auth-card pattern (`max-w-md` `.card`, `h1` plus a muted line); form-field spec; required mark on the name only; the button row (secondary Cancel, primary Create, stacked on mobile) | "textarea optional field label" (ux) → "inline error connected with aria-describedby", already provided by `form_field.html`. "form optional required marking" (ux) → "use an asterisk or (required) text": the asterisk on the name, plus "(optional)" in the description label. "textarea" (html-tailwind) → no result; retried as "input sizing" (html-tailwind) → "consistent input heights": the textarea keeps the field rule and only adds `min-h-28 py-2` |
| Project page | Back-link pattern (`arrow-left`, `min-h-11`); `h1` with `wrap-anywhere`; `.card` with `h2`; tokens | "long text readability measure" (ux) → "darker text on light backgrounds" (ink on surface, 17.85:1) and "truncate with ellipsis and expand", **rejected** because expanding needs JavaScript; the full text wraps inside `max-w-prose`. "empty value placeholder" (ux) → "show a helpful message": a muted "No description". "back link breadcrumb" (ux) → "preserve navigation history": a plain link to the workspace page, no history manipulation |

**Colour and typography:** no new colours or tokens. Every page uses
MASTER's tokens and type scale; the only new element style is the textarea
height. The description paragraph uses `leading-relaxed` (1.625), MASTER's
body-copy line height for longer text.

**Target sizes (AC-21; step 10).** "Size from CSS" is what the CSS is
designed to produce; it was **not measured**. The 320px and 1280px columns
come from the user's manual check, reported as "all pass" on 2026-10-06
(not measured).

| Target category | Where | Size from CSS (designed, not measured) | 320px | 1280px | Result or exception |
|---|---|---|---|---|---|
| "New project" button | workspace page header | `.btn-primary`, `min-h-11` (44px) | user-reported pass | user-reported pass | pass |
| "Create a project" button | workspace page empty state | `.btn-primary`, `min-h-11` | user-reported pass | user-reported pass | pass |
| Project row links | workspace page | full width, `min-h-11` | user-reported pass | user-reported pass | pass |
| Back link to the workspace | project page | `inline-flex min-h-11` | user-reported pass | user-reported pass | pass |
| Cancel link | create project | `.btn-secondary`, `min-h-11` | user-reported pass | user-reported pass | pass |
| "Create project" button | create project | `.btn-primary`, `min-h-11` | user-reported pass | user-reported pass | pass |
| Name input and description textarea | create project | `min-h-11`; textarea `min-h-28` | user-reported pass | user-reported pass | pass |

*Corrections at `/done` (2026-10-06):*
- **Q-38:** the user's "all pass" covered **768px** as well; this table only shows the 320 and 1280px columns.
- **Q-37:**
  - The planned "list row" (html-tailwind) search was **not run**. "hover state" (html-tailwind) was run in its place, with no recorded reason.
  - The off-topic "long text readability measure" (ux) result was **not retried**. Its effective fallback was MASTER's existing rule: ink on surface, with `max-w-prose` for a readable line length.

**Pre-delivery checklist (step 11).** The skill's canonical checklist plus
MASTER's, applied to all three changed or new pages. No item had a
page-specific result.

| Item | Result |
|---|---|
| *Process:* only relevant searches; empty ones retried once, with any fallback stated | pass (table above) |
| *Process:* quick-reference §1–§3 final pass (accessibility, touch, performance) | pass: tokens only; keyboard and focus via the shared rules; labels; 44px targets (designed, not measured); no images; no layout shift |
| *Process:* small phone and landscape | pass: user manual check at 320/768/1280px, reported "all pass" on 2026-10-06 |
| *Process:* reduced motion; largest text size | reduced motion: pass (`motion-safe` only, plus the base rule). Text scaling: **not checked** (not on the step 10 list given to the user) *(corrected at `/done`, review Q-36)* |
| *Process:* dark mode | N/A (not built; spec 03, OQ-1) |
| *Visual:* no emoji; one icon family | pass (Heroicons v2 outline; new `clipboard-document-list`) |
| *Visual:* pressed state doesn't shift layout | pass (colour-only states) |
| *Visual:* semantic tokens only | pass (grep: no palette classes, no raw hex, no `|safe`, no scripts in the new or changed templates) |
| *Interaction:* hover and focus feedback, shared timing | pass (150ms `motion-safe`, shared focus ring) |
| *Interaction:* disabled states; gestures | N/A |
| *Interaction:* reading order and descriptive labels | pass from the DOM: header, then main (projects, members, add member); button text says what it does. Visual order: **not checked separately** (not on the step 10 list) *(corrected at `/done`, review Q-36)* |
| *Light/dark:* text contrast ≥ 4.5:1, boundaries ≥ 3:1 | light: pass (existing tokens, checked by `core/tests/test_ui.py`). Dark: N/A |
| *Layout:* no fixed or sticky bars; gutters; spacing rhythm; readable measure | pass (`max-w-prose` on the description; shared gutters) |
| *Layout:* 320/768/1280, no sideways scrolling | pass: user manual check at 320/768/1280px, reported "all pass" on 2026-10-06 |
| *A11y:* decorative icons hidden; no icon-only controls | pass (every icon is `aria-hidden`, next to visible text) |
| *A11y:* labels, hints, inline errors linked | pass (`form_field.html` IDs; `aria-invalid` styling) |
| *A11y:* colour isn't the only indicator | pass (text labels and error text with icons) |
| *A11y:* error summary focus | not done: needs JavaScript (accepted step 03 limit) |
| *MASTER list:* `cursor-pointer`, hover transitions 150–300ms | pass |

## Test results
Run on 2026-10-06 by `test-runner`. Python 3.12.10, Django 5.2.17.

| Check | Command | Result |
|---|---|---|
| Focused | `manage.py test projects` | 80/80 OK |
| Drift | `manage.py makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | No issues (0 silenced) |
| Full suite | `manage.py test` | 269/269 OK (189 existing + 80 new) |

- **Tests written:** `test-author` wrote `projects/tests/` (`data.py` plus the models, forms, views and ui modules), 80 tests tagged "spec 04 AC-n". Every AC from AC-1 to AC-21 is cited; AC-22 is covered by the full suite.
- **Defects:** none. There were 0 fix rounds. Three failures on test-author's first run were mistakes in its own tests, which it fixed.
- **Existing tests:** none changed (checked by modification time; there's no git).
- **AC-20 race test:** with `clean_name` patched, the test asserts status 200, the name errors are exactly `[DUPLICATE_NAME_MESSAGE]`, there's no non-field error, no extra project and no success message, and the typed values are shown again. Further ORM reads and writes afterwards prove the transaction is still usable.
- **Correction to the plan's Approach and Risks text (reported by `test-author`):**
  - The project constraint uses `F('workspace')`, and `workspace` isn't a form field. Django's form validation therefore **never** runs that constraint, whether or not `clean_name` raised an error. The plan's reasoning ("excluded because the field already failed") doesn't apply here.
  - The behaviour is still as intended. The field-level `clean_name` gives the friendly error, and the database constraint plus the view's `IntegrityError` path (D-3) catch the race. That is also why the patched race test really reaches the database path.
- **Manual check (D-1):** the browser tools weren't connected, so the user did step 10 by hand and reported "all pass" on 2026-10-06 (sizes not measured). Nothing is unresolved.

## Review log

### 2026-10-06: full review (security-reviewer + quality-reviewer)

Scope: the "Files changed" list above (not a git repo).

**Security: no findings at any severity.**
- Every project lookup goes through `Workspace.objects.for_user()`, then `self.workspace.projects`.
- The login check runs before the workspace lookup.
- Non-member, wrong-workspace and missing-ID requests all get the same 404, including for HEAD and OPTIONS.
- A posted `workspace` is ignored.
- CSRF is in place, and a GET never creates anything.
- `linebreaksbr` escapes the description, and there's no `|safe`.
- D-3's atomic block rolls back before the error is added, so nothing uses a broken transaction.

Two notes for later steps, not findings:
- the broad `except IntegrityError` (see Q-42);
- a future edit view or admin registration will need its own length and duplicate checks.

**Quality.** Finding IDs continue after step 03's Q-32. The orchestrator confirmed two of them by reading the files:
- Q-34: the `forms.py:34-35` comment.
- Q-36: checklist rows claiming user-checked text scaling and visual order, which weren't on the step 10 list. This was the orchestrator's own error, made when the pending rows were replaced.

| ID | Sev | file:line | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| Q-33 | Medium | `workspaces/templates/workspaces/workspace_detail.html:19`; plan UI table; spec OQ-1 | **A deviation from the approved spec, decided by `/build`:** the header "New project" button only shows when projects exist. OQ-1 and the plan said the action appears in the section header **and** in the empty state. It's recorded under "Differences from the plan text" and AC-7 and AC-8 are still met, but the user never accepted it. | The user either accepts the deviation explicitly, or the header button is shown in both states. | accepted by the user at /done, 2026-10-06 (one create button at a time) |
| Q-34 | Medium | `projects/forms.py:34-35`; plan Starting state `:49-52`, Approach `:73`, Risks `:288` | The comment and the plan's reasoning are wrong. Form validation **never** runs the `F('workspace')` constraint, because `workspace` isn't a form field; it isn't that "the field error stops it". "The constraint alone shows a generic non-field error" is also wrong: without the form check, a duplicate surfaces as an `IntegrityError`, which the view handles. The correction only appears in Test results. | Rewrite the comment (form validation never runs this constraint, so `clean_name` is the only friendly check, and the database constraint plus the view's `IntegrityError` path catch races). Fix the three plan passages or point them to the correction. | accepted (user, 2026-10-06); plan text corrected at /done; forms.py comment fix deferred to step 05 |
| Q-35 | Medium | `projects/views.py:13-31` vs `workspaces/views.py:13-20`; CLAUDE.md access pattern | There are now two members-only workspace lookups with different shapes. `ProjectWorkspaceMixin` is generic ("resolve the URL's workspace for a member") but has a project-specific name and lives in `projects`, so tasks would have to import it from projects or copy it. CLAUDE.md still says `WorkspacePageMixin.get_queryset()` is "the only place". | Before or at step 05, move it to `workspaces/mixins.py` (e.g. `MemberWorkspaceMixin`, keeping the MRO-order docstring) and document it as the nested-resource pattern. At minimum, record it in CLAUDE.md at `/done` as the second sanctioned lookup site. | deferred to step 05 (user, 2026-10-06): move to workspaces as a shared mixin before tasks copy it |
| Q-36 | Medium | plan checklist rows `:402`, `:404`, `:411`; step 10 list `:209-218` | **The build notes overstate the evidence:** "Text scaling: pass (user manual check)" and "Visual order: pass (user manual check)" weren't on the step 10 list the user was given. The §1–§3 row states "44px targets" without the "designed, not measured" caveat. | Mark those cells "not checked (not on the step 10 list)", or confirm with the user. Add "(designed, not measured)" to the 44px claim. | accepted (user, 2026-10-06); checklist corrected at /done |
| Q-37 | Low | plan build notes `:371`, `:373` vs step 7 `:195` | The planned "list row" (html-tailwind) search isn't recorded, and the unplanned "hover state" search is recorded without saying why it replaced it. The off-topic "long text readability measure" result wasn't retried. | Record the search or the reason for swapping it, and record a retry or fallback for the readability search. | accepted (user, 2026-10-06); recorded at /done |
| Q-38 | Low | plan target table `:385-393` | It has 320px and 1280px columns, but step 10 covered 768px too. | Add a 768px "user-reported pass" column. | accepted (user, 2026-10-06); 768px noted at /done |
| Q-39 | Low | plan "Differences" `:346` | "Back-link text" is listed as a deviation, but the plan already specified it. | Remove that bullet. | accepted (user, 2026-10-06); bullet removed at /done |
| Q-40 | Low | `projects/templates/projects/project_detail.html:8` | The back link's visible and accessible name is just the workspace name ("Apollo"). The workspace page's back link says "Back to dashboard". | Use "Back to {{ workspace.name }}". | deferred to step 05 (user, 2026-10-06) |
| Q-41 | Low | `workspace_detail.html:19`, `:38`; `project_form.html:7`, `:14` | The wording varies: "New project" (header and `h1`), "Create a project" (empty state), "Create project" (submit). The dashboard uses one label ("Create workspace") in both places. | Pick one label for the action. | deferred to step 05 (user, 2026-10-06) |
| Q-42 | Low | `projects/views.py:53` | `except IntegrityError` treats **any** integrity error as a duplicate name. The only cause today is the name constraint. | Add a one-line comment that the only expected cause is the name constraint, so a later step that adds fields revisits it. | deferred to step 05 (user, 2026-10-06) |
| Q-43 | Low | `projects/models.py:5-6`; plan Risks `:293` | (a) The comment implies the constraint's message is shown to users. In practice it only appears through `full_clean()`. (b) The plan says the 2,000-character limit is "noted for PostgreSQL", but Django never enforces `TextField.max_length` in the database on **any** backend. | Reword the comment, and correct the Risks text. Database enforcement would need a `CheckConstraint(Length(...))`, as its own decision. | accepted (user, 2026-10-06); plan Risks corrected at /done; models.py comment fix deferred to step 05 |
| Q-44 | Low | `projects/admin.py:3` | The startapp stub comment "Register your models here." reads like unfinished work, but not registering is deliberate. | Replace it with a one-line reason. | deferred to step 05 (user, 2026-10-06) |
| Q-45 | Low | `workspaces/views.py:26` | `workspaces` now depends on `projects` at runtime through the reverse accessor and `alphabetical()`. CLAUDE.md's import-direction rule doesn't describe this. | No code change. Record the dependency in CLAUDE.md at `/done`. | deferred to step 05 (user, 2026-10-06); dependency recorded in CLAUDE.md at /done |
| Q-46 | Low | `projects/tests/test_ui.py:20-30`, `:37-42`; `core/tests/test_ui.py:475` | The projects UI tests import helpers from another app's test module and copy its colour regexes. Core's global token check hard-codes `('accounts', 'core', 'workspaces')`, so it never scans `projects` templates. | In a later approved step, move the shared helpers to a non-test module and make the core check loop over every app. | deferred to step 05 (user, 2026-10-06) |
| Q-47 | Low | `projects/tests/test_ui.py:73-85`, `:146-148`, `:199` | `pages()` is called inside a loop (21 requests in one test). The textarea test matches the exact CSS string. | Call `pages()` once per test, and assert on `component_rules()` tokens. | deferred to step 05 (user, 2026-10-06) |
| Q-48 | Low | `projects/tests/test_views.py` divider comments; `test_forms.py:16`; plan `:431` | Some section comments cite "AC-n" without the "spec 04" prefix (every docstring has it). No test names AC-22, which is a suite-level criterion met by the full run. | Add the prefix, and record that AC-22 is met by the full suite, or name it in a docstring. | deferred to step 05 (user, 2026-10-06) |

**For `/done`:** the quality reviewer listed CLAUDE.md text to update.
- **Apps:** add `projects` and its nesting.
- **The workspaces → projects runtime dependency** (Q-45).
- **The access pattern:**
  - add the nested-resource rule and where the mixin lives (Q-35);
  - the Conventions example `Project.objects.for_user` should become `self.workspace.projects`.
- **Data rules:**
  - per-workspace unique names, with D-3;
  - form validation never runs `F()`-based constraints (Q-34);
  - CASCADE; no admin registration.
- **Templates:**
  - the textarea rule;
  - the icon meaning (projects vs workspaces);
  - descriptions via `linebreaksbr` in `max-w-prose`;
  - maybe rename MASTER's "Project adjustments (step 03)" heading.
- **Known limitations:** the description limit is enforced by the form only (Q-43).
- **Testing:** the shared `data.py` pattern and the `core.tests.test_ui` helper imports (Q-46).
- **Steps landed:** step 04, 80 tests (269 in total).

**Result:** High 0 · Medium 4 · Low 12. There are no open High findings, so
the status is `reviewed`. **Q-33 needs an explicit user decision**
(accept the deviation, or fix it).
