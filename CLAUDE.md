# CLAUDE.md

Guidance for Claude Code in this repository. This file records **why** decisions
were made, not just what they are. If a rule here looks wrong, raise it with the
user. Do not quietly work around it, and do not reopen a settled choice in a spec
or plan unless the user asks.

---

## What this project is

A web-based Project Management System. Teams create projects, assign tasks,
track progress, manage members and collaborate. It has two goals, in this order:

1. Build it with a clean, spec-driven, approval-gated workflow.
2. Later, use it as a hands-on DevOps learning project (Docker, CI/CD,
   monitoring, Kubernetes).

**Why the order matters:** the DevOps phases need a real, working, well-tested
app to deploy. So the app stays simple and conventional now, and nothing
infrastructure-shaped is added early. Each DevOps tool arrives later as its own
approved step, so we learn what it changes.

---

## Common commands

Development is on **Windows**. Always use the virtualenv interpreter explicitly.
Never call bare `python` or `pip`, because a global Python can silently differ
from the project's.

| Purpose | PowerShell | Bash tool (Git Bash) |
|---|---|---|
| Interpreter | `.\.venv\Scripts\python.exe` | `.venv/Scripts/python.exe` |
| Dev server | `.\.venv\Scripts\python.exe manage.py runserver` | `.venv/Scripts/python.exe manage.py runserver` |
| Full test suite | `.\.venv\Scripts\python.exe manage.py test` | `.venv/Scripts/python.exe manage.py test` |
| Focused tests | `.\.venv\Scripts\python.exe manage.py test <app>.tests.<module>` | same, with `/` paths |
| System checks | `.\.venv\Scripts\python.exe manage.py check` | `.venv/Scripts/python.exe manage.py check` |
| Migration drift | `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` | same |
| Apply migrations | `.\.venv\Scripts\python.exe manage.py migrate` | same |
| Install deps | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` | same |

**Standard verification order:** focused tests, then migration drift, then
`check`, then the full suite. This runs the cheapest, most specific feedback
first. Drift comes before the full suite because a missing migration makes test
failures misleading.

**Docker (step 08):** the commands are PowerShell-first, and Docker
Desktop must be running. In the Bash tool (Git Bash), MSYS rewrites
container paths such as `/data` and `/app`, so prefix a command that passes
one with `MSYS_NO_PATHCONV=1`. The port is published on `127.0.0.1` only. `README.md` has the full list and explains the
concepts.

| Purpose | Command |
|---|---|
| Build / start / stop | `docker compose build` / `docker compose up -d` / `docker compose down` |
| Logs | `docker compose logs -f web` |
| Django command in the container | `docker compose exec web python manage.py <migrate\|check\|test>` |
| Shell in the container | `docker compose exec web bash` |
| PostgreSQL shell | `docker compose exec db psql -U pms -d pms` |
| Reset the container database | `docker compose down -v` |

There is no linter or formatter yet, on purpose (see Stack constraints).

---

## Feature workflow

Every change goes through five stages: **SPEC → PLAN → BUILD & VERIFY →
REVIEW → DONE**. A **gate** is an explicit human approval. Claude never
approves its own spec or plan, and never moves past a gate on its own.

| # | Stage | Command | Output | Gate to leave the stage |
|---|---|---|---|---|
| 1 | Spec | `/spec` | `.claude/specs/NN-slug.md` | User runs `/spec NN approve` |
| 2 | Plan | `/plan` | `.claude/plans/NN-slug.md` | User runs `/plan NN approve` |
| 3 | Build & Verify | `/build` | App code, migrations, tests, and the verification run in the standard order (see Common commands), all done directly by the main build | Everything green, or the user accepts the failures |
| 4 | Review | `/review` | One concise review covering correctness, security and access control, data integrity and important maintainability issues, logged in the plan | User decides which findings to fix (see Review findings) |
| 5 | Done | `/done` | Spec and plan marked done; CLAUDE.md architecture and history updated where needed | — |

**From step 06 onward** this five-stage, token-efficient workflow applies.
Steps 01–05 used the earlier six-stage workflow, with mandatory test,
review and runner agents. Their records stay as they are; don't rewrite
them.

**Status lifecycle**, stored in the spec's and plan's front-matter `status:` field:

- Spec: `draft` → `approved` → `done`
- Plan: `draft` → `approved` → `built` → `reviewed` → `done`

Each command checks the status it needs first and refuses with a clear message
if the status is wrong.

**Numbering:** steps are two-digit and sequential (`01`, `02`, …). The spec and
the plan share the same `NN-slug` filename.

**Why this workflow:**
- Specs hold *what* and *why*, and plans hold *how*. Keeping them apart stops
  the implementation details from being debated before the goal is agreed.
- Acceptance criteria are numbered (`AC-1`, `AC-2`, …) so tests, plan steps and
  review findings can point to them. "Done" is then something you can check,
  not a matter of opinion.
- Tests are derived from the **spec**, not the code. Tests written from the
  code tend to repeat the code's bugs.
- Small, numbered steps line up well with the later CI/CD phase, where each
  step becomes a pipeline run.

**Finding "the diff":** the project is a Git repository (branch `main`)
since step 08. Reviewers use `git diff` / `git status` and cross-check the
plan's **"Files changed"** section, which `/build` keeps up to date. Claude
commits only when the user asks.

### Token-efficient execution
Optimise for correctness, learning value and progress per token. The aim is
to keep moving toward the DevOps stages (Docker → PostgreSQL → CI/CD →
deployment → monitoring/Grafana → Kubernetes), not to add process ceremony.
- **Specs stay concise:**
  - goal and context;
  - user-visible behaviour;
  - numbered acceptance criteria;
  - out-of-scope items;
  - only open questions that matter.

  Where CLAUDE.md already covers authentication, access control, UI, testing
  or architecture, point to it instead of restating it.
- **Plans stay concise:**
  - key technical decisions;
  - the real files and components affected;
  - migrations and data changes;
  - meaningful risks;
  - the test and verification approach.

  Don't re-explain settled architecture.
- **Reuse established patterns** rather than rediscovering or re-documenting
  them.
- **Don't paste large parts of CLAUDE.md, a spec or a plan** into agent
  prompts or reports.
- **Prefer one implementation and verification pass**, with `/build` running
  the tests and checks itself, and one concise `/review`.
- **Don't run review → fix → recheck cycles for minor clean-up.** After a fix
  round, re-run only what the changed area needs, plus the full suite when
  appropriate.
- **Token efficiency means less repetition, not less correctness.** Never
  change application architecture just to save tokens.

### Sub-agents
Sub-agents are optional tools, not workflow stages. Use one only when an
independent context really improves correctness, and never run several just
because they exist.
- **`test-author`:** for complex or security-sensitive acceptance criteria,
  where independent test design adds real value. Otherwise `/build` writes
  the tests, still from the approved spec, not by copying the
  implementation.
- **`test-runner`:** normally unnecessary, since `/build` runs the
  verification commands itself. Use it only when independent verification
  matters.
- **`security-reviewer`:** for changes touching authentication,
  authorization or access control, permissions, secrets, file uploads,
  payments, external APIs, sensitive data, or production security settings.
  Not automatically for every feature.
- **`quality-reviewer`:** for substantial architecture changes, major
  refactors or technically risky work. Not for small features or simple UI
  changes.

### Review findings
Prioritise by impact.
- **High:** normally fixed before the step closes.
- **Medium:** fixed when it materially affects correctness, security, access
  control, data integrity, accessibility, architecture or future
  maintainability.
- **Low:** accepted by default, unless it affects security, access control,
  data integrity, accessibility or future architecture.

Never reopen a build or start another review cycle only for cosmetic
clean-up, documentation wording, duplicated test data, minor comments,
test-structure preferences or optional refactors. Low findings that may
matter later go into Known limitations and are handled the next time that
area changes.

---

## Stack constraints

### Use:
- **Python 3.12.** A stable release, fully supported by Django 5.2. It will
  match a future `python:3.12-slim` Docker image. It must be installed
  separately on the dev machine and is not installed yet as of 2026-10-01; a
  3.13 or 3.11 interpreter is **not** a substitute.
- **Django 5.2 LTS.** Batteries included: auth, admin, ORM, migrations, forms,
  CSRF and a test runner, all without extra dependencies. Pin with
  `Django~=5.2.0` in `requirements.txt`. *Why 5.2 and not the originally
  chosen 5.1:* 5.1 stopped receiving security fixes in December 2025. 5.2 is
  the long-term-support release, with security support until April 2028.
  Decided in plan 01, D-2.
- **SQLite** for the host `.venv` workflow, and **PostgreSQL 17** in Docker
  Compose (since step 09). SQLite needs no server, and the database is a
  single file. **Write only ORM code that works on any database**, because
  the same code and tests run on both. No raw SQL, and nothing
  that depends on SQLite quirks.
  - *Known SQLite limitation (accepted, plan 01 D-3):* SQLite's `LOWER()` and
    case-insensitive `LIKE`/`iexact` only fold **ASCII** letters. Usernames
    may contain Unicode letters, so on SQLite "Ä" and "ä" count as
    **different** for the case-insensitive username and email rules. On
    PostgreSQL they count as the same. This is local-development behaviour
    only. Don't "fix" it by restricting usernames to ASCII; that would be a
    product change that needs its own spec.
- **Django templates + Tailwind CSS via the Play CDN `<script>` tag.** No Node
  and no build step, so the toolchain stays pure Python. Known trade-off: the
  Play CDN is not meant for production. We accept that for now and will revisit
  it in a DevOps step.
- **Django's built-in test framework** (`django.test.TestCase`, `manage.py test`).
  Nothing to install, and it is what the docs and the test runner already use.
- **`requirements.txt`** for dependencies. It is the simplest thing that Docker
  and CI can consume later.

### Do NOT add without being asked:
- React, Vue, HTMX, Alpine, or any JS framework or bundler; Node/npm of any kind
- Kubernetes manifests, CI config, or Docker changes beyond step 08's
  development `Dockerfile`/`compose.yaml` (e.g. production images, extra
  services). Docker and Compose exist since step 08; changing them needs its
  own step.
- MySQL, Redis, Celery, or any message broker or cache server (PostgreSQL
  exists since step 09)
- Django REST Framework or any API layer
- pytest, factory_boy, coverage, linters (ruff/flake8), formatters (black),
  pre-commit, type checkers
- Third-party Django apps (allauth, crispy-forms, debug-toolbar, …)
- Poetry, pipenv, uv, or anything that replaces `requirements.txt`

**Why so strict:** every dependency here should be a deliberate, approved step
with its own spec. That is the whole learning value of the DevOps phases. If a
feature seems to need one of these, say so in the spec's "Open questions" and
let the user decide.

---

## Architecture

*`/done` adds to this as each step lands. Record only what was actually built,
plus the reasoning behind any structural choice.*

### Project layout (confirmed in step 01)
- The Django project package is `config/` (settings, root urls, wsgi/asgi).
  Apps live at the repo root.
- Settings read `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` and `DJANGO_ALLOWED_HOSTS`
  from the environment, with local-only defaults (an insecure-labelled key,
  DEBUG on, localhost). The Docker/CI phase is then a configuration change, not
  a rewrite.
- The shared base template is `templates/base.html`, containing the nav,
  messages and the Tailwind CDN. App templates go in `<app>/templates/<app>/`.

### Git and Docker (step 08)
- **The image is for development only.** `Dockerfile` (`python:3.12-slim`)
  runs `runserver` on `0.0.0.0:8000` as root. A production image (Gunicorn,
  a non-root user, hardening) is a later DevOps step.
- **Layers:** dependencies install from `requirements.txt` in their own
  layer, before the code is copied. A new dependency still goes only
  through `requirements.txt`, then `docker compose build`.
- **`compose.yaml` has a `web` service** (and a `db` service since step
  09, see PostgreSQL below):
  - a bind mount of the project at `/app`, for live reload;
  - the port published as `127.0.0.1:8000:8000`, so the `DEBUG` development
    server with its dev-only key is never exposed to the local network
    (step 08 S-5). Keep the `127.0.0.1` prefix;
  - environment values labelled development-only.
- **The container keeps its own database**, separate from the host's
  `db.sqlite3`. Step 08 used SQLite on a named volume. Step 09 replaced it
  with PostgreSQL. The optional `DJANGO_SQLITE_PATH` setting stays, for
  pointing the host's SQLite file elsewhere.
- **`.dockerignore` vs `.gitignore`:** `.dockerignore` also leaves out
  tracked files the image doesn't need (`.git`, `.claude/`, root `*.md`,
  the Docker files). `design-system/` must stay in the build context,
  because `core/tests/test_ui.py` reads `MASTER.md`.

### PostgreSQL (step 09)
- **`db` service:** `postgres:17`, pinned to the major version because it
  fixes the on-disk format (plan 09, D-2).
  - It keeps its data in the `postgres-data` named volume.
  - It publishes **no port**: only Compose services reach it.
  - A `pg_isready` health check lets `web` wait for it with
    `depends_on: condition: service_healthy`. Starting the container isn't
    enough: on a fresh volume, PostgreSQL needs a few seconds before it
    accepts connections.
  - The check runs over TCP (`pg_isready -h 127.0.0.1`), the way `web`
    connects. During first-time setup the image runs a temporary server
    that listens on the Unix socket only, so a socket check could pass
    before TCP is open (step 09 Q-76). Keep the `-h`.
- **Choosing the backend (plan 09, D-1):** `config/settings.py` uses
  PostgreSQL when `DJANGO_DB_HOST` is set, with `DJANGO_DB_NAME`, `_USER`,
  `_PASSWORD`, `_HOST` and `_PORT`. Otherwise it uses SQLite. Compose sets
  host `db`, the service name; never `localhost`, which inside `web` means
  `web` itself. The values in `compose.yaml` are dev-only.
- **Collation `C`, ctype `en_US.utf8`** (`POSTGRES_INITDB_ARGS`, plan 09,
  D-3).
  - Lists sort in code-point order, exactly as on SQLite.
  - `LOWER()` still folds all Unicode letters.
  - Test databases inherit it from `template1`.
  - The image's default collation would reorder names, ignoring spaces
    and punctuation. Choosing natural-language sorting later is a product
    decision.
  - The initdb arguments apply only when the volume is first created.
- **One case rule for users (S-1 fixed, plan 09, D-4):**
  - `UserManager.filter_username_ci()` and `filter_email_ci()` compare
    `Lower(field)` with `Lower(Value(input))`, the same database function
    as the unique constraints, so at most one user can match.
  - Use them, never `__iexact`, for user lookups. `__iexact` uses `UPPER()`
    on PostgreSQL, which disagrees with `LOWER()` for e.g. `I`/`ı`.
  - Login (`get_by_natural_key`), the registration checks and add-member
    use them.
  - Project names still use `__iexact`. That's harmless: it's at most
    stricter than the constraint, and the race backstop catches the rest.
- **Dependency:** `psycopg[binary]~=3.3.0`. The wheel bundles `libpq`, so
  the `Dockerfile` needs no system packages.

### Apps
- **`accounts`: identity only.** It holds the user model, registration and
  login/logout, under the `accounts:` URL namespace at `/accounts/`.
- **`core`: the signed-in home.** It holds the root redirect and the
  dashboard, under the `core:` namespace. The dashboard lives here, not in
  `accounts`, because later steps fill it with projects and tasks. It also
  holds shared view helpers (`core/mixins.py`). `core` may import from feature
  apps (the dashboard lists workspaces), but feature apps import only
  `core.mixins` from it, so imports never go in a circle.
- **`workspaces`: workspaces and their membership** (step 02), under the
  `workspaces:` namespace at `/workspaces/`. It is its own app because
  projects will belong to a workspace.
- **`projects`: projects inside a workspace** (step 04), under the
  `projects:` namespace. Its URLs are **nested** under the workspace
  (`/workspaces/<workspace_pk>/projects/…`), and that include comes before
  the `workspaces/` include in `config/urls.py`. It is its own app because
  tasks will belong to projects.
  - `projects` imports from `workspaces`.
  - `workspaces` doesn't import `projects`, but the workspace page **depends
    on it at runtime** through the `workspace.projects` reverse relation and
    `ProjectQuerySet.alphabetical()`. Removing or renaming `projects` would
    break that page.
- **`tasks`: tasks inside a project** (step 05), under the `tasks:`
  namespace, **nested** under the project
  (`/workspaces/<workspace_pk>/projects/<project_pk>/tasks/…`). Its include
  comes first in `config/urls.py`, then the projects include, then
  `workspaces/`. It is its own app because later features (assignment,
  status) attach to tasks.
  - Imports only point down the hierarchy: `tasks` → `projects.mixins` →
    `workspaces.mixins`.
  - The project page **depends on `tasks` at runtime** through the
    `project.tasks` reverse relation and `TaskQuerySet.in_creation_order()`.

### Workspaces and access control (step 02)
- **One record of ownership:** a non-null `Workspace.owner` foreign key.
  `Membership` (workspace, user) has no role field. "Exactly one owner" is
  therefore built into the structure. The Owner/Member labels come from
  comparing a row with `owner`, via the `is_workspace_owner` annotation in
  `Workspace.member_list()`.
- **The owner is always a member as well.** Always create workspaces with
  `Workspace.objects.create_with_owner()`, which writes the workspace and the
  owner's membership in one transaction. Never call `Workspace.objects.create`
  directly. Workspaces are deliberately **not** registered in the admin,
  because the admin's add form would skip this.
- **`owner` uses `on_delete=PROTECT`** (plan 02, D-1). Deleting a user who
  owns a workspace is refused rather than silently deleting everyone's
  workspace. Deleting a plain member removes only their memberships.
- **No duplicate memberships** is enforced three ways:
  - a database `UniqueConstraint(workspace, user)`;
  - a form check, so the error appears next to the field;
  - `Workspace.add_member()` uses `get_or_create`, so two simultaneous adds
    give a field error, not a 500.
- **The access pattern later steps should copy:**
  - `Workspace.objects.for_user(user)` is the members-only queryset. It is
    used to look a workspace up **from the URL** in exactly **two** places:
    - `WorkspacePageMixin.get_queryset()` (`workspaces/views.py`), for the
      workspace's own pages;
    - `MemberWorkspaceMixin.resolve_scope()` (`workspaces/mixins.py`), for
      every resource nested under a workspace.

    `DashboardView` also calls it, but only to **list** the user's own
    workspaces, never to resolve a URL. A source-check test in
    `projects/tests/test_mixins.py` fails if any other caller appears.
  - **Nested resources use one chain of `resolve_scope()` hooks**, called
    from `MemberWorkspaceMixin.dispatch`:
    - `MemberWorkspaceMixin` sets `self.workspace` through `for_user()`;
    - `MemberProjectMixin` (`projects/mixins.py`) calls `super()` first, then
      sets `self.project` from `self.workspace.projects`;
    - the deepest object is then scoped by the view's `get_queryset()`
      (e.g. `self.project.tasks.all()`).

    These mixins go **after** `LoginRequiredNoReplayMixin` in the bases, so
    login is checked first. A new nesting level extends `resolve_scope()`,
    always calling `super()` first; it never adds its own `dispatch` or its
    own `for_user` lookup.
  - As a result, a non-member, any missing ID, and any child requested under
    the wrong workspace or the wrong project (even another project in the
    same workspace) all get the same 404, before any method check.
  - The parent of a new object is always set on the server from the
    authorised scope (`form.instance.workspace = self.workspace`,
    `form.instance.project = self.project`), never from a form field.
    Posted IDs are ignored.
  - Create views allow only `get`, `head`, `post` and `options`. Detail views
    allow only `get`, `head` and `options`.
  - A non-member and a missing ID therefore get the same **404**, which hides
    whether the workspace exists.
  - Role checks (owner-only actions) come **after** that lookup and raise
    **403**, so only members ever see a 403.
- **Adding members by username** ignores letter case, and only active users
  can be added. Unknown and inactive users get the same "not found" message.
  The lookup treats anything other than exactly one match as "not found", so
  S-1 can't cause a 500 here.
- **`LoginRequiredNoReplayMixin`** (`core/mixins.py`) is the login guard for
  views that accept form submissions. Use it instead of `LoginRequiredMixin`.
  - Anonymous GET or HEAD → login with `?next=`, as before.
  - Anonymous POST (or any other method) → login **without** `next`, so after
    logging in the user lands on the dashboard and the submission is never
    replayed (spec 02, AC-23).
  - Every other case keeps Django's own handling.
  - `LoginView` stays the only code that reads `next`.

### Projects (step 04)
- **One workspace per project:** `Project.workspace` is a non-null foreign
  key with `on_delete=CASCADE` (plan 04, D-2). A project can't exist without
  its workspace, and nothing deletes workspaces today.
- **Fields:** `name` (required, up to 100 characters, trimmed) and
  `description` (optional plain text, up to 2,000 characters, trimmed).
  Nothing records who created a project or when; that comes in a later spec.
- **Names are unique within a workspace, ignoring letter case.** This is
  enforced three ways:
  - a database `UniqueConstraint(F('workspace'), Lower('name'))`;
  - `ProjectForm.clean_name`, so the error appears next to the field;
  - `ProjectCreateView` saves in a short `transaction.atomic()` block and
    catches `IntegrityError` **outside** it (plan 04, D-3). The block rolls
    back first, then the race shows as the same field error. Never keep
    using the database inside a failed atomic block.

  **Form validation never runs constraints that use `F('workspace')`**,
  because `workspace` isn't a form field. The form check is therefore the
  only friendly duplicate check, and the database constraint is the race
  backstop. `DUPLICATE_NAME_MESSAGE` lives in `projects/models.py`.
- **Order:** projects are listed alphabetically, ignoring case
  (`ProjectQuerySet.alphabetical()`).
- **Who can do what:** any workspace member, the owner included, can create
  and view projects. There are no project-level roles. Projects aren't
  registered in the admin.

### Tasks (step 05)
- **One project per task:** `Task.project` is a non-null foreign key with
  `on_delete=CASCADE` (plan 05, D-2). There's no separate workspace field;
  the workspace comes through the project.
- **Fields:** `title` (required, up to 200 characters, trimmed) and
  `description` (optional plain text, up to 2,000 characters, trimmed).
  Titles may repeat, so there's no uniqueness rule and no race handling.
- **Order:** a stable oldest-first creation order by the auto-increment
  primary key (`TaskQuerySet.in_creation_order()`, plan 05, D-3). There's no
  timestamp field, and no date is shown anywhere.
- **Who can do what:** any workspace member who can access the project can
  create and view its tasks. Tasks aren't registered in the admin.
- **Assignment (step 06):**
  - `Task.assignee` is one optional foreign key to the user (at most one
    assignee by structure), with `on_delete=SET_NULL`: deleting the user
    leaves the task unassigned (plan 06, D-1).
  - Only `Workspace.assignable_users()` can be chosen: the workspace's
    **active** members, owner first, then alphabetical. `TaskAssignForm`
    limits its choices to that queryset, so any other user ID fails as an
    invalid choice. The form is the only write path; the database can't
    enforce membership across tables.
  - Any member who can access the task may assign it. It uses the POST-only
    `tasks:assign`, with the usual scope chain, CSRF and no-replay.
  - `TaskPageMixin` (`tasks/views.py`) builds the task page for the detail,
    assign and status views, like `WorkspacePageMixin`.
- **Status (step 07):**
  - `Task.status` holds one of three values, `Task.Status` (To do,
    In progress, Done), with the default To do. Any status can change to any
    other.
  - A database `CheckConstraint` (`tasks_task_status_valid`) refuses other
    values from any write path (plan 07, D-1).
  - It uses the POST-only `tasks:status`, built like `tasks:assign`. The
    current status shows as a text badge on the task page and on each
    project-page task row, through one partial,
    `tasks/templates/tasks/partials/status_badge.html`.
  - **Single-field task updates** (assignee, status) follow one pattern: a
    POST-only view with the scope resolved first, the previous value
    captured before validation, an info message and no write when nothing
    changes, `save(update_fields=[...])` otherwise, and the page shown again
    with a field error when the value is invalid. Reuse it for the next
    single-field change; consider a shared base only when a third appears.

### Users and authentication
- **Custom user model `accounts.User` (extends `AbstractUser`)** has existed
  since the first migration. Django's docs warn that swapping the user model
  later is very painful. Always refer to it via `settings.AUTH_USER_MODEL` /
  `get_user_model()`.
- **Usernames and emails are unique ignoring letter case.** This is enforced
  twice:
  - Database `UniqueConstraint(Lower(...))` constraints, which also stop two
    simultaneous sign-ups and cover the admin.
  - Field-level checks in the registration form, so errors appear next to the
    field.

  The email constraint skips blank emails, because `createsuperuser` allows
  them. The shared messages live in `accounts/models.py`.
- **Login ignores letter case** via `UserManager.get_by_natural_key`
  (the shared `LOWER()` rule, see PostgreSQL above), so the login page, the admin and `createsuperuser` all
  behave the same. The casing chosen at registration is the one stored and
  displayed.
- **Use Django's auth views, not custom ones.**
  - `LoginView` (with `redirect_authenticated_user`) is the *only* code that
    reads `next=`, so return-to links are validated in one place.
    `RegisterView` deliberately ignores `next`.
  - `LogoutView` is POST-only. The nav logs out with a POST form plus a CSRF
    token. The "logged out" message is added *after* `logout()` flushes the
    session.
- **Where to send users is set once in settings:** `LOGIN_URL`,
  `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL`. Views use
  `resolve_url(settings.…)` and never hard-code route names.
- **Protected pages** use `LoginRequiredMixin`. Anonymous users are sent to
  login with `?next=`. Later steps follow the same pattern, plus queryset
  scoping (see Conventions).

### Templates and design system (step 03)
- **Design system:** `design-system/project-management-system/MASTER.md`
  was generated by the ui-ux-pro-max skill and holds the generated
  `pages/*.md` overrides.
  - Its **"Project adjustments (step 03)" section overrides everything else**
    in MASTER.md and in `pages/*.md`. The generated text above it (Google
    Fonts, GSAP, an emerald CTA, 1200px/1400px grids) is kept only as a record
    of the skill's output.
  - Read the adjustments before any UI work. Change them only through an
    approved step.
- **Tokens:** `base.html` defines **semantic colour tokens** in `@theme`
  (`primary`, `ink`, `muted`, `canvas`, `surface`, `line`, `line-strong`,
  `ring`, `danger`, the message kinds, the badge kinds) and a system
  `--font-sans`.
  - Templates use the token utilities (`bg-primary`, `text-muted`,
    `border-line`), never Tailwind palette classes or raw hex.
  - Each token pair meets WCAG 2.2 AA, and `core/tests/test_ui.py`
    recomputes the ratios from `base.html`, so a token change that breaks AA
    fails the tests.
- **Layers:** shared styles live in `@layer components` (`.btn-primary`,
  `.btn-secondary`, `.card`, `.link`, `.nav-link`, `.form-field`, `.msg-*`,
  `.badge-*`, `.skip-link`), so a page-level utility can override them. That
  fixed step 02's Q-11, where unlayered rules beat utilities. Global rules
  (body, the keyboard focus ring, reduced motion) live in `@layer base`.
- **Focus:** a single `:focus-visible` ring for every control. Always use
  `outline-hidden`, never `outline-none`: in Tailwind v4, `outline-none`
  removes the outline that Windows forced-colors mode needs to show focus.
- **Buttons:** one size everywhere (`min-h-11`, 44px), the nav included.
  Interactive targets are 44px tall wherever possible.
- **Icons:** inline SVG partials in `templates/partials/icons/`, copied from
  Heroicons v2 outline (MIT) and included with
  `{% include "partials/icons/<name>.html" with class="size-5" %}`.
  - Always next to visible text, so always `aria-hidden`.
  - No icon package, and no emoji.
  - Each icon has one meaning: `folder` = a workspace,
    `clipboard-document-list` = a project, `list-bullet` = tasks,
    `check-circle` = a success message only.
- **Action labels (projects and tasks):**
  - A link or button that **opens** a create form reads "New <thing>", both
    in a section header and in its empty state. The submit button reads
    "Create <thing>".
  - Only one create action shows at a time: the header one when items exist,
    the empty-state one otherwise.
  - Workspaces are a known exception: the dashboard still says
    "Create workspace" (plan 05, D-4; review Q-51).
- **Back links** read "Back to <destination name>", with the name in its own
  `wrap-anywhere` span.
- **Textarea:** `.form-field textarea` adds `min-h-28 py-2` on top of the
  shared field rule, and gets the same border, focus and invalid styling.
- **Base layout:** `base.html` has a "Skip to main content" link,
  `<header>`/`<nav aria-label="Main">` with `aria-current="page"` on the
  current item, and `<main id="main">`.
  - Messages sit in a `role="status"` region.
  - Each message shows an icon and a hidden kind word ("Success:"), and its
    text is never changed.
- **Forms** render through `templates/partials/form_body.html`, in this order:
  1. one "* Required field" note;
  2. non-field errors in an error box;
  3. each visible field through `partials/form_field.html`;
  4. hidden fields.

  Inside a field:
  - `form_field.html` gives help text and errors the IDs `<id>_helptext` and
    `<id>_error`, which Django 5.2's `aria-describedby` on the input already
    points at.
  - Invalid fields are styled from Django's `aria-invalid="true"`, so the
    visual and announced states can't disagree.
  - Python forms carry no CSS classes, only attributes such as
    `autocomplete`.

  New forms include the partial rather than copying markup.
- **Long text:** user text (workspace and project names, usernames,
  descriptions) uses `wrap-anywhere` inside `min-w-0` flex children, so it
  never causes sideways scrolling.
  - Multi-line plain text such as descriptions is shown with `linebreaksbr`,
    which escapes the text before adding `<br>`, inside `max-w-prose`.
  - Never use `|safe`.

### Known limitations (deliberately deferred)
- **SQLite ignores letter case for ASCII letters only** (see Stack
  constraints). This now affects only the host `.venv` workflow.
  PostgreSQL in Compose folds all Unicode letters.
- **S-2, for the DevOps/production step:**
  - There are no HTTPS or secure-cookie settings yet (`SESSION_COOKIE_SECURE`,
    `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS).
  - The app should refuse to start with `DEBUG` off and the fallback secret key.
- **S-3, accepted (step 02 product behaviour):**
  - An owner can add any active user without that user agreeing, and the
    user can't leave. The workspace name then appears on their dashboard.
  - It is shown escaped (no XSS), but it could be used for spam or social
    engineering.
  - Invitations or "leave workspace" need their own spec.
- **S-4, for whichever step adds removing members or leaving a workspace:**
  "the owner is always a member" is enforced only because nothing deletes
  memberships yet. That step must add a model-level guard that refuses to
  remove the owner's membership. Otherwise the owner could be locked out of
  their own workspace.
- **UI limits accepted in step 03 (no JavaScript allowed):**
  - Failed forms keep inline errors but don't move focus to an error
    summary.
  - There's no show/hide password toggle.
  - Messages aren't dismissible.
  - A `role="status"` message that is already on the page when it loads may
    not be announced by every screen reader.
  - Dark mode isn't built; MASTER notes how the tokens would map.
- **Q-24, for the DevOps step that replaces the Play CDN:** the Tailwind tag
  is unpinned (`@4`), but `wrap-anywhere` needs 4.1 or later. Pin the version
  or move to a build then.
- **Project and task description lengths are enforced by the form only.**
  Django never enforces `TextField.max_length` in the database, on any
  backend. The only write paths today are `ProjectForm` and `TaskForm`. A
  future edit view or admin registration needs its own length (and, for
  projects, duplicate) checks; database enforcement would need a
  `CheckConstraint` on `Length()`.
- **Task order on PostgreSQL:** ordering by `pk` follows insertion order.
  When two inserts commit at the same moment, a lower ID can commit after a
  higher one, so a task could briefly appear one place earlier. It's rare
  and stable afterwards. SQLite serialises writes, so it can't happen
  there. **Reassessed and accepted in step 09 (OQ-6):** a real fix needs a
  new ordering field, which is a product change for its own spec.
- **Deferred to the next UI step (step 05 review):**
  - **Q-53:** extract the copied back link and list-section/empty-state
    markup into partials. The workspace page's back link has already drifted
    (it lacks `max-w-full`/`min-w-0`).
  - **Q-62:** use one location order (workspace → project) on the
    create-task and task pages, and add the workspace to the task page title.
  - **Q-63:** a linked breadcrumb for pages three levels deep (the task page
    has a plain-text location line for now).
  - **Q-51:** rename the workspace action labels to the "New <thing>" rule.
- **Deferred to a later step (step 05 review; not in step 06's scope):**
  - **Q-69:** `WorkspaceCreateView` still accepts PUT. Not exploitable, but
    it's the only create view without `http_method_names`.
  - **Q-54:** remove the unused `admin` imports.
  - **Q-55:** fix the `workspaces/mixins.py` docstring (the chain stops at
    the project).
  - **Q-56:** reword the `projects/models.py` comment.
  - **Q-57 to Q-61**, test quality:
    - the source check should allow specific methods, not whole classes;
    - the unscoped-lookup check uses a hard-coded file list;
    - a `projects` test imports `tasks`;
    - test data is copied in several places;
    - some assertions depend on exact markup nesting.
- **Deactivated assignee (step 06 Q-70):** if an assignee is deactivated
  after being assigned, the task page still shows their name, but the
  drop-down can't offer them, so it preselects "Unassigned". Saving without
  changing anything would then unassign the task. Handle this in the step
  that specifies deactivation or member removal (with S-4).

- **Task status values are repeated (step 07 Q-72):** `todo`,
  `in_progress` and `done` appear in `Task.Status`, the check constraint and
  the badge partial. If statuses ever change, take them from one constant and
  have the model supply the badge style.

- **Floating base image tag (step 08 Q-74):** the `Dockerfile` uses
  `python:3.12-slim`, so a rebuild can pick up a newer patch release or a
  new Debian base. That's fine for development. Pin a tag or digest in the
  CI/CD step for reproducible builds.

- **Dev database credentials are repeated (step 09 Q-78):** the database
  name, user and password appear in both the `web` and `db` services in
  `compose.yaml`. Change one without the other and you get an
  authentication error. Remove the duplication in the step that moves
  credentials out of `compose.yaml` (e.g. a git-ignored `.env`).

- **The admin add-user form still uses `__iexact` (step 09 Q-77,
  accepted):** Django's `UserAdmin` checks usernames with `UPPER()` on
  PostgreSQL, which is only *stricter* than the `LOWER()` rule (it refuses
  `ı` while `I` exists) and can't cause a 500. It's superuser-only.
  Switch it to `filter_username_ci()` if the admin user forms are ever
  customised.

### Steps landed
- **01 — User authentication:** username/email/password sign-up (unique
  ignoring letter case), login ignoring username case, POST-only logout, a
  login-protected dashboard, the root redirect, and navigation that changes
  with login state. 66 tests.
- **02 — Workspaces and membership:** signed-in users create named
  workspaces, which they own. Owners add active users by username, ignoring
  case. Members see the name and the member list, owner first. Non-members
  get a 404, and non-owner members get a 403 on add. The dashboard lists the
  user's workspaces. 74 tests (140 in total).
- **03 — UI refresh:** every page restyled with the ui-ux-pro-max skill's
  full workflow, on a saved design system with indigo/slate semantic tokens
  (all WCAG AA). It adds system fonts, layered shared components (fixing
  Q-11), a skip link, a current-page marker, accessible messages and form
  errors, and inline SVG icons. No behaviour changed. 49 tests (189 in
  total).
- **04 — Projects:** workspace members create projects (a name and an
  optional description) inside a workspace. Project names are unique per
  workspace, ignoring case, with a race-safe save. The workspace page lists
  projects alphabetically, with an empty state, and each project has its
  own page. Projects are nested under their workspace, so non-members and
  wrong-workspace IDs get the same 404. 80 tests (269 in total).
- **05 — Tasks:** workspace members create tasks (a title and an optional
  description) inside a project, listed oldest first on the project page,
  each with its own page. Access is one `resolve_scope()` chain (workspace →
  project → task), so wrong or missing IDs at any level get the same 404.
  It also cleared step 04's deferred items (one shared lookup chain,
  "Back to" links, "New project" labels, comments, test helpers). 109 tests
  (378 in total).
- **06 — Task assignment:** a task can be assigned to one active member of
  its workspace, reassigned or unassigned from the task page. Outsiders,
  inactive users and invalid IDs are rejected without changing anything.
  First step under the token-efficient workflow. 13 tests (391 in total).
- **07 — Task status:** tasks are To do, In progress or Done (default To do,
  enforced in the database), changed from the task page, and shown as a text
  badge on the task page and the project's task rows. 12 tests (403 in
  total).
- **08 — Version control and Docker:** the project became a Git repository
  (`main`, with the user making the first commit). The unchanged app now
  runs in a development Docker container through Compose:
  - live reload through a bind mount;
  - SQLite kept on a named volume;
  - the port published only on localhost.

  The full suite passes on the host and in the container. No new tests
  (403 in total).
- **09 — PostgreSQL in Docker Compose:** Compose runs the app on
  PostgreSQL 17 in its own `db` service (no published port, a TCP health
  check, data on a named volume), while the host `.venv` stays on SQLite.
  User lookups now share one `LOWER()` case rule on both backends (S-1
  fixed). The full suite passes on both. 8 tests (411 in total).

---

## Testing

- **Who writes tests:** `/build` may write them directly. Use `test-author`
  only when independent test design genuinely helps (see Sub-agents).
- **Tests come from the approved spec**, not from the implementation. Every
  important acceptance criterion gets appropriate coverage, and the test
  names its AC (`# AC-3` in a comment or the docstring).
- **Test behaviour.** Prefer behaviour-focused tests to brittle markup or
  source-inspection tests. Don't write tests for documentation wording or
  for implementation details that aren't meaningful behaviour.
- Tests live in `<app>/tests/` as a package (`test_models.py`, `test_views.py`,
  …). That keeps them focused as apps grow, and lets you run one module at a time.
- Use `django.test.TestCase` and the test `Client`. Build test data in
  `setUpTestData` or small helper functions. No fixtures files and no
  factory libraries.
- Shared HTML and CSS test helpers (a stdlib HTML parser, `@layer`/`@apply`
  rule parsing, the colour regexes, and `local_template_dirs()`) live in
  `core/tests/helpers.py`. That isn't a test module, so import from it, not
  from another app's test file. Per-app shared data lives in
  `<app>/tests/data.py` base classes. Core's token check scans every local
  app's templates automatically (since step 05).
- **Test permissions, not just the happy path.** For every view that touches
  a project or task, test that a non-member gets a 404 or 403 and an anonymous
  user is redirected to login. Ownership gaps are the most likely serious bug
  in this kind of app.
- Tests must not touch the network or depend on test order.
- When a test exposes an application bug, fix the application, within the
  plan's scope. Never weaken the test just to make the suite pass.
- Verification follows the standard order: focused tests, then migration
  drift, then `check`, then the full suite.

---

## Frontend and UI work

- **Use the `ui-ux-pro-max` skill for all frontend work.** That means new or
  changed templates, page layout, styling, forms, navigation, empty states and
  messages. Load the skill (`ui-ux-pro-max:ui-ux-pro-max`) before writing the
  markup, both in `/build` and in any review fix that touches templates.
  Plans that include templates should say which pages it was applied to.
- **Use the skill efficiently: design system first, searches only when
  needed.**
  - **Design system:** the project design system was made by the skill's
    `--design-system --persist` mode, at
    `design-system/<project>/MASTER.md`, plus optional `pages/<page>.md`
    overrides.
    - Read it before any UI work.
    - Regenerate it, or use `--force`, only when the user approves.
  - **Reuse first:** reuse the existing components and patterns. Don't
    rediscover design decisions for pages that already exist.
  - **Searches only when needed:** run focused `--domain` searches only for a
    genuinely new UI pattern, a design question MASTER doesn't answer, or an
    accessibility or layout problem that needs guidance. Run
    `--stack html-tailwind` searches only when you need implementation
    guidance.
  - **Checklist:** check only the relevant items of the skill's pre-delivery
    checklist (`references/pro-rules.md`, `references/quick-reference.md`).
    Don't list N/A items.
  - **Record it briefly:** the build notes summarise the meaningful UI
    decisions, not every search and its result.
- **The skill works inside the stack, never around it.** Its output must be:
  - Django templates;
  - Tailwind utility classes from the Play CDN, with shared rules as `@apply`
    in `base.html`;
  - forms rendered through `partials/form_body.html`.

  Ignore its suggestions that need React, shadcn/ui, Radix, npm or a build
  step, or any other JS framework, icon package or font service not already
  allowed. If a good design truly needs one of those, raise it as a spec
  open question; don't add it.
- **Keep one visual language.** Build on the existing look (white
  `rounded-2xl` cards, slate text, indigo accents) unless a spec asks for a
  redesign. A new page should look like it belongs with the old ones.
- **Accessibility is part of "done".** Every input has a label, there is a
  visible focus state, text has enough colour contrast, headings follow a
  sensible order, and errors appear next to the field they belong to.

*Why:* the skill gives consistent, accessible design guidance without adding
any project dependency. It is a Claude Code plugin installed for the user,
not part of the app. The stack limits still apply, so the DevOps phases keep
a pure-Python toolchain. Added 2026-10-05 at the user's request. On the same
day the user asked for the skill to be used as fully as possible. From step
06 the user made it design-system-first, with searches only when needed, to
cut repeated work.

---

## Conventions

- **Authorization is enforced in the queryset.** Get objects through querysets
  scoped to the user's memberships (e.g. `Workspace.objects.for_user(user)`, then `workspace.projects` for a
  nested resource), not
  through `get_object_or_404(Project, pk=pk)` followed by a check. That way a
  forgotten check fails closed.
- Every view that isn't public needs a login (`LoginRequiredMixin` /
  `@login_required`). State changes use POST only, with CSRF on, and are never
  done by GET.
- Use class-based views for standard CRUD and function views when they are
  clearer. Don't mix the two styles within one app.
- Use Django forms or ModelForms for every input. Never read `request.POST`
  directly into a model.
- Keep business rules on models or managers, not in templates.
- Commit every model change with its migration. Never edit a migration that has
  already been applied; add a new one.
- Names: snake_case for modules and functions, PascalCase for classes, and
  `app_name` namespaced URLs (`projects:detail`).
- Keep each change within its plan. If something outside the plan needs to
  change, stop and say so rather than expanding the step.
- Don't commit secrets. `SECRET_KEY` comes from the environment. The local
  fallback must say clearly that it is insecure.
