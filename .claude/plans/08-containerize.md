---
step: 08
slug: containerize
spec: .claude/specs/08-containerize.md
status: done
created: 2026-10-10
approved: 2026-10-10
---

# Plan 08 — Version control and Docker

## Approach
Run `git init -b main` at the repo root and extend the existing `.gitignore`. Add a
development-only image, `Dockerfile` on `python:3.12-slim`, with a
`.dockerignore` and a single-service `compose.yaml`. The Compose service
bind-mounts the source for live reload and keeps SQLite in a **named volume**
(D-2), so the database survives when a container is recreated and never
ends up in the image. Application code is unchanged; the only settings
change is the optional database-path variable in D-2. Docs go in a new
`README.md`. No Gunicorn, Nginx, PostgreSQL, non-root user or other
hardening; those belong to later DevOps steps.

**Why a named volume rather than the bind-mounted `db.sqlite3`:** SQLite
relies on file locking. Across a Docker Desktop bind mount from a Windows
drive, locking is unreliable and slow. A named volume lives inside Docker's
Linux filesystem. It also keeps container data apart from the host `.venv`
database, and gives the "volume" concept a real use alongside the "bind
mount" one.

## Data model & migrations
None. `makemigrations --check` must still report no changes.

## URLs, views, templates
None.

## Implementation steps
- [x] 1. **Git:**
  - `git init -b main`, so the default branch is named `main`.
  - Extend `.gitignore` with:
    - `db.sqlite3*`, `*.sqlite3` and `*-journal`;
    - `.env`, `.env.*` and `*.local`;
    - `.claude/settings.local.json`;
    - `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/` and `htmlcov/`;
    - `.idea/`, `.vscode/`, `*.log` and `.DS_Store`.
  - Check `git status --ignored` and `git ls-files --others --exclude-standard`.
  - **No commit** (D-1).
- [x] 2. **Settings (D-2):** add the optional `DJANGO_SQLITE_PATH`
  environment variable to `config/settings.py`. The default stays
  `BASE_DIR / 'db.sqlite3'`, so the host workflow is unchanged.
- [x] 3. **`Dockerfile`:**
  - Base image `python:3.12-slim`, `WORKDIR /app`.
  - `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`. The first keeps
    `__pycache__` off the bind mount; the second makes logs appear
    immediately.
  - `COPY requirements.txt`, then `pip install --no-cache-dir -r
    requirements.txt`, then `COPY . .`. The dependency layer is cached
    until `requirements.txt` changes.
  - `EXPOSE 8000`.
  - `CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]`.
- [x] 4. **`.dockerignore`:** leaves out `.git`, `.venv`, `db.sqlite3*`,
  `__pycache__`, `*.py[cod]`, `.env*`, caches, IDE folders, `.claude/`,
  `Dockerfile`, `compose.yaml` and the root `*.md` files.
  - `design-system/` stays in the image, because
    `core/tests/test_ui.py` reads `MASTER.md`, so the tests must pass in
    a standalone container too.
  - **How it differs from `.gitignore`:** Git ignores what should never be
    in history. `.dockerignore` also leaves out files that *are* tracked
    but don't belong in a runtime image: Git metadata, workflow docs and
    the Docker files themselves. That keeps the context small and the
    layers stable.
  - `README.md` is excluded along with the other root `*.md` files.
- [x] 5. **`compose.yaml`:** one service, `web`.
  - `build: .`
  - `ports: "8000:8000"`
  - `volumes: .:/app` (a bind mount, for live reload) and
    `sqlite-data:/data` (a named volume).
  - The `environment` values are all labelled development-only:
    - `DJANGO_DEBUG=1`;
    - `DJANGO_SECRET_KEY=django-insecure-docker-dev-only`;
    - `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`;
    - `DJANGO_SQLITE_PATH=/data/db.sqlite3`.
  - Top-level `volumes: sqlite-data:`.
  - Live reload works because `runserver`'s StatReloader polls file times,
    and that works across Windows bind mounts without inotify.
- [x] 6. **`README.md`:**
  - what the project is;
  - the `.venv` workflow;
  - the Docker workflow, with PowerShell commands to:
    - build: `docker compose build`;
    - start: `docker compose up -d`;
    - stop: `docker compose down`;
    - view logs: `docker compose logs -f web`;
    - run migrations, the check and the tests:
      `docker compose exec web python manage.py migrate|check|test`;
    - open a shell: `docker compose exec web bash`;
    - inspect the database: `docker compose exec web python manage.py dbshell`
      or `ls -l /data`. `dbshell` needs the `sqlite3` CLI, so the docs use
      `manage.py shell` if it isn't in the image;
    - reset the database: `docker compose down -v`, then `up -d` and
      `migrate`;
  - "Docker concepts in plain language", covering the terms listed in AC-13.
- [x] 7. **`CLAUDE.md`:**
  - add Docker rows to Common commands;
  - replace the "not a git repository yet" paragraph with the `git diff`
    rule;
  - add a short Docker/Git conventions note under Architecture: dev image
    only, the named volume, and the rule that dependency changes still go
    through `requirements.txt`.
  - The step history waits for `/done`.
- [x] 8. **Verify** (see the test plan).

## Test plan
These ACs are about infrastructure, so verification is by command, not new
Django tests. The 403 existing tests are the behaviour check.

| AC | Check | What it asserts |
|---|---|---|
| AC-1 | `git status --ignored`, `git ls-files -o --exclude-standard`, `git symbolic-ref --short HEAD` | Git is set up on branch `main`; `.venv`, `db.sqlite3`, caches and `.env` show as ignored and none are offered for tracking |
| AC-2 | Search the files Git would track for `SECRET_KEY` and key-like strings | Only the insecure-labelled fallbacks and the dev-only Compose value |
| AC-3 | `docker compose build`; `docker compose run --rm web python --version` | The build succeeds; Python is 3.12.x; only `requirements.txt` is installed |
| AC-4 | `docker run --rm <image> ls -a /app` | No `.git`, `.venv`, `db.sqlite3`, `__pycache__` or `.env` in the image |
| AC-5 | `docker compose up -d`, then `curl -I http://localhost:8000/accounts/login/` | Returns 200 from the host |
| AC-6 | Edit a template on the host, then reload the page and check the logs | Change appears with no rebuild (reverted afterwards) |
| AC-7 | Register a user, run `docker compose down` then `up -d`, and log in | The user still exists; `/app` in the image has no database |
| AC-8 | Read `compose.yaml` and the `Dockerfile`; run `exec web env` | Settings come from runtime env; values are dev-only |
| AC-9 | `exec web python manage.py migrate` | Applies successfully |
| AC-10 | `exec web python manage.py check` | No issues |
| AC-11 | `exec web python manage.py test` | 403 tests, all pass |
| AC-12 | Host: `makemigrations --check --dry-run`, `check` and the full suite with `.venv` | Unchanged and green; the host still uses `./db.sqlite3` |
| AC-13 | Read through `README.md` | Every listed command and concept is present, with Windows in mind |

## Risks
- **Port 8000 clash:** a host `runserver` and the container can't both bind
  8000. The README says to stop one first.
- **Running as root in the container:** acceptable for a dev image; a
  non-root user goes with the production-image step. Known limitation.
- **Line endings:** Git on Windows may convert line endings to CRLF. No
  shell scripts are copied into the image, so this doesn't affect the
  build. No `.gitattributes` for now.
- **`.venv` visible through the bind mount:** the Windows venv appears at
  `/app/.venv`, but it isn't on `PATH` and isn't used. Harmless.
- **Secrets:** the Compose secret is a deliberately insecure dev label. A
  real secret must come from the environment or a `.env` file, which is
  ignored by both Git and Docker.

## Decisions needing approval
- **D-1 — No initial commit.** Settled by spec OQ-1 (revised and
  approved 2026-10-10): `/build` runs `git init -b main` and prepares the ignore
  rules only. After verification passes, you make the first commit,
  suggested message `08: containerize`.
- **D-2 — Optional `DJANGO_SQLITE_PATH` setting.** A three-line change to
  `config/settings.py`; the default is unchanged, so the host behaviour is
  identical. It lets the container keep SQLite on a named volume (see
  Approach). *Alternative:* no settings change, with the container using
  the bind-mounted `./db.sqlite3` shared with the host. That means less
  change, but less reliable SQLite locking on Windows and no separate
  container data. *Proposed:* add the setting. **Accepted with plan
  approval, 2026-10-10.**

## Files changed
- **Created:**
  - `.git/` (by `git init -b main`; no commit);
  - `Dockerfile`, `.dockerignore`, `compose.yaml`;
  - `README.md`.
- **Modified:**
  - `.gitignore`: the rules from step 1;
  - `config/settings.py`: the optional `DJANGO_SQLITE_PATH` setting;
  - `CLAUDE.md`: the Docker commands, "Finding the diff" now Git-based,
    and the new "Git and Docker (step 08)" architecture section.
- **No application, model, migration or test files changed.**

**Build notes:**
- Docker Desktop wasn't running at first; `/build` started it.
- `python:3.12-slim` resolved to Python 3.12.15. Installed: Django 5.2.18,
  asgiref and sqlparse only.
- `python:3.12-slim` has no `sqlite3` CLI, so the README inspects the
  database with `ls /data` and `manage.py shell`, not `dbshell` (as the
  plan allowed).
- The README and the `.dockerignore` comments explain how
  `.dockerignore` differs from `.gitignore`.
- The `.dockerignore` keeps `design-system/`, as planned.
- Git Bash rewrites `/app`-style container paths for every Docker
  command, `exec` included (corrected by Q-73). Run those checks with
  `MSYS_NO_PATHCONV=1`. The README commands are PowerShell-first.
- The container was stopped with `docker compose down` after
  verification. The `sqlite-data` volume is kept and migrated, with the
  test user removed.

## Test results
All measured by `/build` on 2026-10-10. There were no browser or manual
user checks; reachability was checked with `curl`.

| AC | Result |
|---|---|
| AC-1 | `git init -b main`; `symbolic-ref` shows `main`. `git status --ignored` shows `.venv/`, `db.sqlite3` and every `__pycache__/` as ignored. No env, sqlite or cache files are offered for tracking. |
| AC-2 | Secret scan of the files Git would track: only `settings.py`'s `django-insecure-dev-only-change-me` fallback (labelled insecure) and `compose.yaml`'s `django-insecure-docker-dev-only`. No `.env`, key or database files. |
| AC-3 | `docker compose build` succeeded. Python 3.12.15; `pip list` shows Django 5.2.18, asgiref, sqlparse and pip only. |
| AC-4 | The image's `/app` holds only the app folders, `design-system/`, `manage.py` and `requirements.txt`. `find` shows no `.git`, `.venv`, `db.sqlite3*`, `.env*`, `__pycache__` or `.pyc`, and `/data` doesn't exist in the image. |
| AC-5 | After `docker compose up -d`, `curl` to `http://localhost:8000/accounts/login/` from the host returns **200**. |
| AC-6 | A marker added inside the login template's `content` block was served with no rebuild. A comment appended to `core/views.py` gave `/app/core/views.py changed, reloading.` Both files restored (`cmp` matched). |
| AC-7 | User `persist08` created in the container, then `docker compose down` (0 containers left) and `up -d`: the user still exists, in `/data/db.sqlite3`. The host `db.sqlite3` doesn't have the user. Test user deleted afterwards. |
| AC-8 | The container env shows `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and `DJANGO_SQLITE_PATH` from `compose.yaml`, all dev-labelled. The `Dockerfile` sets no Django settings. |
| AC-9 | `exec web python manage.py migrate`: all migrations applied OK. |
| AC-10 | `exec web python manage.py check`: no issues. Drift in the container: no changes. |
| AC-11 | `exec web python manage.py test`: **403 tests, OK** (47.3 s). |
| AC-12 | Host `.venv`: drift "No changes detected"; `check` no issues; the full suite gives **403 OK**. `DATABASES['default']['NAME']` is still `<repo>/db.sqlite3`. |
| AC-13 | `README.md` covers the `.venv` workflow, and the Docker commands to build, start, stop, view logs, migrate, check, test, open a shell, and inspect or reset the database (PowerShell-friendly). It explains every concept in AC-13 in plain language. |

Unresolved: none.

## Review log

### 2026-10-10: review of the build
**Scope:** the "Files changed" list. The repo has no commits yet, so
`git diff` is empty and everything is untracked. Done inline, with no
specialist reviewers: dev-only infrastructure, with no auth or access
control code changed.

The ACs are met as recorded in "Test results". No application, model or
migration changes; the settings default is unchanged (AC-12).

- **S-5 — Medium — fixed (retest).** `compose.yaml:6` publishes `"8000:8000"`.
  - **Evidence:** Docker binds a published port on **every** host
    interface (0.0.0.0), unlike a host `runserver`, which binds only to
    127.0.0.1. Anyone on the same network can reach the `DEBUG=1`
    development server, which signs cookies with a secret key published in
    a tracked file. `ALLOWED_HOSTS` doesn't help, because a client can
    send `Host: localhost`.
  - **Fix:** `"127.0.0.1:8000:8000"`. AC-5 (the browser on the host) is
    unaffected. Mention it in the README's port-mapping explanation.
- **Q-73 — Low — fixed (retest).** `README.md:30` and `CLAUDE.md:48` say the Docker
  commands "work the same in PowerShell and Git Bash", and the build notes
  say `exec` isn't affected.
  - **Evidence:** this is wrong. Git Bash rewrites container paths such as
    `/data` and `/app` for every Windows program, `docker compose exec`
    included. The build's own `docker run … ls -a /app` failed for that
    reason. As written, `docker compose exec web ls -l /data`
    (`README.md:62`) breaks in Git Bash.
  - **Fix:** say the commands are for PowerShell, and add one note:
    "In Git Bash, prefix commands that pass container paths with
    `MSYS_NO_PATHCONV=1`." It's cheap, and it affects future Claude runs
    through `CLAUDE.md`, so fix it with S-5.
- **Q-74 — Low — deferred (Known limitations).** The `Dockerfile` uses the floating tag
  `python:3.12-slim`, so rebuilds can pick up a new patch release or a new
  Debian base. That's fine for development. Pin a tag or digest in the
  CI/CD step for reproducible builds. Add it to Known limitations at
  `/done`.
- **Q-75 — Low — fixed at /done.** `CLAUDE.md:214` still lists "Docker,
  docker-compose" under "Do NOT add without being asked". `/done` should
  change it to say they now exist (step 08) and that further Docker
  changes need their own step.

**Result:** no High findings. S-5 is worth fixing before closing, because
it's a security exposure with a one-line fix; Q-73 can go in the same
retest.

### 2026-10-10: retest (S-5 and Q-73 only)
- **S-5 — fixed.**
  - `compose.yaml` now publishes `"127.0.0.1:8000:8000"`.
  - The README's Docker intro and port-mapping concept explain the
    deliberate localhost binding; `CLAUDE.md` notes it too.
  - **Measured:**
    - `docker compose port web 8000` and `docker ps` show
      `127.0.0.1:8000->8000/tcp`;
    - `curl` to `http://localhost:8000/accounts/login/` and to
      `127.0.0.1` both return **200**, so AC-5 is kept;
    - `curl` to a non-loopback host address (`172.23.160.1`, the first
      IPv4 adapter `ipconfig` listed) is refused.
- **Q-73 — fixed.**
  - The README commands are labelled PowerShell-first, with one Git Bash
    note on MSYS path conversion and `MSYS_NO_PATHCONV=1`.
  - `CLAUDE.md`'s Docker note says the same.
  - The build note above is corrected.
  - **Measured:** the README's example
    `MSYS_NO_PATHCONV=1 docker compose exec web ls -l /data` works in Git
    Bash.
- **Q-74 — accepted and deferred** to the CI/CD and reproducibility step,
  as decided. **Q-75 — deferred to `/done 08`**, as decided.
- **Not re-run:** the full suite. Only `compose.yaml` and docs changed, and
  no Python, template or settings files were touched; the earlier 403/403
  (host and container) still stands. The container was stopped again
  afterwards.
