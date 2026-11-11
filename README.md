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

## Production image rehearsal (step 11)

The existing host and `docker compose` workflows above remain development
workflows. This separate image packages code for later deployment. It is a
local HTTP rehearsal only: **do not expose it publicly yet**. HTTPS/security
configuration and static asset delivery (including admin CSS and replacing
Tailwind Play CDN) remain for a later approved step.

- **Gunicorn** is the server process that runs Django in production. Version
  26.2.0 is pinned in production-only requirements, based on its
  [published release](https://pypi.org/project/gunicorn/26.2.0/).
  It uses two sync workers, with access/error logs in the container output.
- **Non-root** means the server runs as user 10001, without administrator
  privileges. Application code is owned by root and read by this user.
- **Baked-in code** means the image contains the application. There is no host
  source mount or live reload; rebuild after code/dependency changes.
- **DEBUG off** means errors use generic responses. Production settings reject
  attempts to enable debugging and refuse missing or unsafe configuration.

Create `.env.production.local` once in the project root. It is ignored by Git
and excluded from both images. Generate two distinct random values with the
host virtualenv command below; use one for the secret key and one for the
database password. Keep these values private and do not paste them into Git.

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

The file needs these keys (replace angle-bracket instructions with generated
values; do not copy the instructions as credentials):

```dotenv
DJANGO_SECRET_KEY=<generated random key>
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_DB_NAME=pms_rehearsal
DJANGO_DB_USER=pms_rehearsal
DJANGO_DB_PASSWORD=<different generated random password>
DJANGO_DEBUG=0
```

Run from PowerShell. Always include the separate project name and file, so the
rehearsal has its own network and database volume. It publishes only port 8001
on localhost, leaving development port 8000 alone.

```powershell
docker compose -p pms-production -f compose.production.yaml --env-file .env.production.local build
docker compose -p pms-production -f compose.production.yaml --env-file .env.production.local up -d db
docker compose -p pms-production -f compose.production.yaml --env-file .env.production.local run --rm web python manage.py migrate --noinput
docker compose -p pms-production -f compose.production.yaml --env-file .env.production.local run --rm web python manage.py check
docker compose -p pms-production -f compose.production.yaml --env-file .env.production.local run --rm web python manage.py check --deploy
docker compose -p pms-production -f compose.production.yaml --env-file .env.production.local up -d web
docker compose -p pms-production -f compose.production.yaml --env-file .env.production.local logs -f web
# Ctrl+C stops following logs. Open http://localhost:8001/
docker compose -p pms-production -f compose.production.yaml --env-file .env.production.local down
```

Migrations are an explicit command, never part of server startup. `down` keeps
the rehearsal data; adding `-v` **deletes its database volume and all data**.
Database name/user/password initialise a fresh volume only; editing the file
does not change an existing database account. Do not print resolved Compose
configuration or commit the runtime file because it contains credentials.

The image selects `config.settings_production` for Gunicorn and management
commands. Outside this rehearsal Compose file, supply `DJANGO_DB_HOST` and
optionally `DJANGO_DB_PORT` (default 5432) as well as the required variables
above. Compose supplies host `db` and port 5432. Production never falls back
to SQLite. Known development secrets/passwords, weak secret keys, wildcard
allowed hosts and invalid database ports are rejected without displaying values.
Keep the Python/PostgreSQL image pins aligned in both Docker/Compose variants.

Deployment checks intentionally report the remaining local HTTP limitations:
`security.W004` (HSTS), `security.W008` (HTTPS redirect), `security.W012`
(secure session cookie) and `security.W016` (secure CSRF cookie). These are
not suppressed. Resolve them with the actual HTTPS deployment design before
public exposure; enabling them blindly would break this local HTTP rehearsal.
Investigate any additional warning. Gunicorn does not serve Django static files;
admin styling and production frontend assets still need a delivery decision.
The two existing CI jobs remain unchanged; production-image verification is
local in this step.

## Server deployment (step 12)

The production image runs on one Linux server with Docker Compose, using
`compose.server.yaml`. It is a **private learning deployment**: plain HTTP,
listening only on the server's loopback (`127.0.0.1:8010`), reached through
an SSH tunnel. It is **not** ready for public users (see the end of this
section). Every step is manual; there is no automatic deployment.

**Build vs deployment:** *building* turns a Git revision into an image
(code baked in). *Deploying* runs that image, with server-side secrets and
a database, as containers. Since step 13, **CI builds** the image once,
verifies it and, for `main`, publishes it to GitHub Container Registry
(see Continuous integration). **The server only pulls** that exact image
(`dc pull web`) and runs it (`dc up -d`); it never builds.

### What lives on the server
| Path / object | What it is |
|---|---|
| `/opt/pms/app` | Git checkout of one CI-passed revision: supplies `compose.server.yaml` and the revision to pull |
| `/opt/pms/dc` | Helper: `docker compose -p pms -f compose.server.yaml --env-file …` |
| `/etc/pms/production.env` | Secrets and settings, root-only (`600`), outside the checkout |
| `/opt/pms/backups/` | Database backups, root-only |
| Image `ghcr.io/amanshakya28515/pms-web:<revision>` | Pulled from the registry, one per deployed revision; older ones (and step 12's local `pms-web:<revision>`) kept for recovery |
| Containers `pms-web-1`, `pms-db-1` | The running app and PostgreSQL 17 |
| Volume `pms_postgres-data` | The database files (persistence, **not** a backup) |

The code isn't under `/var/www`: nginx never serves it, and nothing reads
the checkout while the app runs (the image has its own copy).

### First-time setup (run as root on the server)
Docker and Compose: `apt-get install -y docker.io docker-compose-v2`
(check first that it suits anything else on the server). Then:

```bash
mkdir -p /opt/pms && cd /opt/pms
git clone https://github.com/AmanShakya28515/project-management-system.git app
cd app && git checkout --detach <ci-passed-commit>
```

**Secrets** (new values for the server; never printed or copied from a PC):

```bash
mkdir -p /etc/pms && chmod 700 /etc/pms && umask 077
F=/etc/pms/production.env
K=$(openssl rand -base64 48 | tr -d '\n'); P=$(openssl rand -hex 24)
printf 'DJANGO_SECRET_KEY=%s\n' "$K" > $F
printf 'DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n' >> $F
printf 'DJANGO_DB_NAME=pms\nDJANGO_DB_USER=pms\n' >> $F
printf 'DJANGO_DB_PASSWORD=%s\n' "$P" >> $F
unset K P; umask 022
```

**Helper** (so every command targets only this project):

```bash
F=/opt/pms/dc
printf '#!/bin/sh\ncd /opt/pms/app || exit 1\n' > $F
printf 'export PMS_REVISION=$(git rev-parse --short HEAD)\n' >> $F
printf 'C="-p pms -f compose.server.yaml"\n' >> $F
printf 'E="--env-file /etc/pms/production.env"\n' >> $F
printf 'exec docker compose $C $E "$@"\n' >> $F
chmod 700 $F
```

**First deployment** (migrations are always explicit, never on startup):

```bash
/opt/pms/dc pull web
/opt/pms/dc up -d db
/opt/pms/dc run --rm web python manage.py migrate --noinput
/opt/pms/dc run --rm web python manage.py check --deploy
/opt/pms/dc up -d web
```

### Everyday operation
| Task | Command |
|---|---|
| Status | `/opt/pms/dc ps` |
| Logs | `/opt/pms/dc logs --tail 50 web` (or `db`; add `-f` to follow) |
| Running revision | `/opt/pms/dc images` (the `pms-web` tag) or `git -C /opt/pms/app log --oneline -1` |
| Resource use | `docker stats --no-stream pms-web-1 pms-db-1` |
| Stop / start | `/opt/pms/dc stop` / `/opt/pms/dc start` |
| Restart | `/opt/pms/dc restart` |
| Remove containers, keep data | `/opt/pms/dc down` |

Both services restart by themselves after a server reboot
(`restart: unless-stopped`). Each is capped at 512 MB RAM and 1 CPU, and
its logs at 3 × 10 MB, because the server is shared. **Never** run
`down -v` (it deletes the database) or server-wide commands such as
`docker system prune` on a shared server.

**Open the app** from your PC (keep this window open; `Ctrl+C` closes it):

```powershell
ssh -N -L 8010:127.0.0.1:8010 root@<server-ip>
```

Then browse to <http://localhost:8010/>. Port 8010 isn't reachable from the
internet; only the tunnel reaches it.

### Backups
A volume survives restarts, but not a lost disk, a deleted server or a
mistaken `down -v`. Take a backup before every update:

```bash
umask 077; mkdir -p /opt/pms/backups
B=/opt/pms/backups/pms-$(date +%Y%m%d-%H%M).dump
D='pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'
/opt/pms/dc exec -T db sh -c "$D" > $B; umask 022; ls -l $B
```

Keep a copy off the server (PowerShell, in a private folder outside the
project): `scp "root@<server-ip>:/opt/pms/backups/*.dump" .`

**Test a restore** into a throwaway database (no ports, deleted after;
the live database is never touched):

```bash
N=pms-restore-test
docker run -d --name $N -e POSTGRES_PASSWORD=x postgres:17.11-trixie
until docker exec $N pg_isready -h 127.0.0.1; do sleep 1; done
docker exec -i $N pg_restore -U postgres -d postgres \
  --create --no-owner --no-privileges < $B
docker exec $N psql -U postgres -d pms -c "select name from workspaces_workspace;"
docker rm -f -v $N
```

Backups contain user data and password hashes: keep them private. There's
no automatic schedule or retention; this is a manual, learning setup.

### Updating to a new revision
Only deploy a commit on `main` whose CI run passed, so its image is published.

1. **Back up** (above).
2. **Fetch and select:** `cd /opt/pms/app && git fetch && git checkout --detach <commit>`.
3. **Pull:** `/opt/pms/dc pull web` downloads the image CI verified for
   that commit. Nothing is built on the server. The old image stays for
   recovery.
4. **Migrate:** `/opt/pms/dc run --rm web python manage.py migrate --noinput`,
   and read its output.
5. **Recreate the app:** `/opt/pms/dc up -d web`.
6. **Check:** `/opt/pms/dc ps`, the logs, and the app through the tunnel.

**Downtime:** a few seconds while `web` is recreated (step 5). Migrations
that change existing tables can lengthen it.

**No published image for this revision** (`pull` says "not found" or
"manifest unknown"): its CI run failed, is still running, or the commit
isn't on `main`. Check the Actions tab, fix and push, then deploy the new
revision. Never build on the server instead. "unauthorized" means the
package isn't public yet (see Continuous integration). The tag is the
7-character revision; if `git rev-parse --short` ever prints more, use
`--short=7` in the helper.

**Recovery:** if the new revision misbehaves and it added **no**
migrations, check out the old commit and run `/opt/pms/dc up -d web`; the
old image is reused, nothing is downloaded or built. Checking out a step 12
commit also restores its older Compose file, which names its local
`pms-web:<revision>` image. If it **did** migrate, an old
image may not work with the new schema, and old code can't safely undo
arbitrary migrations: restore the pre-update backup into the database
instead (stop `web` first), or fix forward with a new commit.

### Before this could be public
- **HTTPS** with a domain and a reverse proxy, plus the settings behind the
  four `check --deploy` warnings (HSTS, HTTPS redirect, secure session and
  CSRF cookies). None of them is suppressed.
- **Static files:** Gunicorn doesn't serve them (the admin is unstyled),
  and the Tailwind Play CDN isn't meant for production.
- SSH hardening (keys instead of root passwords) and automated, monitored
  backups.

**Removing the deployment:** `/opt/pms/dc down`, then delete `/opt/pms` and
`/etc/pms`. Delete the database too only on purpose: `docker volume rm
pms_postgres-data`.

## Monitoring (step 14)

A separate Compose project, `pms-monitoring` (`compose.monitoring.yaml`),
runs next to the app on the server and shows its health in **Grafana**.
It's private like the app: every port is on the server's loopback, and
Grafana is opened through the SSH tunnel. It changes nothing in the app,
and it can be started, stopped or removed without touching the app.

| Component | What it does | Memory cap |
|---|---|---|
| **Alloy** (collector) | Every 15 s: server CPU/memory/disk, the app's container CPU/memory, an "is the login page up?" probe; plus the app's and database's logs | 160 MB |
| **Prometheus** | Stores the numbers (metrics) for 15 days, at most 1 GB | 192 MB |
| **Loki** | Stores the logs for 7 days | 192 MB |
| **Grafana** | Dashboards, login required | 384 MB |

Only Compose project `pms` is collected (its logs and its two containers);
the server totals cover the whole VPS. This Alloy is our own container on
`127.0.0.1:12346`: the server's existing Alloy service is not touched.
Ports used: Grafana `127.0.0.1:3010`, Prometheus `127.0.0.1:9095`, Loki
`127.0.0.1:3110`.

### First-time setup (root on the server)
Check the ports are free first: `ss -ltn | grep -E ':(3010|3110|9095|12346) '`
should print nothing.

**Grafana password** (generated on the server, never printed):

```bash
umask 077; F=/etc/pms/monitoring.env
P=$(openssl rand -base64 24 | tr -d '\n')
printf 'GRAFANA_ADMIN_PASSWORD=%s\n' "$P" > $F
unset P; umask 022; ls -l $F
```

Read it when you need it with `cat /etc/pms/monitoring.env` (never paste
it anywhere). It's used only on Grafana's **first** start. To change it
later: `/opt/pms/mon exec grafana grafana cli admin reset-admin-password '<new>'`.

**Helper** `/opt/pms/mon` (like `dc`, scoped to project `pms-monitoring`):

```bash
F=/opt/pms/mon
printf '#!/bin/sh\ncd /opt/pms/app || exit 1\n' > $F
printf 'C="-p pms-monitoring -f compose.monitoring.yaml"\n' >> $F
printf 'E="--env-file /etc/pms/monitoring.env"\n' >> $F
printf 'exec docker compose $C $E "$@"\n' >> $F
chmod 700 $F
```

**Start:** `/opt/pms/mon pull` then `/opt/pms/mon up -d`.

### Everyday operation
| Task | Command |
|---|---|
| Status | `/opt/pms/mon ps` |
| Logs of one component | `/opt/pms/mon logs --tail 50 grafana` (or `alloy`, `loki`, `prometheus`) |
| Resource use | `docker stats --no-stream` (the `pms-monitoring-*` rows) |
| Stop / start (data kept) | `/opt/pms/mon stop` / `/opt/pms/mon start` |
| Apply a changed configuration | `/opt/pms/mon up -d` |
| Update to new pinned versions | check out the new commit, then `/opt/pms/mon pull` and `/opt/pms/mon up -d` |
| Remove containers, keep data | `/opt/pms/mon down` |
| Remove everything incl. history | `/opt/pms/mon down -v` (deletes **only** monitoring data, never the app's) |

The app's `dc` commands and update routine are unchanged. Both projects use
the same checkout `/opt/pms/app`: if you check out a commit from before step
14 (to recover the app), `mon` commands fail until you check out a step 14+
commit again. The running monitoring containers keep running meanwhile.

### Open Grafana
Add Grafana's port to the tunnel (PowerShell on your PC):

```powershell
ssh -N -L 8010:127.0.0.1:8010 -L 3010:127.0.0.1:3010 root@<server-ip>
```

Browse to <http://localhost:3010/>, log in as `admin`, and open
**Dashboards → PMS → PMS monitoring**.

| Row | Panel | How to read it |
|---|---|---|
| Uptime | App status, Up / down over time | Green UP = the login page answered 200 within 5 s (checked every 15 s); red DOWN shows within about a minute |
| Uptime | Login page response time | Normally a few milliseconds; rising values mean the app is struggling |
| Containers | CPU | Cores used by `pms-web-1` / `pms-db-1` (each capped at 1.0) |
| Containers | Memory | Use against the dashed 512 MB limit line; near the line means risk of being killed |
| Server | CPU, memory, disk, load | The whole VPS, all sites together: is there room left? |
| Logs | Logs | Pick a service (web/db) and type in **Search logs**; e.g. `GET /accounts` or `error` |

Dashboards and data sources come from `monitoring/grafana/` in the
repository: changes made in the browser can't be saved. Edit the files and
run `/opt/pms/mon up -d` instead.

**Never on the shared server:** `docker system prune`, `volume prune`, or
anything not scoped to `pms-monitoring`/`pms`. `mon down -v` is safe only
because it is scoped to the monitoring project.

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

**What a run checks:** three jobs run in parallel, and the run passes only
if all pass. The two test jobs run the three checks in this order,
stopping at the first failure:

1. migration drift (`makemigrations --check --dry-run`);
2. the system check (`check`);
3. the full test suite (`test`).

| Job | Database | How it runs |
|---|---|---|
| PostgreSQL (Docker Compose) | PostgreSQL 17 in the `db` service | builds the image, then `docker compose run --rm web python manage.py …` |
| SQLite (Python 3.12) | SQLite | Python 3.12 on the runner, `pip install -r requirements.txt`, then `python manage.py …` |
| Production image | PostgreSQL 17, throwaway | builds `Dockerfile.production`, runs it with `compose.server.yaml` (the server's file) and a throwaway env file, then checks: migrations apply, `check --deploy` shows exactly W004/W008/W012/W016, the login page answers 200, the app runs as UID 10001, the log has no `ERROR`, the image holds no secrets |

**Publishing (step 13):** on a push to `main`, when all three jobs pass, a
fourth job, *Publish the image*, pushes the very image the production job
verified (it is handed over, never rebuilt) to GitHub Container Registry
as `ghcr.io/amanshakya28515/pms-web:<7-character revision>`. Branches and
pull requests build and verify the image but never publish it. Every
commit on `main` gets a finished run; on other branches a newer push
cancels the older run. The published revisions are listed on the
repository page under **Packages → pms-web**.

**One-time setting:** a package first published by a workflow is
private. On GitHub open the package → Package settings → Change
visibility → **Public**, so the server can pull without logging in.

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

**Versions are pinned:** the runner (`ubuntu-24.04`), the actions (major
tags: `checkout`/`setup-python`/`upload-artifact` `@v7`,
`download-artifact` `@v8`),
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
- **Secrets:** this workflow stores none. Jobs only read the code
  (`permissions: contents: read`). The production job generates throwaway
  values on the runner, masked in the log. Only the publish job may write
  packages, using the run's own short-lived `GITHUB_TOKEN`; GitHub gets no
  access to the server.

## Container registry concepts in plain language

- **Registry:** a storage place for images, like GitHub for code. We use
  GitHub Container Registry (`ghcr.io`), next to the repository.
- **Image name and tag:** `ghcr.io/amanshakya28515/pms-web:<revision>`:
  registry / owner / image name, then the tag after `:`. The tag is the
  commit's revision, so every image says which code it holds. There's no
  `latest` tag: the server always asks for an exact revision.
- **Push / pull:** CI *pushes* (uploads) an image; the server *pulls*
  (downloads) it. Public means anyone can pull, with no login; only this
  repository's workflow can push.
- **Build once, run everywhere:** the image the server runs is
  byte-for-byte the one CI tested. Before step 13 the server built its own
  image, which CI had never seen (step 12's stray-character bug, Q-82).
- **Continuous delivery vs deployment:** CI now *delivers* a ready,
  tested image; a person still decides when to *deploy* it (`dc pull`,
  `migrate`, `up -d web`). Automatic deployment would be its own step.

## Monitoring concepts in plain language

- **Metrics:** numbers measured over time, such as "CPU used" every 15
  seconds. Stored in Prometheus and drawn as graphs.
- **Logs:** the text lines a program prints. Stored in Loki, searched in
  Grafana. Metrics tell you *that* something is wrong; logs tell you *why*.
- **Collector / scraping:** a program that reads the measurements at a fixed
  interval ("scrapes" them) and sends them on. Here that is Alloy.
- **Exporter:** a small piece that turns something (the server, a container,
  a web page) into metrics. Alloy has built-in exporters for the server
  (node-exporter), containers (cAdvisor) and probes (blackbox).
- **Probe:** an outside check that does what a user would do, here
  requesting the login page, and records whether it worked and how fast.
- **Retention:** how long data is kept before it's deleted (15 days of
  metrics, 7 of logs), so storage can't grow forever on a shared disk.
- **Dashboard:** a page of panels (graphs, status tiles, log views). Ours is
  defined as JSON in the repository ("dashboards as code"), so it comes
  back exactly the same on a fresh install.
- **Data source:** where Grafana reads data from (Prometheus for metrics,
  Loki for logs).
