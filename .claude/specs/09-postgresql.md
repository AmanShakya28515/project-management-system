---
step: 09
slug: postgresql
status: done
created: 2026-10-24
approved: 2026-10-24
---

# 09 — PostgreSQL in Docker Compose

## Goal
When the app runs through Docker Compose, it uses PostgreSQL, running as a
second Compose service, instead of SQLite. All existing behaviour and
tests are unchanged.

## Context / why now
- Step 08 containerised the app with one `web` service, which uses
  SQLite on a named volume.
- PostgreSQL is the next DevOps step in CLAUDE.md. It's the database
  later deployment, CI and Kubernetes steps will use.
- CLAUDE.md held back PostgreSQL until asked, and this step brings it in.
- Two known limitations were deferred to "the PostgreSQL step": S-1 (the
  case rules for login and uniqueness can disagree) and task ordering
  under concurrent inserts.
- The code was written to be database-neutral (ORM only, no raw SQL). A
  scan found no SQLite-specific code outside the settings. Only comments
  and test notes mention SQLite's ASCII-only case folding.

The Docker and Git rules in CLAUDE.md (dev-only image, port on
`127.0.0.1`, dev-only labelled values, no automatic commits) still apply
and aren't repeated here.

## User stories
- As a developer, I want the Compose setup to run the app on PostgreSQL,
  so that development matches the database later environments will use.
- As a learner, I want to see two containers talk to each other by
  service name, so that I understand Compose networking before
  Kubernetes.

## Acceptance criteria

### Services and networking
- **AC-1** Given the Compose configuration, when the app is started with
  the documented command, then two services run: the existing `web`
  service and a new PostgreSQL service. The app is reachable from the
  host browser exactly as in step 08.
- **AC-2** Given the running setup, then `web` reaches the database
  through the database **service name** on the Compose network, not
  `localhost`. The database isn't reachable from other machines on the
  network (see OQ-2).
- **AC-3** Given a fresh start with no existing database data, when both
  services are started together, then `web` doesn't fail because the
  database isn't ready yet. After startup the app works without a manual
  restart.

### Data and configuration
- **AC-4** Given data created through the containerised app, when the
  containers are stopped, removed and started again, then the data is
  still there, in a named volume. A documented reset command removes it.
- **AC-5** Given the configuration, then:
  - the database name, user, password, host and port reach Django and
    PostgreSQL through environment variables;
  - no production credential is written into any tracked file;
  - development values are clearly labelled development-only.
- **AC-6** Given `requirements.txt`, then exactly one new direct project
  dependency is added to `requirements.txt`: the PostgreSQL driver Django
  needs (see OQ-1). It's pinned like Django, and the image builds with it.

### Django against PostgreSQL
- **AC-7** Given a fresh PostgreSQL database, when migrations run inside
  the `web` container, then all of them apply successfully.
- **AC-8** Given the running setup, when Django's system check and the
  migration-drift check run inside the container, then they report no
  issues and no changes.
- **AC-9** Given the running setup, when the full test suite runs inside
  the container, then every test passes against PostgreSQL. That's the
  current 403 plus any added in this step.
- **AC-10** Given the finished step, then application behaviour is
  unchanged on PostgreSQL, apart from the S-1 fix in AC-11.

### Deferred limitations
- **AC-11** Given two accounts whose usernames are distinct under the
  case-insensitive uniqueness rule, when anyone logs in with either
  username, in any letter case, then login never causes a server error.
  It matches using the same case rule as uniqueness (see OQ-5). The same
  holds for the email rule wherever email is matched without regard to
  case.
- **AC-12** Given tasks in a project, then they're still listed oldest
  first, in a stable order, on PostgreSQL. The concurrent-insert
  limitation is reassessed, and the decision is recorded (see OQ-6).
- **AC-13** Given the codebase, then nothing depends on SQLite-specific
  behaviour. Any SQLite-only assumption found in code or tests is fixed
  only as far as PostgreSQL compatibility needs. Comments that are now
  misleading are corrected.

### Host workflow and documentation
- **AC-14** Given the host `.venv` workflow with no database environment
  variables set, then it still uses the local SQLite file and its full
  suite passes, exactly as documented in CLAUDE.md.
- **AC-15** Given the documentation:
  - `README.md` explains, for Windows, how to start the two services,
    run migrations, checks and tests, open a database shell, and inspect
    or reset the PostgreSQL data.
  - It explains in plain language:
    - why the database is a separate service;
    - service-name networking;
    - why `web` uses the service name rather than `localhost`;
    - the PostgreSQL environment variables;
    - the database volume;
    - startup ordering and readiness;
    - what changes from SQLite to PostgreSQL.
  - `CLAUDE.md` records the lasting architecture decisions.

## Out of scope
- Production deployment, managed PostgreSQL, backups and restores,
  replication, connection pooling
- Redis, Celery, Nginx, Gunicorn, CI/CD, monitoring, Kubernetes
- Application feature changes, beyond the S-1 login fix (AC-11)
- Moving existing data from the SQLite databases into PostgreSQL (see
  OQ-4)
- Switching the host `.venv` workflow to PostgreSQL

## Open questions
Each has a proposed answer, and the ACs assume it. **All seven were
accepted as proposed when the spec was approved on 2026-10-24.**

- **OQ-1 Driver.** *Proposed:* `psycopg` version 3, the binary build,
  which is the driver Django 5.2 recommends. It's the only new
  dependency. It also installs into the host `.venv`, where it stays
  unused. → AC-6
- **OQ-2 Database port on the host.** *Proposed:* don't publish the
  PostgreSQL port at all. The database shell is opened through the
  container (`exec`). That keeps it off the network and avoids clashing
  with any PostgreSQL installed on Windows. → AC-2
- **OQ-3 The old SQLite volume.**
  - *Proposed:* the Compose `web` service stops using SQLite, and its
    `sqlite-data` volume is removed from the configuration.
  - The optional SQLite path setting stays for the host workflow.
  - The README says how to delete the old volume. → AC-1, AC-14
- **OQ-4 Moving existing data.** *Proposed:* no. The container starts
  with an empty PostgreSQL database and is migrated fresh. The step 08
  container data was test data only. → Out of scope
- **OQ-5 The S-1 fix.** *Proposed:* login matches usernames using the
  **same** lowercase rule as the uniqueness constraint. At most one
  account can then match, and login, the admin and `createsuperuser`
  keep behaving the same. Today's ASCII behaviour is unchanged. → AC-11
- **OQ-6 Task order under concurrent inserts.** *Proposed:* accept it,
  and keep it documented with the PostgreSQL reasoning confirmed. It's
  rare and only temporary, and fixing it needs a new ordering field,
  which is a product change for its own spec. → AC-12
- **OQ-7 Where the dev credentials live.** *Proposed:* in `compose.yaml`,
  labelled development-only, as step 08 did with the secret key. Real
  credentials would come from an ignored `.env` file or a platform secret
  store in later steps. → AC-5
