# Step 08 — Version control and Docker: learning notes

What was built in step 08, **how** it works, **why** it was done that way, and what is in and out of scope. The official records are the spec (`.claude/specs/08-containerize.md`), the plan (`.claude/plans/08-containerize.md`), `CLAUDE.md` and the root `README.md`; this file explains them in teaching order.

## Contents

1. [What we did in step 08, and why](#1-what-we-did-in-step-08-and-why)
2. [Git: the repository and `.gitignore`](#2-git-the-repository-and-gitignore)
3. [The image: `Dockerfile` and `.dockerignore`](#3-the-image-dockerfile-and-dockerignore)
4. [Running it: `compose.yaml`](#4-running-it-composeyaml)
5. [Data and settings: volumes and environment variables](#5-data-and-settings-volumes-and-environment-variables)
6. [How we proved it works, and what the review caught](#6-how-we-proved-it-works-and-what-the-review-caught)
7. [Scope: what is in, what is out, and what comes next](#7-scope-what-is-in-what-is-out-and-what-comes-next)
8. [Hands-on exercises](#8-hands-on-exercises)

---

## 1. What we did in step 08, and why

### The one-sentence version
We put the project under **Git**, and made the **unchanged** Django app run,
migrate, check and pass all 403 tests inside a **Docker container** on
Windows.

### Why this step came now
The project has two goals, in order:
1. build a real, well-tested app;
2. use it to learn DevOps.

Steps 01–07 finished the first goal well enough: auth, workspaces, projects,
tasks, assignment and status, with 403 tests. A DevOps step needs a working
app to package; you can't learn deployment on something that doesn't work.
So step 08 is the bridge: it takes the app as it is and puts it in a box.

The DevOps road in `CLAUDE.md`:

```
Docker (08) → PostgreSQL → CI/CD → deployment → monitoring/Grafana → Kubernetes
```

Each later step depends on this one:
- **PostgreSQL** will be a second container next to ours.
- **CI** will build the same image.
- **Kubernetes** runs containers.

### What changed (and what didn't)

| File | New or changed | Purpose |
|---|---|---|
| `.git/` | new | Git is set up (`git init -b main`) |
| `.gitignore` | changed | Keeps local, secret and generated files out of Git |
| `Dockerfile` | new | The recipe for the image |
| `.dockerignore` | new | What Docker must not copy into the image |
| `compose.yaml` | new | How to run the container: ports, mounts, settings |
| `config/settings.py` | changed (one setting) | `DJANGO_SQLITE_PATH`, so the container can keep its database elsewhere |
| `README.md` | new | Commands and plain-language concepts |
| `CLAUDE.md` | changed | Lasting rules for future steps |

**No application code changed:** no models, views, templates, migrations or
tests. That was a requirement (AC-12). A packaging step that also changes
behaviour makes it impossible to tell which change broke what.

### The big picture

```
 Your Windows machine                        Docker (Linux VM inside Docker Desktop)
 ─────────────────────                       ──────────────────────────────────────
                                             ┌───────────── container "web" ─────────────┐
 Browser ── http://localhost:8000 ─────────▶ │ port 8000                                 │
           (127.0.0.1 only)                  │ python manage.py runserver 0.0.0.0:8000   │
                                             │                                           │
 D:\Project_Management_System ◀═ bind mount ═▶ /app   (your code, live)                  │
                                             │                                           │
                         named volume "sqlite-data" ═▶ /data/db.sqlite3 (survives)       │
                                             └───────────────────────────────────────────┘
                                                    built from image ◀── Dockerfile
```

### How the work flowed (the project workflow)
Even an infrastructure step went through the normal gates:

1. **Spec:** what "containerised" means, written as 13 checkable acceptance
   criteria (AC-1 to AC-13). You revised OQ-1 so that Claude makes no
   automatic commit.
2. **Plan:** the technical decisions:
   - **D-1:** no commit;
   - **D-2:** a separate database on a named volume;
   - you changed `git init` to `git init -b main`.
3. **Build:** implemented, then verified every AC by running real commands.
4. **Review:**
   - **S-5 (Medium):** the port was exposed to the network;
   - **Q-73:** a documentation mistake about Git Bash;
   - two Lows.
5. **Retest:** fixed S-5 and Q-73.
6. **Done:** `CLAUDE.md` updated, and the spec and plan closed.

The lesson: infrastructure deserves the same rigour as features. The review
found a real security exposure (see section 6).

---

## 2. Git: the repository and `.gitignore`

### What Git is, in one paragraph
Git records **snapshots** (commits) of your project over time. You can see
exactly what changed, go back, and later share the history with a server
such as GitHub. CI/CD systems start from a Git repository: "a new commit
arrived, so build and test it". That's why Git had to come before CI.

### What we ran

```powershell
git init -b main
```

- `git init` creates the hidden `.git/` folder, which is the history
  database.
- `-b main` names the first branch `main`. Without it, older Git defaults
  can call it `master`. `main` is today's convention and what GitHub
  expects. You asked for this in the plan revision.

**No commit was made.** The spec (OQ-1) decided that you make the first
commit yourself, so that you look at what goes into history first. As of
writing, `main` still has no commits. When you're ready:

```powershell
git status          # check what would be committed
git add -A
git commit -m "08: Version control and Docker"
```

### `.gitignore`: what must never enter history

```gitignore
.venv/                          # the virtualenv: big, machine-specific, rebuildable
db.sqlite3*  *.sqlite3  *-journal   # local databases: personal data, not code
.env  .env.*  *.local           # secrets and per-machine settings
.claude/settings.local.json     # personal Claude Code settings
__pycache__/  *.py[cod]         # compiled Python: generated on every run
.pytest_cache/ .mypy_cache/ htmlcov/   # tool output (for later steps)
.idea/ .vscode/ *.log .DS_Store # editor, log and OS clutter
```

**The rule of thumb:** track what a teammate needs to rebuild the project,
and ignore what can be regenerated, is personal, or is secret.

Why each one matters:
- **`.venv/`** holds hundreds of megabytes of Windows-specific files.
  Anyone can recreate it with `pip install -r requirements.txt`.
- **`db.sqlite3`** would put real user accounts and password hashes in
  history, forever. Git history is very hard to truly erase.
- **`.env`** is where a real secret would live. Committing it once leaks
  it, even if you delete it later.

### How we checked it (AC-1)

```powershell
git status --ignored                          # lists what is ignored (!!) and untracked (??)
git ls-files --others --exclude-standard      # what Git *would* add
git symbolic-ref --short HEAD                 # shows "main", even before the first commit
```

The result: `.venv/`, `db.sqlite3` and every `__pycache__/` showed as
ignored, and nothing secret-looking was offered for tracking.

### Secrets (AC-2)
We searched the files Git would track for `SECRET_KEY`-like strings. There
are only two, and both are **deliberately fake and labelled**:
- `config/settings.py`: the fallback `django-insecure-dev-only-change-me`;
- `compose.yaml`: `django-insecure-docker-dev-only`.

The `django-insecure-` prefix is Django's own convention. Its
`check --deploy` warns about it, so nobody can mistake it for a real key.

### How Git changes the workflow
Before step 08, the plan's "Files changed" list was the only record of what
a step touched. Now reviewers use `git diff` and `git status` and
cross-check that list. `CLAUDE.md` was updated to say so. Claude still
commits only when you ask.

---

## 3. The image: `Dockerfile` and `.dockerignore`

### Image vs container
- An **image** is a frozen, read-only package: a small Linux system, Python,
  Django and our code. Think of it as a class.
- A **container** is a running instance of an image. Think of it as an
  object. You can delete a container and start a fresh one from the same
  image at any time.

### The `Dockerfile`, line by line

```dockerfile
FROM python:3.12-slim
```
This is the starting point: an official image with Debian Linux and
Python 3.12 already installed.
- **Why 3.12:** the stack rule in `CLAUDE.md`. It matches the host
  virtualenv, so "works on my machine" means the same thing in both
  places.
- **Why `-slim`:** it has fewer packages than the full image, so it's
  smaller and has less to patch. The trade-off is that it has no `sqlite3`
  command-line tool, which is why the README inspects the database with
  `manage.py shell` instead of `dbshell`.

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
```
- `PYTHONDONTWRITEBYTECODE=1` stops Python writing `.pyc` files. Our code is
  bind-mounted from Windows (see section 4), so without this the container
  would litter your project with `__pycache__` folders.
- `PYTHONUNBUFFERED=1` makes `print` and log output appear immediately in
  `docker compose logs`, instead of waiting in a buffer.

```dockerfile
WORKDIR /app
```
Every later instruction, and every `docker compose exec` command, runs in
`/app`. The directory is created if it doesn't exist.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```
**This ordering is the most important idea in the file.**
- Each instruction makes a **layer**, and Docker caches layers.
- If a layer's inputs haven't changed, Docker reuses it instead of
  re-running it.
- We copy *only* `requirements.txt` first and install Django. That layer
  depends only on `requirements.txt`.
- Then we copy the code. Editing a view changes only the last layer, so a
  rebuild takes seconds rather than reinstalling everything.
- If we had written `COPY . .` first, *any* code change would make Docker
  reinstall all dependencies.

`--no-cache-dir` stops pip keeping its download cache inside the image,
which keeps the image smaller. Dependencies still come **only** from
`requirements.txt` (AC-3). We verified that `pip list` in the container
shows just Django 5.2.18, asgiref, sqlparse and pip.

```dockerfile
EXPOSE 8000
```
This is documentation: "this container listens on 8000". It does **not**
open the port to your machine. Compose's `ports:` does that (section 4).

```dockerfile
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```
This is the default command when a container starts.
- **Why `0.0.0.0`:** inside a container, `127.0.0.1` means "this container
  only". Traffic from Docker's port forwarding arrives on the container's
  network interface, so Django must listen on all interfaces (`0.0.0.0`)
  *inside* the container. Section 4 explains how we still keep it private on
  your machine.
- **Why the exec form `[...]`:** the process runs directly, without a shell
  wrapper, so it receives the stop signal from `docker compose down`
  properly.

#### What this image deliberately is *not*
It runs Django's **development** server, as **root**. That's fine for local
learning, and wrong for production. A production image (Gunicorn, a
non-root user, hardening) is a later DevOps step. The `Dockerfile` says so
in its header comment.

### `.dockerignore`: the build context

When you run `docker compose build`, Docker first sends the **build
context** (by default, the whole project folder) to the Docker engine.
`COPY . .` copies from that context. `.dockerignore` filters it.

We exclude:

| Excluded | Why |
|---|---|
| `.git`, `.gitignore`, `.claude/` | History and workflow files: useless at runtime, and they change often (they'd break the layer cache) |
| `.venv/` | A *Windows* virtualenv; it can't even run on Linux |
| `db.sqlite3*`, `*.sqlite3`, `*-journal` | The database must **never** be baked into an image (AC-7) |
| `__pycache__`, `*.py[cod]`, tool caches | Generated junk |
| `.env`, `.env.*`, `*.local` | Secrets must never go into an image: anyone who has the image can read them |
| `Dockerfile`, `.dockerignore`, `compose.yaml`, root `*.md` | Not needed to *run* the app |

**Kept on purpose:** `design-system/`. The test `core/tests/test_ui.py`
reads `MASTER.md`, so the tests would fail in a standalone container
without it. The plan caught this before the build.

#### `.gitignore` vs `.dockerignore`: they answer different questions
- `.gitignore` answers: what should **never be in history**?
- `.dockerignore` answers: what should **not go into the runtime image**?

So `.dockerignore` excludes everything `.gitignore` does, **plus** tracked
files that are useful in Git but pointless in an image: `.git` itself,
the docs and the Docker files.

#### How we proved it (AC-4)

```powershell
docker run --rm project_management_system-web ls -a /app
```
`/app` contained only the app folders, `design-system/`, `manage.py` and
`requirements.txt`. A `find` showed no `.git`, `.venv`, database, `.env`,
`__pycache__` or `.pyc` files, and `/data` doesn't exist in the image.

---

## 4. Running it: `compose.yaml`

### Why Compose instead of `docker run`
Without Compose, starting our container would take one long command:

```powershell
docker run -d -p 127.0.0.1:8000:8000 -v ${PWD}:/app -v sqlite-data:/data `
  -e DJANGO_DEBUG=1 -e DJANGO_SECRET_KEY=... -e DJANGO_ALLOWED_HOSTS=... `
  -e DJANGO_SQLITE_PATH=/data/db.sqlite3 project_management_system-web
```

Compose writes that down **once**, in a file that lives in Git, and
reduces it to `docker compose up -d`. It also manages **several services**
together. That will matter in the PostgreSQL step, where a `db` service
joins `web`.

### The file, block by block

```yaml
services:
  web:
    build: .
```
There is one service, named `web` (that's why the commands say
`docker compose exec web …`). `build: .` means "build the image from the
`Dockerfile` in this folder". Compose names the image
`project_management_system-web`, after the folder and the service.

```yaml
    ports:
      - "127.0.0.1:8000:8000"  # host:container, this machine only
```
**Port mapping**, in the form `host-ip:host-port:container-port`. A
request to port 8000 on your machine is forwarded to port 8000 in the
container.

The `127.0.0.1` prefix was a **review fix (S-5)**:
- The first version said just `"8000:8000"`.
- Docker then publishes on **every** network interface (`0.0.0.0`), so
  anyone on your Wi-Fi could reach the app.
- That app runs with `DEBUG=1` (detailed error pages) and a secret key
  that is published in Git.
- `ALLOWED_HOSTS` does not protect you: it checks the `Host` header, which
  any client can set to `localhost`.

Two different `0.0.0.0`s are involved, and they're easy to confuse:

| Where | Setting | Meaning |
|---|---|---|
| Inside the container | `runserver 0.0.0.0:8000` | Accept traffic arriving from Docker's forwarding. **Required.** |
| On your Windows machine | `127.0.0.1:8000:8000` | Forward only traffic from this machine. **Keeps it private.** |

```yaml
    volumes:
      - .:/app               # bind mount
      - sqlite-data:/data    # named volume
```
There are two different kinds of mount here:
- **The bind mount `.:/app`:** your project folder on Windows *appears* as
  `/app` in the container. It is a live view, not a copy, and it hides the
  code that `COPY . .` baked into the image. Edit a file in VS Code and
  the container sees it at once. Django's auto-reloader (StatReloader,
  which checks file timestamps) restarts the server. That is how **live
  reload** works (AC-6) without rebuilding the image.
- **The named volume `sqlite-data:/data`:** storage that Docker manages,
  living inside Docker's Linux VM, not in your project folder. It survives
  when containers are deleted. Section 5 explains why the database lives
  here.

The image *also* contains a copy of the code (from `COPY . .`). The bind
mount is a development convenience on top; the image can still run on its
own, without your folder. Later, CI and production use the image alone.

```yaml
    environment:
      DJANGO_DEBUG: "1"
      DJANGO_SECRET_KEY: "django-insecure-docker-dev-only"
      DJANGO_ALLOWED_HOSTS: "localhost,127.0.0.1"
      DJANGO_SQLITE_PATH: "/data/db.sqlite3"
```
These are **environment variables** given to the container at run time.
Section 5 explains how Django reads them.

```yaml
volumes:
  sqlite-data:
```
This declares the named volume. Docker creates it on first `up`; its real
name is `project_management_system_sqlite-data`.

### The life cycle

| Command | What happens |
|---|---|
| `docker compose build` | Builds or rebuilds the image (only needed when `requirements.txt` or the `Dockerfile` changes) |
| `docker compose up -d` | Creates the network and container and starts them in the background (`-d` = detached) |
| `docker compose logs -f web` | Follows the server output (Ctrl+C stops following, not the server) |
| `docker compose exec web <cmd>` | Runs a command **inside the running** container |
| `docker compose run --rm web <cmd>` | Starts a **new, temporary** container for one command (when the app isn't running) |
| `docker compose down` | Stops and **deletes** the container and network; the volume is kept |
| `docker compose down -v` | The same, **and deletes the volume**, which wipes the container's database |

"Delete the container" sounds scary, but it's normal. Containers are meant
to be disposable. Anything worth keeping lives in a volume or in your
bind-mounted folder.

### Windows notes we learned the hard way
- **Docker Desktop must be running.** The first build failed with
  `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`.
  That's the Windows pipe to the Docker engine; nothing is listening until
  Docker Desktop starts.
- **Git Bash rewrites paths (finding Q-73).** Git Bash (MSYS) turns
  arguments like `/data` into `C:/Program Files/Git/data` before Docker
  sees them. Our own first check failed with
  `ls: cannot access 'C:/Program Files/Git/app'`. In Git Bash, prefix such
  commands:
  ```bash
  MSYS_NO_PATHCONV=1 docker compose exec web ls -l /data
  ```
  PowerShell doesn't do this, so the README is PowerShell-first.
- **One port, one app.** A host `runserver` and the container can't both
  use port 8000. Stop one before starting the other.

---

## 5. Data and settings: volumes and environment variables

### Configuration through environment variables
Since step 01, `config/settings.py` reads its important settings from the
environment, with safe local defaults:

```python
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-only-change-me')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [... os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1') ...]
```

That early decision paid off now. Containerising needed **no rewrite**,
only different values supplied from outside. It's the "config in the
environment" rule from the Twelve-Factor App:
- **the same image** runs in development, CI and production;
- only the environment changes;
- a secret is never built into the image.

We proved it (AC-8) with `docker compose exec web env`, which listed the
four `DJANGO_*` values from `compose.yaml`. The `Dockerfile` itself sets
no Django settings.

**Where real secrets will go later:** never in `compose.yaml`, which is
tracked by Git. Use a `.env` file (ignored by both Git and Docker) or the
secret store of the CI or hosting platform.

### The one settings change: `DJANGO_SQLITE_PATH` (plan decision D-2)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # Defaults to the project folder; Docker points this at a named volume.
        'NAME': os.environ.get('DJANGO_SQLITE_PATH', BASE_DIR / 'db.sqlite3'),
    }
}
```

- **On the host** (the `.venv` workflow) the variable isn't set, so the
  default `D:\Project_Management_System\db.sqlite3` is used. Nothing
  changed for you (AC-12, verified).
- **In the container** Compose sets it to `/data/db.sqlite3`, which is on
  the named volume.

#### Why not just use the bind-mounted `db.sqlite3`?
The bind mount already makes `db.sqlite3` visible at `/app/db.sqlite3`, so
that would have needed zero settings changes. We rejected it for three
reasons:
1. **SQLite depends on file locking**, to stop two writers corrupting the
   file. File locking across a Docker Desktop bind mount from a Windows
   drive is unreliable and slow. A named volume lives on Docker's own
   Linux filesystem, where locking works properly.
2. **Separation.** Host experiments and container experiments don't
   overwrite each other. We checked: a user created in the container did
   **not** appear in the host database.
3. **Learning.** It gives "volume" a real job, next to the "bind mount"
   that serves code.

**The trade-off:** there are two databases, so a user registered in Docker
can't log in to the `.venv` version, and the other way round. That is
deliberate and documented.

### Bind mount vs named volume

| | Bind mount (`.:/app`) | Named volume (`sqlite-data:/data`) |
|---|---|---|
| Lives in | your Windows folder | Docker's Linux VM |
| You manage it with | Explorer, VS Code | `docker volume ls`, `docker compose down -v` |
| Good for | **code** you edit | **data** the app writes |
| Survives `docker compose down` | yes (it's your folder) | yes |
| Deleted by | you | `docker compose down -v` |

### Proving persistence (AC-7)

1. In the container: created user `persist08`.
2. Ran `docker compose down`; zero containers remained.
3. Ran `docker compose up -d`, a brand-new container.
4. The user still existed, in `/data/db.sqlite3`.
5. Deleted the test user afterwards.

The other half of AC-7, "never baked into the image", was proved in note
03: there's no database in the image, and no `/data` in the image at all.
The volume is attached only at run time.

### Inspecting and resetting the container's data

```powershell
docker compose exec web ls -l /data                     # the file is there
docker compose exec web python manage.py shell          # then: from accounts.models import User; User.objects.count()
docker compose down -v                                  # DELETE the volume (all container data)
docker compose up -d
docker compose exec web python manage.py migrate        # recreate the empty tables
```

### Looking ahead
SQLite in a volume is a stepping stone. In the PostgreSQL step, the
database becomes its **own container** (a `db` service) with its own
volume, and `web` connects to it over the Compose network. The
environment-variable pattern stays the same: only a `DATABASE_*`
configuration is added.

---

## 6. How we proved it works, and what the review caught

### Verifying infrastructure: commands, not unit tests
Steps 01–07 proved behaviour with Django tests. Step 08's acceptance
criteria are about the **environment**, so each one was proved by running
a real command and recording the output in the plan. The 403 existing
tests acted as the "nothing broke" check, run **twice**: on the host and
in the container.

| AC | What it means | Proof |
|---|---|---|
| AC-1 | Git, with sensible ignores | `git status --ignored`; branch is `main` |
| AC-2 | No real secrets tracked | Searched the trackable files: only the two `django-insecure-` placeholders |
| AC-3 | Builds on Python 3.12 from `requirements.txt` | `docker compose build`; Python 3.12.15; `pip list` |
| AC-4 | No junk or secrets in the image | `ls -a /app` and `find` inside the image |
| AC-5 | Reachable from the browser | `curl http://localhost:8000/accounts/login/` → 200 |
| AC-6 | Live reload | Edited a template, then a `.py` file; `logs` showed `/app/core/views.py changed, reloading.` |
| AC-7 | Data survives | User `persist08` survived `down` and `up` |
| AC-8 | Settings from the environment | `exec web env` |
| AC-9/10 | `migrate` and `check` inside | Migrations applied; no issues |
| AC-11 | Full suite inside | **403 tests OK** (47 s) |
| AC-12 | Host unchanged | Host drift clean, `check` clean, **403 OK** |
| AC-13 | Documentation | `README.md` covers every command and concept |

### Small lessons from verification

**1. Checks can fail for reasons that have nothing to do with the app.**
- `docker compose build` failed at first because Docker Desktop wasn't
  running.
- `ls /app` failed because Git Bash had rewritten the path.

Neither was an app bug. Read the error before assuming the code is wrong.

**2. A failed check can be the check's own fault.** The first live-reload
test said "not working".
- The marker had been appended *after* `{% endblock %}`.
- In a Django child template, anything outside a block is ignored.
- With the marker moved inside `{% block content %}`, it appeared.

Before concluding "the feature is broken", make sure the experiment was
valid.

**3. Clean up after experiments.** The edited template and `views.py` were
restored, and `cmp` confirmed they were identical to before. The test user
was deleted.

### What the review caught

| ID | Severity | Finding | Outcome |
|---|---|---|---|
| **S-5** | Medium | `"8000:8000"` published the DEBUG server, with its public dev key, on every network interface | **Fixed:** `127.0.0.1:8000:8000` |
| **Q-73** | Low | The docs claimed the commands "work the same in Git Bash", which is false because of path rewriting | **Fixed:** PowerShell-first, plus one Git Bash note |
| **Q-74** | Low | `python:3.12-slim` is a floating tag, so rebuilds can change the base | **Deferred** to the CI/CD step (pin a tag or digest) |
| **Q-75** | Low | `CLAUDE.md` still said "don't add Docker" | **Fixed** at `/done` |

#### The key lesson: S-5
The app worked perfectly, and the browser reached it. That is exactly why
the problem was invisible: **reachable from me** looked like success, but
the real question was **reachable from whom?** Docker's default
publishing is permissive, and many tutorials use `"8000:8000"` without
comment. For anything running in DEBUG or with a known key, bind to
`127.0.0.1`.

After the fix, the measurement was:
- `docker compose port web 8000` → `127.0.0.1:8000`;
- `localhost` and `127.0.0.1` → 200;
- a non-loopback address on the machine → refused.

#### Q-74 in plain words
`FROM python:3.12-slim` is like saying "the latest 3.12 slim, whatever
that is today". Build next month and you might get a newer Python patch
release or Debian base. For development that's fine, and even helpful for
security fixes. For CI/CD you want **reproducible** builds: the same input
gives the same image. Pin an exact tag (`python:3.12.15-slim-bookworm`) or
an image digest (`@sha256:…`). That's recorded in `CLAUDE.md`'s Known
limitations.

---

## 7. Scope: what is in, what is out, and what comes next

### In scope (step 08 delivered)
- **Git:**
  - a repository on `main`;
  - ignore rules for local, generated and secret files;
  - no automatic commit.
- **A development Docker image:** Python 3.12 slim, dependencies from
  `requirements.txt` only, with a cache-friendly layer order.
- **A clean build context:** `.dockerignore`.
- **Compose:**
  - one `web` service;
  - the port published on localhost only;
  - live code reload through a bind mount;
  - SQLite on a named volume;
  - development-only environment values.
- **Django inside the container:** `migrate`, `check` and the full test
  suite all work.
- **Documentation:** the root `README.md` (commands and concepts),
  `CLAUDE.md` (lasting rules) and these learning notes.
- **Unchanged behaviour:** zero application, model, migration or test
  changes. The host `.venv` workflow is identical.

### Out of scope, and why each waits

| Not done | Why not yet | Expected step |
|---|---|---|
| PostgreSQL | Changing the database *and* containerising at once would mix two sources of failure | Next step |
| Gunicorn, Nginx, any production server | `runserver` is for development; production serving is its own topic | Production image or deployment |
| A production image (non-root user, pinned base, no bind mount, `DEBUG` off, static files) | Different goals from a dev image: security and size versus convenience | Production image or deployment |
| HTTPS and secure cookies (finding S-2) | Only meaningful once deployed | Deployment |
| Pushing to GitHub or any remote | You decide when and where the code is published | When you choose; needed before CI |
| CI/CD pipelines | Needs a remote repository and a reproducible build first (Q-74) | CI/CD |
| Monitoring, Grafana, Kubernetes | They need a deployable, observable app first | Later DevOps steps |
| Replacing the Tailwind Play CDN (Q-24) | No Node or build step allowed yet | The step that replaces the CDN |
| Redis, Celery, other services | The app doesn't need them | Only if a feature does |

**Why keep the scope this tight?** The project's learning method is **one
new tool per step**. If PostgreSQL had arrived together with Docker and
something broke, you wouldn't know which one to blame or which one you'd
actually learned. Small steps also map well to CI later: one step, one
pipeline run.

### Known limitations carried forward
- **Q-74:** a floating base-image tag; pin it in CI/CD.
- **The image is development-only:** it runs as root, uses `runserver`,
  and relies on the bind mount for live code.
- **Two separate databases:** one on the host and one in the container.
  This is deliberate.
- **S-1:** to recheck when PostgreSQL arrives. Case-insensitive login and
  the unique constraint can disagree on some Unicode letters.
- **Task ordering:** on PostgreSQL, tasks ordered by `pk` can briefly
  reorder when two are inserted at the same moment. Also revisit in the
  PostgreSQL step.

### What comes next: PostgreSQL (step 09, suggested)
A preview of how step 08's pieces get reused:
- `compose.yaml` gains a second service, `db` (the official `postgres`
  image), with **its own named volume**. You'll recognise that pattern.
- `web` connects to `db` by **service name** over the Compose network.
  This is a new concept: service discovery.
- Database settings come from **environment variables**, the same pattern
  as `DJANGO_SQLITE_PATH`.
- `requirements.txt` gains a PostgreSQL driver (`psycopg`). That's a
  dependency change, so it needs approval in the spec.
- The 403 tests become the safety net that proves the switch changed
  nothing.

---

## 8. Hands-on exercises

Run these in **PowerShell** from the project folder, with Docker Desktop
running. Each one shows one concept. Exercises 6 and 7 change things;
follow their "undo" lines.

### 1. Image vs container
```powershell
docker compose build
docker image ls project_management_system-web     # the image: one, frozen
docker compose up -d
docker compose ps                                  # the container: a running instance
```
**Question:** run `docker compose down`, then `docker image ls` again. Is
the image still there? Why?

### 2. Layer caching
```powershell
docker compose build                 # watch for "CACHED" next to the pip install step
```
Now add a blank line at the end of `requirements.txt` and build again. The
pip step re-runs. Remove the blank line afterwards.
**Question:** why does editing a `.py` file *not* re-run pip?

### 3. The build context
```powershell
docker run --rm project_management_system-web ls -a /app
```
**Question:** `README.md` and `.venv` are in your folder. Why aren't they
here? Which file decides that?

### 4. Bind mount vs image copy
```powershell
docker compose up -d
docker compose exec web ls /app        # the bind mount: you'll see README.md and .venv here!
docker run --rm project_management_system-web ls /app   # the image's own copy: you won't
```
**Question:** explain why the same path, `/app`, shows different files.

### 5. Live reload
```powershell
docker compose logs -f web
```
In VS Code, add a comment to `core/views.py` and save. Watch for
`changed, reloading`. Remove the comment afterwards.

### 6. Volumes survive, containers don't
```powershell
docker compose exec web python manage.py createsuperuser
docker compose down
docker volume ls                       # project_management_system_sqlite-data is still listed
docker compose up -d
```
Log in at <http://localhost:8000/>. The user is still there.
**Undo / reset:** `docker compose down -v`, then `up -d` and
`docker compose exec web python manage.py migrate`.

### 7. Environment variables change behaviour without a rebuild
Temporarily change `DJANGO_DEBUG: "1"` to `"0"` in `compose.yaml`, then:
```powershell
docker compose up -d                   # Compose recreates the container with the new value
```
Visit <http://localhost:8000/does-not-exist/>. You get a plain "Not Found"
page instead of Django's yellow debug page.
**Undo:** set it back to `"1"` and run `docker compose up -d`.

### 8. Port binding (S-5)
```powershell
docker compose port web 8000           # 127.0.0.1:8000
```
**Question:** if this said `0.0.0.0:8000`, who else could open the app,
and why does that matter more with `DEBUG` on?

### 9. Git ignores
```powershell
git status --ignored
git check-ignore -v db.sqlite3         # shows which .gitignore line ignores it
```

### Answers (short)
1. Yes. `down` deletes containers, not images. An image is only removed
   with `docker image rm`.
2. The pip layer depends only on `requirements.txt`. Code is copied in a
   *later* layer.
3. `.dockerignore` excludes them from the build context, so `COPY . .`
   never sees them.
4. The running container has your folder mounted *over* `/app`. A fresh
   `docker run` without the mount shows the copy baked into the image.
5. Django's StatReloader checks file timestamps, and the bind mount shows
   your edits immediately.
6. The database lives in the named volume, which `down` keeps and
   `down -v` deletes.
7. Settings are read from the environment when Django starts. A new value
   means a new container, not a new image.
8. Anyone on your network. DEBUG pages reveal code and settings, and the
   dev secret key is public in Git.
9. `git check-ignore -v` prints the `.gitignore` line and pattern that
   matched (`db.sqlite3*`).
