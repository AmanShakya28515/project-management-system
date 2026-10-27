# Project Management System

A web-based project management app built with Django 5.2. Teams create
workspaces, add members, create projects and tasks, assign tasks and track
their status.

It is also a hands-on DevOps learning project. Step 08 added Git and
Docker, step 09 added PostgreSQL as a second Compose service, and step 10
added continuous integration (CI) on GitHub Actions. Deployment,
monitoring and Kubernetes come in later steps.
`CLAUDE.md` holds the project rules and history.

---

## Run it with the virtualenv (host workflow)

Requires Python 3.12. Run from the project folder in PowerShell:

```powershell
py -3.12 -m venv .venv                                   # first time only
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open <http://localhost:8000/>. Tests: `.\.venv\Scripts\python.exe manage.py test`.

This workflow uses SQLite (`db.sqlite3` in the project folder). Docker
uses PostgreSQL instead (see below).

## Run it with Docker

Requires Docker Desktop, which must be running. The commands below are
written for **PowerShell**; run them from the project folder.

> **Git Bash:** its MSYS path conversion rewrites container paths such as
> `/app` into Windows paths. Prefix commands that pass a container absolute
> path with `MSYS_NO_PATHCONV=1`, for example
> `MSYS_NO_PATHCONV=1 docker compose exec web ls -l /app`.

The app is reachable only from this machine (<http://localhost:8000/>). The
port is bound to `127.0.0.1` on purpose, because the development server
runs with `DEBUG` on and a development-only secret key.

> Only one app can use port 8000. Stop a host `runserver` before you start
> the container, and the other way round.

| Task | Command |
|---|---|
| Build the image | `docker compose build` |
| Start the app and the database (in the background) | `docker compose up -d` |
| See both services and their health | `docker compose ps` |
| First run: create the tables | `docker compose exec web python manage.py migrate` |
| Open the app | <http://localhost:8000/> |
| View logs (Ctrl+C to stop following) | `docker compose logs -f web` (or `db`) |
| Stop the app (the data is kept) | `docker compose down` |
| Run migrations | `docker compose exec web python manage.py migrate` |
| System check | `docker compose exec web python manage.py check` |
| Full test suite | `docker compose exec web python manage.py test` |
| Open a shell in the container | `docker compose exec web bash` |
| Django's Python shell | `docker compose exec web python manage.py shell` |
| Create an admin user | `docker compose exec web python manage.py createsuperuser` |
| PostgreSQL shell (`\dt` lists tables, `\q` quits) | `docker compose exec db psql -U pms -d pms` |

You only need to rebuild (`docker compose build`) when `requirements.txt` or
the `Dockerfile` changes. Code and template edits show up straight away.

### The container's database (PostgreSQL)

Compose runs two services: `web` (Django) and `db` (PostgreSQL 17). Django
connects to the host name `db`, and the data lives in a Docker volume called
`postgres-data`. It is **separate** from the host's `db.sqlite3`, so users
created in Docker don't exist in the `.venv` workflow, and the other way
round.

The database has no port on your machine on purpose. Reach it through the
`db` container instead.

- **Inspect it:**
  - `docker compose exec db psql -U pms -d pms` opens a SQL shell, for
    example `select username from accounts_user;`.
  - `docker compose exec web python manage.py shell`, then
    `from accounts.models import User; User.objects.count()` queries it
    through Django.
- **Reset it (deletes all container data):**
  ```powershell
  docker compose down -v          # -v also removes the postgres-data volume
  docker compose up -d
  docker compose exec web python manage.py migrate
  ```
- **Upgrading from step 08:** the old SQLite volume is no longer used, and
  its data wasn't moved. Delete it with
  `docker volume rm project_management_system_sqlite-data`.

## Docker concepts in plain language

- **Image:** a read-only package holding everything the app needs: a small
  Linux system, Python 3.12, Django and our code. The `Dockerfile` is the
  recipe for building it.
- **Container:** a running copy of an image. You can stop it, delete it and
  start a fresh one from the same image. Anything written inside a
  container is lost when it is removed, unless it goes to a volume.
- **Layer:** each `Dockerfile` instruction produces a layer, and Docker
  caches them. We copy `requirements.txt` and install dependencies *before*
  copying the code. A code change then reuses the cached dependency layer
  instead of reinstalling Django.
- **Build context and `.dockerignore`:** the build context is the set of
  files sent to Docker when it builds, which is this folder. `.dockerignore`
  leaves out things that must never reach the image:
  - `.venv` and local databases;
  - caches and `.env` files;
  - Git metadata.

  It differs from `.gitignore`. Git ignores what should never be in
  history. `.dockerignore` also skips tracked files the image doesn't need,
  such as docs and the Docker files themselves.
- **Port mapping:** `"127.0.0.1:8000:8000"` in `compose.yaml` connects
  port 8000 on your machine to port 8000 inside the container.
  - Django listens on `0.0.0.0:8000` *inside* the container, so it accepts
    connections coming from outside the container.
  - The `127.0.0.1` prefix publishes the port only on your own machine.
  - A plain `"8000:8000"` would publish it on every network interface,
    exposing the development server to your local network.
- **Bind mount:** `.:/app` makes this project folder appear inside the
  container as `/app`. Edits on Windows are seen at once, and Django's
  auto-reloader restarts the server.
- **Volume:** `postgres-data:/var/lib/postgresql/data` is storage managed by
  Docker that outlives containers. PostgreSQL keeps its files there, so the
  data survives `docker compose down` and is never baked into an image.
  `docker compose down -v` deletes it.
- **Environment variables:** settings passed to the container at run time
  (`DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and the
  `DJANGO_DB_*` connection values). Django reads them in
  `config/settings.py`: when `DJANGO_DB_HOST` is set it uses PostgreSQL,
  otherwise SQLite. The `db` container reads its own variables
  (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) once, when it first
  creates the database in an empty volume. Changing them later doesn't
  change an existing database. The values in `compose.yaml` are for
  development only. A real secret never goes in a tracked file.
- **Docker Compose:** describes how to run the app (image, ports, mounts,
  environment) in one file, `compose.yaml`. Short commands like
  `docker compose up` replace long `docker run` command lines.
- **Running Django commands in a container:**
  `docker compose exec web <command>` runs a command inside the running
  `web` container, with the same Python, settings and database as the app.
  Use `docker compose run --rm web <command>` when the app isn't running.

## PostgreSQL concepts in plain language

- **Why the database is a separate service:** one container, one job. The
  `db` container runs only PostgreSQL, from the official image, and keeps
  its data in its own volume. You can restart or rebuild `web` without
  touching the data, and later replace `db` with a managed database by
  changing only environment variables.
- **Service-name networking:** Compose puts both services on a private
  network and gives each a DNS name equal to its service name. Inside `web`,
  the name `db` resolves to the database container.
- **Why `db` and not `localhost`:** inside a container, `localhost` means
  *that container itself*. PostgreSQL isn't running inside `web`, so
  `localhost` would find nothing. `db` is the other container.
- **No published port:** port 5432 is open only on the Compose network,
  so other machines, and your own Windows, can't connect to it directly.
  That's safer, and it can't clash with a PostgreSQL installed on Windows.
- **Startup order and readiness:** `depends_on` with
  `condition: service_healthy` makes `web` wait until the `db` health check
  (`pg_isready`) passes. Starting the container isn't enough: on a fresh
  volume PostgreSQL needs a few seconds to initialise before it accepts
  connections.
- **Migrations against PostgreSQL:** the same migration files create the
  same tables. Django turns them into PostgreSQL SQL. Tests create and
  destroy a separate `test_pms` database automatically.
- **What changes from SQLite:**
  - PostgreSQL is a server, so you connect over the network with a user
    and password rather than opening a file.
  - It enforces types and constraints more strictly.
  - After an error inside a transaction, it refuses further statements
    until the transaction is rolled back.
  - Its `LOWER()` and `UPPER()` handle all Unicode letters, not just
    ASCII.
  - Its sort order depends on the database collation. This project uses
    the `C` collation, so lists sort exactly as they do on SQLite.

## Continuous integration (CI)

Every push to any branch, and every pull request into `main`, runs the
workflow in `.github/workflows/ci.yml` on GitHub Actions.

**Where to see results:**
- the **Actions** tab of the GitHub repository lists every run, with its
  log;
- each commit shows a green tick (passed) or a red cross (failed), and a
  pull request shows the same checks at the bottom.

**What a run checks:** two jobs run in parallel, and the run passes only
if both pass. Each runs the three checks in this order, stopping at the
first failure:

1. migration drift (`makemigrations --check --dry-run`);
2. the system check (`check`);
3. the full test suite (`test`).

| Job | Database | How it runs |
|---|---|---|
| PostgreSQL (Docker Compose) | PostgreSQL 17 in the `db` service | builds the image, then `docker compose run --rm web python manage.py …` |
| SQLite (Python 3.12) | SQLite | Python 3.12 on the runner, `pip install -r requirements.txt`, then `python manage.py …` |

**Reproducing a failure locally:** open the failed run, find the red step,
and run the same command yourself (PowerShell):

```powershell
# PostgreSQL job (Docker Desktop running)
docker compose build
docker compose run --rm web python manage.py test --noinput
# SQLite job
.\.venv\Scripts\python.exe manage.py test --noinput
```

Run one test module by adding its path, e.g. `... test tasks.tests.test_views`.

**Optional:** to stop anything being merged into `main` while CI is red,
turn on a branch protection rule for `main` in the repository settings
(Settings → Branches) and require both CI checks. That's a GitHub setting,
not part of the code.

**Versions are pinned:** the runner (`ubuntu-24.04`), the actions (`@v7`),
the Python image (`python:3.12.16-slim-trixie`) and the PostgreSQL image
(`postgres:17.11-trixie`). Updating one is a deliberate one-line change.

## CI concepts in plain language

- **Continuous integration (CI):** every change is checked automatically,
  on a clean machine, as soon as it's pushed. A broken change is caught
  even if you forgot to run the tests, and "it passes on my machine" stops
  being the only evidence.
- **Workflow:** a YAML file in `.github/workflows/` that describes what to
  run and when. It lives in the repository, so it's versioned and reviewed
  like code.
- **Trigger:** the event that starts a workflow, here `push` and
  `pull_request` (the `on:` block).
- **Job:** a group of steps that runs on its own fresh machine. Jobs run in
  parallel unless one depends on another. This workflow has two.
- **Step:** one command or action inside a job. Steps run in order, and a
  failed step stops the job, so the log points at exactly what broke.
- **Action:** a ready-made, reusable step, such as `actions/checkout`
  (download the code) or `actions/setup-python` (install Python).
- **Runner:** the virtual machine GitHub starts for each job, here Ubuntu
  24.04, thrown away afterwards. Nothing carries over between runs except
  explicit caches.
- **Service container:** a helper container a job needs, such as a
  database. Here Docker Compose starts `db` itself, exactly as on your
  machine, and it's never reachable from outside the runner.
- **Why both databases are tested:** Docker uses PostgreSQL and the host
  workflow uses SQLite, and the same code must work on both (CLAUDE.md
  forbids database-specific code). Testing only one would let the other
  break unnoticed.
- **Why versions are pinned:** a floating tag like `python:3.12-slim` or
  `ubuntu-latest` changes whenever upstream publishes a new release, so a
  run could fail, or pass, with no change in our code. Pinning makes every
  run reproducible; updating becomes a visible change in Git.
- **Secrets:** this workflow needs none. It only reads the code
  (`permissions: contents: read`), and the database values are the
  development-only ones already in `compose.yaml`.
