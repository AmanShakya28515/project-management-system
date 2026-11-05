---
step: 11
slug: production-image
spec: .claude/specs/11-production-image.md
status: done
created: 2026-10-31
approved: 2026-10-31
---

# Plan 11 — Production image

## Approach
- Keep the development Dockerfile, Compose file, base settings and CI workflow
  unchanged. Add a separate production image and explicit production settings
  module; this preserves Windows development and makes the runtime choice clear.
- Add `requirements.production.txt`, including `requirements.txt` plus Gunicorn
  only. Select and record a supported Gunicorn version during build using its
  official release information. Gunicorn stays out of the Windows virtualenv
  and development image dependencies.
- Add `config/settings_production.py`, importing the existing base settings and
  overriding production values. The production image selects it through
  `DJANGO_SETTINGS_MODULE=config.settings_production` for both Gunicorn and
  management commands. The existing WSGI default respects this selection.
- Production settings require explicit, nonblank `DJANGO_SECRET_KEY`,
  `DJANGO_ALLOWED_HOSTS`, `DJANGO_DB_HOST`, `DJANGO_DB_NAME`, `DJANGO_DB_USER` and
  `DJANGO_DB_PASSWORD`. Port defaults to 5432 and must be a valid port number.
  Reject `django-insecure-` secret keys (covering both existing development
  secrets), weak keys reported by Django's deployment check, wildcard hosts,
  and the existing development database password. Errors name variables only,
  never their values. There is no production SQLite fallback.
- Set DEBUG to false. An absent `DJANGO_DEBUG` or the exact value `0` is accepted;
  any other supplied value raises `ImproperlyConfigured`. Do not hide deployment
  warnings or add speculative proxy trust, HTTPS redirects or secure cookies:
  the approved local HTTP boundary remains explicit.
- Add `Dockerfile.production` using the existing pinned Python base. Install
  dependencies before copying code, create an unprivileged user with fixed UID
  10001, and keep application files root-owned and readable by that user.
  Run Gunicorn directly in exec form on `0.0.0.0:8000`, with two sync workers,
  application preloading for early settings validation, and access/error logs
  on stdout/stderr. No reload, startup migration or extra system package.
- Add standalone `compose.production.yaml` for local verification, invoked with
  `-p pms-production -f compose.production.yaml`. It has no source mount and
  uses port `127.0.0.1:8001:8000`, an isolated PostgreSQL volume/network, the
  existing PostgreSQL pin/collation/TCP readiness pattern, and required runtime
  environment interpolation. Share database name/user/password values between
  services through the same environment variables. No fixed container names
  or host database port. This is a local rehearsal, not a deployment recipe.
- Keep `.env.production.local` untracked and outside the image using the existing
  ignore patterns. Document PowerShell commands using that runtime environment
  file; provide variable names and generation instructions, not reusable secrets.

## Data model & migrations
None. Run existing migrations explicitly against the isolated rehearsal database.
Never modify or reset the existing development database or volume.

## URLs, views, templates
No changes. Existing scoped access, CSRF, escaping and authentication remain.
Static delivery (including admin assets) and Tailwind Play CDN remain documented
deployment blockers under the approved boundary; no frontend work is planned.

## Implementation steps
- [x] 1. Add production settings and focused environment-validation tests.
- [x] 2. Add production-only requirements and Dockerfile. Extend `.dockerignore`
  to exclude the new Docker/Compose files while retaining test-required design
  documentation. Confirm existing environment/database exclusions cover both images.
- [x] 3. Add the standalone production rehearsal Compose configuration with
  required environment values and isolated resources.
- [x] 4. Verify in the order below, fix only approved-scope issues, and record
  measured results, warning IDs and any blocked checks here.
- [x] 5. Update README with separate development/production commands, required
  variables, secret generation, explicit migrations, logs, shutdown and the
  approved production-readiness boundary. Reserve lasting CLAUDE.md updates
  and Steps landed for `/done 11`.

## Test plan
| AC | Test module / verification | What it asserts |
|---|---|---|
| AC-1 | Production container smoke check | Gunicorn starts, logs identify the server, login page returns 200. |
| AC-2 | Container user/process inspection | Configured user and actual server processes have nonzero UID. |
| AC-3 | Container mount inspection and HTTP smoke check | No host source mount; packaged templates/code serve requests. |
| AC-4 | `core/tests/test_production_settings.py`; negative container startup | DEBUG absent/0 produces false; enabling or malformed values fails before serving. |
| AC-5 | Same focused module; negative container startup | Each missing/blank required variable, development/weak secret, wildcard host, development DB password and invalid port fails without echoing values; valid values select PostgreSQL correctly. |
| AC-6 | Existing full suite on PostgreSQL; HTTP rehearsal | Existing access tests pass; with production settings, anonymous GET/POST login redirects, member pages, outsider nested 404 and CSRF rejection retain their behaviour. |
| AC-7 | Production `manage.py check --deploy` | Record every warning ID and rationale. Fix image/settings issues in scope; document HTTPS-dependent warnings without suppressing them. |
| AC-8 | Existing full suite on SQLite/PostgreSQL; development smoke check | Development settings retain defaults, Compose still uses runserver/live reload/localhost port; host uses SQLite without DB environment. |
| AC-9 | Both existing CI command sequences locally; production build/run | Drift clean, check clean and full suite passes on both backends; production runtime requirements demonstrated locally. CI configuration remains unchanged. |
| AC-10 | Build context/image inspection; Git diff | No local environment file, database or real credential included; no secret supplied as a build argument or image environment value. |
| AC-11 | Follow README rehearsal commands | Build/start, explicit migrate, inspect logs and stop work; explanations and deployment blockers match measured behaviour. |

### Verification order and isolation
1. Run the focused module using `.\.venv\Scripts\python.exe`. Use Django
   `SimpleTestCase` and isolated subprocesses with controlled environments to
   load settings and assert success/failure; do not connect to a database or
   mutate the parent test process's settings. These tests run in existing CI.
2. On host SQLite: migration drift, `check`, then the full suite.
3. Through existing development Compose: build, migration drift, `check`, then
   the full suite. Confirm login page and live reload using a reversible code
   touch, without changing tracked content.
4. Build the production image and start the isolated rehearsal database. Run
   explicit migrations, production drift and system checks, then the existing
   full suite under production settings against this PostgreSQL database.
   Use disposable verification credentials; do not print environment files or
   resolved secret-bearing Compose configuration.
5. Run `check --deploy`, assess all output, start Gunicorn, inspect UID/mounts
   and perform the HTTP checks above. Use temporary fixture users/resources in
   the isolated database for member/non-member checks. Confirm a disallowed
   Host is rejected and missing routes produce a generic response with DEBUG off.
6. Exercise negative image startup with invalid configuration, verify nonzero
   exit and no secret disclosure, then stop only the rehearsal resources.
   Keep its data by default; any reset command in documentation is clearly
   labelled destructive. No commit/push or new GitHub run is required here;
   distinguish local CI-equivalent evidence from remote CI evidence.

## Risks
- Production mode is an explicit settings selection. Document it for all
  management commands; do not override the image's production selection with
  development settings during verification.
- Local HTTP cannot validate HTTPS behaviour. Record expected deployment warnings
  (such as redirect, HSTS and secure-cookie warnings) individually; unexpected
  warnings require investigation. Never claim the image is ready for public
  exposure until the approved deferred work is completed.
- Separate Docker/Compose definitions duplicate a few pins and readiness values.
  Keep them aligned with existing approved versions and document joint updates.
- PostgreSQL initialisation values apply only to a fresh volume. Use a distinct
  Compose project and volume so production rehearsal cannot alter development data.
- Network/Docker availability may block verification. Report actual failures
  and leave the build incomplete rather than recording unrun checks as passed.

## Decisions needing approval
- Gunicorn is the only new dependency; already approved in spec OQ-1. This plan
  keeps it in production-only requirements to preserve Windows development.
- No further scope decisions. Spec OQ-2/OQ-3 approve the deferred deployment
  boundary, unchanged CI jobs and local production-image verification.

## Files changed
Created: `config/settings_production.py`, `requirements.production.txt`,
`Dockerfile.production`, `compose.production.yaml`,
`core/tests/test_production_settings.py`. Modified: `.dockerignore`, `README.md`
and this plan. Pre-existing Step 10 documentation edits are preserved.
Created ignored `.env.production.local` with generated local rehearsal secrets;
its contents are not recorded here or passed into image builds.

No application feature, base settings, development Docker/Compose or CI workflow
changes. No model changes or migrations added.

## Test results
### 2026-10-31 — Build preflight blocked
- Approved spec and plan confirmed; host virtualenv reports Python 3.12.10.
- `docker version` failed in the sandbox and outside it. Outside the sandbox,
  the selected context is `desktop-linux`, but the
  `dockerDesktopLinuxEngine` named pipe does not exist: the Docker engine is
  unavailable. Start Docker Desktop and wait for the Linux engine to be ready.
- Stopped as required by `/build`'s environment-failure rule. No implementation
  files changed, no tests or Django checks ran, and no image was built.
- Status remains `approved`; resume with `/build 11 resume` after Docker is ready.

### 2026-10-31 — Resumed build completed
- Docker Desktop Linux engine available on resume.
- Focused settings module: **4/4 passed** after fixing JSON serialisation of
  the base settings' SQLite Path in the test harness (no application workaround).
- Host SQLite: migration drift clean, `check` clean, full suite **415/415 OK**
  (148.880 seconds). Four new test methods cover validation subcases.
- Gunicorn's official release notes list 26.2.2, but the package index rejected
  that pin and listed 26.2.0 as its newest available release. Corrected the
  production-only pin to **26.2.0**, which the index successfully resolved.
  Source: https://pypi.org/project/gunicorn/26.2.0/ .
- Both image builds passed. Container dependencies resolved to Django 5.2.18
  and psycopg 3.3.6 within the existing approved ranges.

| Environment | Measured result |
|---|---|
| Host `.venv`, SQLite | Focused 4/4; drift clean; check clean; **415/415 passed**, 148.880 s. |
| Development Compose, PostgreSQL | Build passed; drift clean; check clean; **415/415 passed**, 63.941 s. |
| Production image/settings, PostgreSQL | Build and explicit migrations passed; drift clean; check clean; **415/415 passed**, 61.036 s. |

Additional measured verification:
- Production Gunicorn served HTTP login and member workspace/project/task pages
  successfully. Anonymous GET redirects included `next`; CSRF-valid anonymous
  POST redirects omitted `next`. Authenticated outsider task access returned
  404, missing-CSRF status submission returned 403, and a valid member status
  update persisted. Disallowed Host returned 400; missing route returned a
  generic 404 without traceback/URLconf. DEBUG was false. Disposable HTTP fixture
  users/workspace/project/task were removed afterwards.
- Actual Gunicorn master and two workers all had UID 10001. Application source
  was owned by root and not writable by the runtime user. Docker inspection
  returned an empty mount list. Image filesystem inspection found no environment
  files, SQLite databases, Git metadata or host virtualenv. Secrets were generated
  into the ignored runtime file, never supplied as build arguments.
- Four actual Gunicorn startup failures verified: DEBUG=1, blank secret,
  wildcard hosts and the development database password. Each exited nonzero,
  named the invalid variable and did not print either generated runtime secret.
- Development login returned HTTP 200. Touching `core/views.py`'s timestamp
  triggered StatReloader and a clean server restart; original timestamp restored,
  file content unchanged. Published port inspection confirmed
  `127.0.0.1:8000`. Git diff confirms development Docker/Compose, base settings,
  base requirements and the CI workflow are unchanged.
- `check --deploy` completed with exactly four warnings, none silenced:
  **security.W004** (HSTS), **security.W008** (HTTPS redirect),
  **security.W012** (secure session cookie), **security.W016** (secure CSRF cookie).
  These require the actual HTTPS deployment design. Their reasons and the
  static-delivery/Tailwind limitations are documented in README; this local HTTP
  rehearsal is not approved for public exposure.
- README build/start/migration/check/log/stop command forms were exercised.
  Both verification Compose stacks were stopped with `down`, without `-v`;
  both database volumes and the ignored rehearsal runtime file are retained.
- `git diff --check` passed. No commit, push, registry publication or remote CI
  run was performed. CI-equivalent checks passed locally on both backends.

Unresolved build verification: none. Formal review is the next stage.

## Review log
### 2026-10-31 — Review
Scope: the Step 11 files listed above, including new untracked production files,
against the approved spec and plan. Pre-existing Step 10 documentation edits
were excluded. Review performed inline; no implementation fixes made.

- **Correctness:** the image explicitly selects production settings, uses
  Gunicorn in exec form with preloading, and runs as UID/GID 10001. Production
  settings reject debug enablement, missing/blank required values, development
  credentials, weak keys, wildcard hosts and invalid ports. PostgreSQL is
  mandatory. WSGI's existing `setdefault` preserves the image's settings choice.
- **Security/data integrity:** no credential is baked into the Dockerfile or
  supplied at build time. Git/Docker ignore rules cover the runtime environment
  file and local databases. Rehearsal has no source mount or database host port,
  publishes web only on localhost, and retains the approved TCP healthcheck and
  collation. Migrations are explicit; development data and application scope
  chains are unchanged.
- **Maintainability/scope:** production requirements include the base requirements
  without changing Windows dependencies. Existing development Docker/Compose,
  base settings and CI workflow have no diff. No model, view or template changes;
  no changed UI requires accessibility review.
- **Evidence:** build records 415/415 passing on all three environments, focused
  validation tests, real HTTP access/CSRF checks, process/mount inspection and
  negative Gunicorn startup checks. No application code changed afterwards, so
  the full suite was not rerun. `git diff --check` remains clean. Remote CI has
  not been rerun; local CI-equivalent results are clearly distinguished.
- **Approved limitations:** the four unsuppressed HTTPS-related deployment
  warnings and static/Tailwind asset delivery remain documented future work
  under spec OQ-2. Gunicorn 26.2.0 selection and the unavailable 26.2.2 attempt
  are recorded; no new dependency or scope decision is outstanding.

**Result:** no High, Medium or Low findings. Status set to `reviewed`;
next stage is `/done 11`.

### 2026-10-31 — Closed
Required verification is green; review has no findings. No application code
changed after the successful full-suite runs, so tests were not rerun.
Spec and plan marked done; lasting architecture and limitations recorded in
CLAUDE.md. Nothing committed or pushed.
