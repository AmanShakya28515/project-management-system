# Project Management System

A web-based project management app built with Django 5.2. Teams create
workspaces, add members, create projects and tasks, assign tasks and track
their status.

It is also a hands-on DevOps learning project. Step 08 adds Git and Docker.
PostgreSQL, CI/CD, monitoring and Kubernetes come in later steps.
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

This workflow uses `db.sqlite3` in the project folder.

## Run it with Docker

Requires Docker Desktop, which must be running. The commands below are
written for **PowerShell**; run them from the project folder.

> **Git Bash:** its MSYS path conversion rewrites container paths such as
> `/data` into Windows paths. Prefix commands that pass a container absolute
> path with `MSYS_NO_PATHCONV=1`, for example
> `MSYS_NO_PATHCONV=1 docker compose exec web ls -l /data`.

The app is reachable only from this machine (<http://localhost:8000/>). The
port is bound to `127.0.0.1` on purpose, because the development server
runs with `DEBUG` on and a development-only secret key.

> Only one app can use port 8000. Stop a host `runserver` before you start
> the container, and the other way round.

| Task | Command |
|---|---|
| Build the image | `docker compose build` |
| Start the app (in the background) | `docker compose up -d` |
| First run: create the tables | `docker compose exec web python manage.py migrate` |
| Open the app | <http://localhost:8000/> |
| View logs (Ctrl+C to stop following) | `docker compose logs -f web` |
| Stop the app (the data is kept) | `docker compose down` |
| Run migrations | `docker compose exec web python manage.py migrate` |
| System check | `docker compose exec web python manage.py check` |
| Full test suite | `docker compose exec web python manage.py test` |
| Open a shell in the container | `docker compose exec web bash` |
| Django's Python shell | `docker compose exec web python manage.py shell` |
| Create an admin user | `docker compose exec web python manage.py createsuperuser` |

You only need to rebuild (`docker compose build`) when `requirements.txt` or
the `Dockerfile` changes. Code and template edits show up straight away.

### The container's database

The container keeps its SQLite database at `/data/db.sqlite3`, in a Docker
volume called `sqlite-data`. It is **separate** from the host's
`db.sqlite3`, so users created in Docker don't exist in the `.venv`
workflow, and the other way round.

- **Inspect it:**
  - `docker compose exec web ls -l /data` shows the file.
  - `docker compose exec web python manage.py shell`, then
    `from accounts.models import User; User.objects.count()` queries it.

  The slim image has no `sqlite3` command-line tool, so
  `manage.py dbshell` won't work there.
- **Reset it (deletes all container data):**
  ```powershell
  docker compose down -v          # -v also removes the sqlite-data volume
  docker compose up -d
  docker compose exec web python manage.py migrate
  ```

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
- **Volume:** `sqlite-data:/data` is storage managed by Docker that outlives
  containers. The database lives there, so it survives `docker compose down`
  and is never baked into the image. `docker compose down -v` deletes it.
- **Environment variables:** settings passed to the container at run time
  (`DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_SQLITE_PATH`). Django reads them in `config/settings.py`. The
  values in `compose.yaml` are for development only. A real secret never
  goes in a tracked file.
- **Docker Compose:** describes how to run the app (image, ports, mounts,
  environment) in one file, `compose.yaml`. Short commands like
  `docker compose up` replace long `docker run` command lines.
- **Running Django commands in a container:**
  `docker compose exec web <command>` runs a command inside the running
  `web` container, with the same Python, settings and database as the app.
  Use `docker compose run --rm web <command>` when the app isn't running.
