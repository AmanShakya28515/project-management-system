---
step: 08
slug: containerize
status: done
created: 2026-10-07
approved: 2026-10-10
---

# 08 — Version control and Docker
  
## Goal
The project is under Git, and the existing app runs, migrates, checks and
passes its full test suite inside a Docker container on the developer's
Windows machine, with no change in behaviour.

## Context / why now
Steps 01–07 delivered a working, well-tested app (403 tests). That makes it
ready for the project's second goal, the DevOps phase. CLAUDE.md held back
Git and Docker until asked, and this step brings both in.

Already in place:
- a basic `.gitignore` from step 01;
- configuration read from the environment (`DJANGO_SECRET_KEY`,
  `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`);
- Docker installed on the dev machine (version 29.5).

## Acceptance criteria

### Version control
- **AC-1** Given the project, then it is a Git repository. Its ignore rules
  keep out the virtual environment, local database files, Python caches,
  environment or secret files, and other generated development files. After
  setup, Git lists none of those as files to track.
- **AC-2** Given the tracked files, then they contain no real secret. The
  secret key comes only from the environment, and the local fallback is
  still clearly labelled insecure.

### Image and container
- **AC-3** Given the repository, when the image is built with one documented
  command, then it builds successfully on Python 3.12 and installs
  dependencies from `requirements.txt` only.
- **AC-4** Given an image build, then the build context leaves out the
  virtual environment, local database files, Git metadata, caches and secret
  files, so none of them end up inside the image.
- **AC-5** Given the Compose configuration, when the app is started with one
  documented command, then the development server runs in a container and
  the app (for example the login page) is reachable from a browser on the
  host machine.
- **AC-6** Given a running development container, when application code is
  edited on the host, then the running app picks up the change without
  rebuilding the image (see OQ-2).

### Data and configuration
- **AC-7** Given local data created while using the containerised app, when
  the container is stopped, removed and started again, then the data is
  still there. The SQLite database is never baked into the image.
- **AC-8** Given the container, then Django reads its settings from
  environment variables provided at run time. No production secret is
  written into any Docker or Compose file; development values are clearly
  development-only.

### Running Django inside the container
- **AC-9** Given the running setup, when migrations are run inside the
  container, then they apply successfully.
- **AC-10** Given the running setup, when Django's system check runs inside
  the container, then it reports no issues.
- **AC-11** Given the running setup, when the full test suite runs inside the
  container, then every test passes (currently 403).

### Unchanged behaviour and documentation
- **AC-12** Given the finished step, then application behaviour is
  unchanged, and the existing host workflow with the project virtualenv
  (`.venv`) still works exactly as documented in CLAUDE.md.
- **AC-13** Given the project documentation, then it explains, with Windows
  in mind, how to:
  - build the image;
  - start and stop the app;
  - view logs;
  - run migrations, the system check and the tests;
  - open a shell in the app container;
  - reset or inspect the local database.

  It also explains the step's learning concepts in plain language: images,
  containers, layers, the build context and `.dockerignore`, port mapping,
  volumes and bind mounts, environment variables, Compose, and running
  Django commands in a container (see OQ-3).

## Out of scope
- PostgreSQL, Redis, Celery, Nginx, Gunicorn or any production server, HTTPS
- Production images, deployment, CI/CD, monitoring and Kubernetes
- Pushing to a remote Git host (GitHub and so on)
- Any change to application features, settings behaviour or dependencies
- Frontend build tooling (the Tailwind CDN stays)

## Open questions
Each comes with a proposed answer, and the acceptance criteria assume it.

- **OQ-1 Commits.**
  **Decision:**
  - `/build` initializes the Git repository and prepares the ignore rules.
  - `/build` does not create a commit automatically.
  - After verification passes, the user decides when to make the first commit.
  - Suggested initial commit message: `08: containerize`.

  → AC-1
- **OQ-2 Live code reload in development.** *Proposed:* yes. The development
  container uses the code on the host, so edits show up without a rebuild,
  which matches today's `runserver` experience. The image still contains a
  copy of the code, so it can also run on its own. → AC-6
- **OQ-3 Where the documentation lives.** *Proposed:* a new `README.md` at
  the repository root: what the project is, how to run it with `.venv` or
  Docker, the command list, and a short "Docker concepts" section. CLAUDE.md
  gets only a brief pointer and the new commands. → AC-13
