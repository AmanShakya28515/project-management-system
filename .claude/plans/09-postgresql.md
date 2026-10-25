---
step: 09
slug: postgresql
spec: .claude/specs/09-postgresql.md
status: done
created: 2026-10-24
approved: 2026-10-24
---

# Plan 09 — PostgreSQL in Docker Compose

## Approach
- Add a `db` service (the official PostgreSQL image) to `compose.yaml`,
  with its own named volume and a `pg_isready` health check. `web` waits
  for that health check (`depends_on: condition: service_healthy`).
- `web` reaches the database at host **`db`**, the service name, on the
  default Compose network. The database port isn't published to the host
  (OQ-2).
- `config/settings.py` picks the backend from the environment. When
  `DJANGO_DB_HOST` is set it uses PostgreSQL; otherwise it uses SQLite,
  exactly as today. The host `.venv` workflow therefore changes in nothing
  but the installed packages (AC-14).
- **S-1 (OQ-5):** one shared case rule on `UserManager`. The stored value
  and the input are both compared through the database's `LOWER()`, the
  same function the unique constraints use. It replaces the three
  `__iexact` lookups (login, the registration checks, add-member), which
  use `UPPER()` on PostgreSQL. At most one row can then ever match.

**Why `LOWER()` on both sides, not Python's `.lower()`:** Python and
PostgreSQL can fold some characters differently. Using the database
function for both values guarantees the lookup agrees with the
constraint.

**Why the health check:** on a fresh volume, PostgreSQL spends several
seconds initialising. `runserver` connects at start to check for unapplied
migrations, and it would error until the database accepts connections.
`depends_on` alone only waits for the container to *start*, not for the
database to be *ready* (AC-3).

## Data model & migrations
No model fields or constraints change, so no migration is expected. The
manager gains methods only. `makemigrations --check` must stay clean on
both backends.

## URLs, views, templates
None. No UI change, so the ui-ux-pro-max skill isn't needed.

## Implementation steps
- [x] 1. **Dependency (OQ-1):**
  - add `psycopg[binary]~=3.3.0` to `requirements.txt`, the current
    stable 3.3 line, pinned the way Django is;
  - install it into `.venv`.
- [x] 2. **Settings (D-1):**
  - If `DJANGO_DB_HOST` is set, use `django.db.backends.postgresql` with
    `NAME`, `USER`, `PASSWORD`, `HOST` and `PORT` from `DJANGO_DB_NAME`,
    `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST` and
    `DJANGO_DB_PORT` (default 5432).
  - Otherwise keep the current SQLite block, `DJANGO_SQLITE_PATH`
    included.
- [x] 3. **S-1 (OQ-5, D-4):**
  - Add `UserManager.filter_username_ci(value)` and
    `filter_email_ci(value)`. Each is
    `alias(x=Lower(field)).filter(x=Lower(Value(value)))`.
  - Use them in `get_by_natural_key`, `RegistrationForm.clean_username`,
    `RegistrationForm.clean_email` and `AddMemberForm.clean_username`.
    `AddMemberForm` keeps `is_active=True` and its "exactly one match"
    guard.
  - Update the S-1 comments in `accounts/models.py` and
    `workspaces/forms.py`.
- [x] 4. **`compose.yaml`:**
  - **Add the `db` service:**
    - `image: postgres:17` (D-2);
    - `environment`: `POSTGRES_DB`, `POSTGRES_USER` and
      `POSTGRES_PASSWORD`, labelled dev-only, plus `POSTGRES_INITDB_ARGS`
      (D-3);
    - `volumes: postgres-data:/var/lib/postgresql/data`;
    - `healthcheck` running `pg_isready -U … -d …` (2 s interval, 15
      retries);
    - no `ports`.
  - **Change `web`:**
    - add `depends_on: db: condition: service_healthy`;
    - add the `DJANGO_DB_*` environment values, with host `db`, labelled
      dev-only;
    - remove `DJANGO_SQLITE_PATH` and the `sqlite-data` mount.
  - **Top-level `volumes`:** replace `sqlite-data` with `postgres-data`
    (OQ-3).
  - The `web` port stays on `127.0.0.1`.
- [x] 5. **`Dockerfile`:** unchanged. The `psycopg[binary]` wheel bundles
  `libpq`, so no system packages are needed. Rebuild the image for the
  new requirement.
- [x] 6. **Tests (AC-11):** add `accounts/tests/test_case_rules.py`. The
  tests use a pair of usernames that are **distinct under `LOWER()`** but
  equal under `UPPER()`: `I` and `ı` (dotless i).
  - Login with each username, in its own case, signs in that exact user
    and doesn't cause a server error.
  - Registering `ı` while `I` exists is allowed. It's distinct under the
    uniqueness rule, while a real case variant (`alice` after `Alice`) is
    still refused.
  - Adding `ı` to a workspace finds that user.
  - There's an email equivalent for the registration check.

  These tests run on both backends. On PostgreSQL they fail with the old
  `__iexact` code, so they're real regression tests.
- [x] 7. **SQLite assumptions (AC-13):**
  - Run the full suite on PostgreSQL and fix only genuine incompatibilities.
    The likely candidates are implicit ordering without `order_by` and
    hard-coded IDs; none were found by a scan.
  - The ASCII notes in `projects/tests/data.py` and `tasks/tests/data.py`
    stay, because the tests still run on SQLite on the host.
- [x] 8. **Documentation:**
  - **`README.md`:**
    - the two-service workflow;
    - `docker compose exec db psql -U <user> -d <db>`;
    - reset with `down -v`;
    - removing the old volume:
      `docker volume rm project_management_system_sqlite-data`;
    - the concepts listed in AC-15.
  - **`CLAUDE.md`:**
    - the architecture (`db` service, env switch, health check, `C`
      collation, the case rule);
    - commands;
    - the S-1 entry resolved, and the task-order note confirmed (OQ-6);
    - PostgreSQL moved out of "Do NOT add"; the stack note on SQLite
      kept for the host.
- [x] 9. **Verify** (see the test plan).

## Test plan
| AC | Check | What it asserts |
|---|---|---|
| AC-1 | `docker compose up -d`; `docker compose ps`; `curl` the login page | `web` and `db` are both running and `db` is healthy; the login page returns 200 on `127.0.0.1:8000` |
| AC-2 | `exec web env`; `exec web python manage.py shell -c "connection.settings_dict['HOST']"`; `docker compose port db 5432` | Host `db`; no published database port |
| AC-3 | `down -v`, then `up -d` from empty; `logs web` | `web` starts only after `db` is healthy, with no connection errors; the app works after `migrate` with no restart |
| AC-4 | Create a user, `down`, `up -d`, check the user; `down -v` | Data survives recreation; `down -v` removes it |
| AC-5 | Read `compose.yaml`; search the tracked files | Credentials only as dev-labelled values; no production credential |
| AC-6 | `git diff requirements.txt`; `docker compose build`; `pip list` | Exactly one new direct line, `psycopg[binary]~=3.3.0`; the image builds |
| AC-7 | `exec web python manage.py migrate` on a fresh volume | All migrations apply |
| AC-8 | `exec web … check`, `… makemigrations --check --dry-run` | No issues, no changes |
| AC-9 | `exec web python manage.py test` | All tests pass on PostgreSQL (403 plus the new ones) |
| AC-10 | The AC-9 suite | Existing behaviour tests are unchanged and green |
| AC-11 | `accounts/tests/test_case_rules.py` on PostgreSQL **and** SQLite | Login, registration and add-member use the `LOWER()` rule, with no 500 |
| AC-12 | Existing task-order tests on PostgreSQL; a `CLAUDE.md` note | Oldest-first order holds; the limitation is recorded as accepted (OQ-6) |
| AC-13 | The AC-9 run, plus a code search for SQLite-only constructs | No SQLite-dependent code; misleading comments corrected |
| AC-14 | Host `.venv`: drift, `check`, the full suite, `DATABASES` engine | Still SQLite at `./db.sqlite3`; all green |
| AC-15 | Read through `README.md` and `CLAUDE.md` | All the listed commands and concepts are present |

## Risks
- **Sort order differs by collation.**
  - The PostgreSQL image's default collation (`en_US.utf8`) sorts
    differently from SQLite's code-point order. It ignores spaces and
    punctuation at the first level.
  - That could change the alphabetical order of workspaces, projects and
    members (AC-10).
  - D-3 avoids it with a `C` collation.
- **Unicode case folding depends on `LC_CTYPE`.** With `C` *ctype*,
  `LOWER()` would fold only ASCII, like SQLite. D-3 keeps ctype at
  `en_US.utf8`, so S-1 is genuinely exercised.
- **The PostgreSQL data format is tied to its major version.** A floating
  `postgres:latest` could jump a major version and refuse the existing
  volume. D-2 pins the major version.
- **Transactions behave differently.** After an error inside a
  transaction, PostgreSQL refuses further statements until a rollback.
  The existing `IntegrityError` tests and `ProjectCreateView` already use
  `transaction.atomic()` correctly (plan 04, D-3), so no change is
  expected; the full suite confirms it.
- **Project names still use `__iexact`** in `ProjectForm`. On PostgreSQL
  that can only be stricter than the constraint, or fall through to the
  existing `IntegrityError` handling, which shows a field error. It can't
  cause a 500, so it's left alone (scope). Noted for review.
- **Old data:** the `sqlite-data` volume becomes unused, and its contents
  aren't migrated (OQ-4). The README shows how to delete it.
- **Secrets:** the database password in `compose.yaml` is dev-only and
  public in Git; the database isn't published on any host port.

## Decisions needing approval
_All four (D-1 to D-4) accepted as proposed with plan approval, 2026-10-24._

- **D-1 — How the backend is chosen, and the variable names.**
  PostgreSQL is used when `DJANGO_DB_HOST` is set; otherwise SQLite. The
  variables are `DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`,
  `DJANGO_DB_HOST` and `DJANGO_DB_PORT`, matching the existing `DJANGO_*`
  prefix. *Alternative:* a single `DATABASE_URL`, but that needs another
  package or a hand-written parser. *Proposed:* the separate variables.
- **D-2 — Image `postgres:17`, pinned to the major version.**
  - The major version decides the on-disk data format.
  - 17 is a current, well-supported release.
  - PostgreSQL 18's image changes the data directory layout, which would
    complicate the volume for no learning gain.
  - The minor or digest pin stays with Q-74 in the CI/CD step.
- **D-3 — Collation `C`, ctype `en_US.utf8`.**
  - Set with `POSTGRES_INITDB_ARGS: "--encoding=UTF8 --lc-collate=C
    --lc-ctype=en_US.utf8"`.
  - Ordering stays identical to SQLite's (code-point order of the
    lowercased names), so no visible behaviour changes.
  - `LOWER()` still folds Unicode.
  - Test databases inherit it from `template1`.
  - Revisit natural-language sorting as a product decision later.
- **D-4 — Where the case rule lives.**
  - The `UserManager` methods, used by the three call sites.
  - One rule, next to the constraints it must match.
  - Project-name checks are deliberately left on `__iexact` (see Risks).

## Files changed
- **Created:** `accounts/tests/test_case_rules.py` (8 tests, AC-11).
- **Modified:**
  - `requirements.txt`: `+ psycopg[binary]~=3.3.0`;
  - `config/settings.py`: backend chosen by `DJANGO_DB_HOST` (D-1);
  - `accounts/models.py`: `filter_username_ci`/`filter_email_ci`, and
    `get_by_natural_key` uses them (D-4);
  - `accounts/forms.py`: the registration checks use the shared rule;
  - `workspaces/forms.py`: add-member uses the shared rule;
  - `compose.yaml`: the `db` service, health check, `depends_on`,
    `DJANGO_DB_*`, the `postgres-data` volume; `sqlite-data` removed;
  - `README.md`: the PostgreSQL workflow and concepts;
  - `CLAUDE.md`: a PostgreSQL architecture section; S-1 resolved; the
    task-order note accepted; stack and commands updated.
- **Unchanged:** the `Dockerfile` (as planned); all models and
  migrations; every existing test.

**Build notes:**
- Docker Desktop wasn't running again; `/build` started it.
- PostgreSQL resolved to 17.11.
- The old `project_management_system_sqlite-data` volume still exists on
  this machine. The README tells the user how to delete it; `/build`
  didn't delete it.
- The dev database is left migrated and empty, and the containers are
  stopped (`docker compose down`, volume kept).

## Test results
All measured by `/build` on 2026-10-24.

| AC | Result |
|---|---|
| AC-1 | `up -d` started `db` first (`Waiting` → `Healthy`), then `web`. `ps` shows `db` healthy and `web` up. The login page returns **200** on `127.0.0.1:8000`. |
| AC-2 | Django connection: `postgresql db 5432`. The env has `DJANGO_DB_HOST=db`. `docker compose port db 5432` → `invalid IP:0` (not published); `ps` shows `5432/tcp` with no host mapping. |
| AC-3 | Started from an empty volume (`down -v`): `web` started only after `db` was healthy. The `web` log shows no connection error ("You have 24 unapplied migrations", then "Starting development server"). After `migrate` the app worked with no restart. |
| AC-4 | Users `I` and `ı` survived `down` (0 containers left) and `up -d`. `down -v` removed `postgres-data`, leaving no tables; after `migrate` there were 0 users. |
| AC-5 | The only secret-like values in tracked files are the dev-labelled `compose.yaml` values (secret key and DB password). No `.env` or production credential. |
| AC-6 | `git diff requirements.txt`: exactly one added line, `psycopg[binary]~=3.3.0`. The image built. `psycopg` 3.3.6 is installed in `.venv` as well. |
| AC-7 | `exec web python manage.py migrate` on the fresh database: all 24 migrations OK. |
| AC-8 | `check`: no issues. `makemigrations --check --dry-run`: no changes. |
| AC-9 | `exec web python manage.py test` on PostgreSQL: **411 tests OK** (403 plus 8 new; 83 s). |
| AC-10 | All 403 existing tests are unchanged and pass on PostgreSQL. |
| AC-11 | `test_case_rules` passes on both backends. A probe on PostgreSQL with `I` and `ı`: old `__iexact('ı')` matched **2** users, new `filter_username_ci('ı')` matched **1**. `upper('ı')=I`, `lower('ı')=ı`. |
| AC-12 | The existing oldest-first task tests pass on PostgreSQL. The limitation is recorded as accepted in `CLAUDE.md` (OQ-6). |
| AC-13 | Code search: the only SQLite references are in the settings' SQLite branch. No raw SQL, cursor or `extra`, and no user lookups left on `__iexact`. S-1 comments rewritten. |
| AC-14 | Host `.venv`: backend `sqlite` at `<repo>/db.sqlite3`; drift clean; `check` clean; full suite **411 OK**. |
| AC-15 | The README covers both services, `ps`, `psql`, reset, deleting the old volume and every listed concept. `CLAUDE.md` has the architecture section. |

Also verified: database collation `C` and ctype `en_US.utf8` for both
`pms` and `template1` (D-3).

Unresolved: none.

## Review log

### 2026-10-24: review of the build
**Scope:** `git diff` against `c6ab29b` plus the new files; it matches
"Files changed". Done inline, with no specialist reviewer. The auth change
is a narrow lookup swap, verified by tests on both backends.

The ACs are met as recorded. The case rule is consistent:
- `RegistrationForm.clean_username` overrides Django's own `__iexact`
  check and doesn't call `super()`, so the shared rule really applies;
- `ModelBackend` handles `DoesNotExist`, and the constraint rules out a
  second match;
- the SQLite behaviour is unchanged, because both `LOWER` and `LIKE` fold
  ASCII only.

- **Q-76 — Medium — fixed (retest).** `compose.yaml:36`: the health check
  `pg_isready -U pms -d pms` can report "ready" **during first-time
  initialisation**.
  - **Evidence:** on an empty volume, the image's entrypoint runs a
    *temporary* server with `listen_addresses=''`
    (`docker-entrypoint.sh:297`, checked in the image): it accepts the
    Unix socket only.
  - `pg_isready` without `-h` uses that socket, so it can pass while TCP
    is still closed. `web` would then start, `runserver`'s migration
    check would get "connection refused" on `db:5432`, and the container
    could exit.
  - Verification passed because initialisation is short, so this is a
    timing race against AC-3, not a demonstrated failure.
  - **Fix:** `pg_isready -h 127.0.0.1 -U pms -d pms`, which checks over
    TCP, like `web` connects.
- **Q-77 — Low — accepted.** The admin's add-user form, Django's
  `UserAdmin` with `BaseUserCreationForm.clean_username`, still uses
  `__iexact`. On PostgreSQL that's only *stricter*: it refuses `ı` while
  `I` exists. It can't cause a 500, and it's superuser-only. Revisit if
  the admin user forms are ever customised.
- **Q-78 — Low — deferred** (to the environment and secret configuration step). The dev database credentials appear twice in
  `compose.yaml` (lines 20 and 30, and the name and user too). Editing
  one without the other gives an authentication error. A YAML anchor or a
  git-ignored `.env` with `${…}` interpolation would remove the
  duplication. Fits the step that moves credentials out of
  `compose.yaml`.

**Result:** no High findings. Q-76 is worth fixing before closing: it's
a one-line change that removes a first-start race.

### 2026-10-24: retest (Q-76 only)
- **Q-76 — fixed.**
  - The `compose.yaml` health check is now
    `pg_isready -h 127.0.0.1 -U pms -d pms`, with a short comment on why.
  - The interval, timeout and retries are unchanged, as are the services
    and `depends_on: condition: service_healthy`.
  - **Measured, fresh volume, `db` alone:**
    - the log shows the temporary setup server ready at 17:26:43.858
      (pid 60) and the real server at 44.374 (pid 1), a ~0.5 s window in
      which the old socket check could pass;
    - the first health check ran at 44.444 and reported
      `127.0.0.1:5432 - accepting connections`, so the service became
      healthy only after TCP was open.
  - **Measured, fresh volume, both services together:**
    - the temporary server was ready at 17:27:22.572 and the real server
      at 23.081;
    - the first healthy check ran at 23.242, and `web` started at 23.788;
    - the `web` log has 0 error, refused or traceback lines;
    - `migrate` applied, and the login page returned **200** with no
      restart.
- **Q-77 — accepted** (Low). **Q-78 — deferred** to the environment and
  secret configuration step.
- **Not re-run:** the full suite. Only the `compose.yaml` health check
  changed; no Python, template or settings files. The earlier 411/411 on
  PostgreSQL and SQLite stands. The containers were stopped afterwards,
  leaving the volume migrated and empty.
