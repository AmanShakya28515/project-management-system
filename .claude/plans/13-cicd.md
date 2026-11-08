---
step: 13
slug: cicd
spec: .claude/specs/13-cicd.md
status: done
created: 2026-11-07
approved: 2026-11-07
---

# Plan 13 — CI/CD: build once, publish, pull

## Approach
One workflow, four jobs:

```
push / PR
 ├─ postgres    (unchanged)  ─┐
 ├─ sqlite      (unchanged)  ─┼─> publish  (main pushes only)
 └─ production  (new)        ─┘    load the verified image, push to GHCR
      build Dockerfile.production
      verify it with compose.server.yaml
      main only: save the image as an artifact
```

- **D-1 Verify with the real server file.** The `production` job builds the
  image under its final registry name, then runs it with
  `compose.server.yaml` and a throwaway env file. CI then tests the exact
  image and the exact Compose file the server uses, not the step 11
  rehearsal file. This replaces the rejected alternative of a separate CI-only
  Compose file, which could drift from the server's.
- **D-2 Publish the verified image, not a rebuild.** On `main`, the
  `production` job saves the image (`docker save | gzip`) as a one-day
  workflow artifact. The `publish` job (`needs` all three jobs) loads it and
  pushes it. Rebuilding in `publish` would produce a different, untested
  image (dependencies float within `~=`). Making `production` wait for the
  other jobs instead would serialise the run and add several minutes.
- **D-3 Registry name and tag:** `ghcr.io/amanshakya28515/pms-web:<7-char
  revision>` (GHCR needs a lowercase owner). There's no `latest` tag (spec,
  out of scope). The build adds the label
  `org.opencontainers.image.source=<repo URL>` so GitHub links the package to
  the repository.
- **D-4 Server pulls, cannot build.** `compose.server.yaml` loses its
  `build:` section, and `image:` becomes the registry name. With
  `build:` kept, a forgotten `pull` would make `up` silently build an
  untested image on the server; without it, a missing image is a loud
  error. The helper `/opt/pms/dc` stays as it is, because `PMS_REVISION`
  still comes from the checkout (which supplies the matching Compose file).
  Checking out an older commit restores its older Compose file and its
  local `pms-web:<rev>` name, so step 12 recovery still works.
- **D-5 Q-80:** the concurrency group becomes the commit SHA on `main` and
  the ref elsewhere: `main` runs never share a group, so none is cancelled
  or dropped from the queue. Other branches keep cancel-in-progress.
- **D-6 Registry login uses the run's own `GITHUB_TOKEN`** through
  `docker login --password-stdin` in a plain `run` step, so there are no
  stored secrets and no third-party login action. Only the `publish` job
  gets `packages: write`; the workflow default stays `contents: read`.
- **D-7 The throwaway CI env file** is generated on the runner with Python's
  `secrets` module (strong, so production settings accept it), masked with
  `::add-mask::`, written under `$RUNNER_TEMP` and never printed. It isn't a
  GitHub secret and is never reused.
- **D-8 New actions:** `actions/upload-artifact` and
  `actions/download-artifact`, official, pinned to their current major tag
  (checked at build time), like the existing `@v7` pins. No Docker
  marketplace actions are needed; plain `docker` commands do the job.

## Data model & migrations
None. No application code changes.

## URLs, views, templates
None.

## Implementation steps
- [x] 1. **`ci.yml`, concurrency (D-5):**
  `group: ci-${{ github.ref == 'refs/heads/main' && github.sha || github.ref }}`,
  and `cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`.
- [x] 2. **`ci.yml`, new `production` job** (`ubuntu-24.04`, 15 min, read-only):
  1. checkout; compute `REV` (first 7 characters of `GITHUB_SHA`) and
     `IMAGE=ghcr.io/amanshakya28515/pms-web:$REV` into `$GITHUB_ENV`;
  2. `docker build -f Dockerfile.production --label …source… -t $IMAGE .`
     (AC-1);
  3. generate the masked env file (D-7);
  4. with `docker compose -p pms -f compose.server.yaml --env-file …` and
     `PMS_REVISION=$REV`: `up -d db`, `run --rm web python manage.py migrate
     --noinput`, then `check --deploy`, asserting the set of `security.W`
     IDs is exactly W004, W008, W012, W016 and that it exits 0;
  5. `up -d web`, then poll `http://127.0.0.1:8010/accounts/login/` until
     it answers 200 (up to about 30 s); `exec -T web id -u` must print
     `10001`; `logs web` must contain no `ERROR`;
  6. secret check (AC-6): no generated value appears in `docker image
     inspect` or `docker history --no-trunc`, and no `.env*` file exists
     in the image's `/app`;
  7. `if: failure()` show the logs; `if: always()` `down -v` (CI runner
     only);
  8. on a push to `main` only: `docker save $IMAGE | gzip` and upload it as
     the artifact `pms-web-image`, retention 1 day.
- [x] 3. **`ci.yml`, new `publish` job:** `needs: [postgres, sqlite,
  production]`; `if: github.event_name == 'push' && github.ref ==
  'refs/heads/main'`; `permissions: contents: read, packages: write`;
  download the artifact, `docker load`, log in with `GITHUB_TOKEN`
  (`--password-stdin`), `docker push $IMAGE`, `docker logout ghcr.io`.
- [x] 4. **`compose.server.yaml`:** remove `build:`; set
  `image: ghcr.io/amanshakya28515/pms-web:${PMS_REVISION:?…}`; update its
  header comment (pull, not build).
- [x] 5. **`.dockerignore`:** add `compose.server.yaml`, alongside the other
  Compose files (it isn't needed inside the image).
- [x] 6. **Local verification:** the full suite, drift and `check` (no app
  change is expected, but run them); build `Dockerfile.production` and run
  the `production` job's checks locally against `compose.server.yaml`;
  `docker compose -f compose.server.yaml config --quiet` with dummy
  values.
- [x] 7. **Commit and push** (only when the user asks); watch the run on
  `main`: four jobs green, `publish` pushes the image.
- [x] 8. **One-time GitHub setting (user):** the package `pms-web` →
  Package settings → Change visibility → **Public**. Then check from the
  PC, logged out of ghcr.io: `docker pull ghcr.io/amanshakya28515/pms-web:<rev>`
  works (AC-6).
- [x] 9. **Failure demo (AC-1, AC-5):** a throwaway branch with a broken
  line in `Dockerfile.production` → `production` is red and `publish`
  doesn't run (it also never runs on a branch). Delete the branch
  afterwards (local and remote).
- [x] 10. **Server rollout (user-run, short batches):** back up → `git fetch`
  → `git checkout --detach <rev>` → `/opt/pms/dc pull web` →
  `migrate --noinput` → `up -d web` → `ps`, logs, tunnel. Confirm the
  running image is `ghcr.io/…:<rev>` and that nothing was built. The old
  `pms-web:bd25e63` image stays for recovery (AC-9).
- [x] 11. **README:** the CI section (three checks, the `production` job,
  publishing on `main`); a "Container registry" concepts section (registry,
  image name/tag, public pull, build once/pull everywhere); "Build vs
  deployment" and the update routine rewritten for pull (step 3 becomes
  `dc pull web`, and the "two builds needn't be identical" note goes);
  "no published image for this revision": check the Actions run, fix and
  push, never build on the server; how to list published revisions on
  GitHub (repository → Packages).

## Test plan
There are no Django tests: nothing in the application changes. Verification
is the CI run itself, a local rehearsal and the user-run server checks.

| AC | Where | What it asserts |
|---|---|---|
| AC-1 | `production` job; step 9 demo | Every push builds `Dockerfile.production`; a broken line turns the run red |
| AC-2 | `production` job steps 4–5 | migrate OK; `check --deploy` = exactly W004/W008/W012/W016; login 200; UID 10001; no ERROR in the log |
| AC-3 | `postgres`, `sqlite` jobs | Unchanged steps still run and pass; local full suite passes |
| AC-4 | `publish` job on `main` | Runs only after all three jobs pass; pushes the loaded (verified) image under `:<rev>`; the tag matches the commit |
| AC-5 | Step 9 branch run; PR runs | `publish` is skipped; no artifact is uploaded |
| AC-6 | `production` step 6; step 8 | No secret value in inspect/history; no `.env*` in `/app`; an anonymous `docker pull` works |
| AC-7 | Workflow review | Only `publish` has `packages: write`; no `secrets.*` besides `GITHUB_TOKEN`; no SSH or server details |
| AC-8 | Workflow review; two quick pushes to `main` if they happen | `main` runs use per-SHA groups and aren't cancelled |
| AC-9 | Step 10 (user-run) | `dc pull` then `up`; no build output; data persists; old image kept; downtime a few seconds; loopback/caps unchanged |
| AC-10 | README review | The flow, the concepts, the publish check and the no-image case are all documented |
| AC-11 | Workflow review | New actions pinned to a major tag; runner/images unchanged |

## Risks
- **Package visibility:** a package first pushed by `GITHUB_TOKEN` is
  private by default. Step 8 makes it public once; until then a server
  `pull` fails with "unauthorized". The README says so.
- **Tag length:** CI uses 7 characters; the server's `git rev-parse --short`
  normally gives 7, and gives more only if a 7-character prefix becomes
  ambiguous. If that ever happens, the pull fails loudly ("not found"),
  and the fix is `--short=7` in the helper. Accepted, noted in the README.
- **Artifact size:** about 90–100 MB compressed per `main` run, kept for
  1 day. That's within GitHub's free limits for a public repository.
- **Secrets in CI logs:** the values are masked and never echoed; the
  check in step 6 searches for them without printing them.
- **Shared server:** the rollout changes only project `pms`; `pull`
  downloads about 100 MB; no build CPU is needed, so the load is lower than
  in step 12.
- **First run on `main` after merge:** if `publish` fails (for example a
  permissions problem), nothing reaches the registry and the server stays
  on `bd25e63`; fix and push again.

## Decisions needing approval
- (none) The workflow changes, image publishing and the two official
  artifact actions are this approved step's scope (spec 13, OQ answered).

## Files changed
- Modified: `.github/workflows/ci.yml` (header, concurrency, `production`
  and `publish` jobs), `compose.server.yaml` (no `build:`, registry image),
  `.dockerignore` (`compose.server.yaml`), `README.md` (server deployment,
  CI, new "Container registry concepts" section).
- No application code, migrations or tests changed.

**Build notes (2026-11-07):**
- Action pins checked with `git ls-remote`: the newest majors are
  `upload-artifact@v7` and `download-artifact@v8` (checkout still `@v7`).
- `docker save | gzip` of the image is about 58 MB, so the per-`main`
  artifact is smaller than the plan's 90–100 MB estimate.

## Test results
- Host: drift "No changes detected"; `check` no issues; full suite
  **415/415 OK**.
- Workflow YAML parses (PyYAML in a throwaway `python:3.12.16-slim-trixie`
  container): jobs `postgres`, `sqlite`, `production`, `publish`;
  `publish` needs all three.
- **Local run of the `production` job's checks** (Docker Desktop 29.5.2,
  separate project `pms13ci`, throwaway env file deleted afterwards):
  `compose.server.yaml config` OK (and refuses to interpolate without the
  env values); image built with the source label; db `Healthy`; all
  migrations applied; `check --deploy` IDs exactly
  W004/W008/W012/W016 and "identified 4 issues"; login **200**; `id -u`
  **10001**; no `ERROR` in the log; no secret names in inspect/history;
  no `.env*`/`*.local` in `/app`. Cleaned up with `down -v` (project
  `pms13ci` only) and the test image removed.
- **Step 7:** commit `0b0d976` pushed to `main`; CI run 42386988247:
  PostgreSQL, SQLite, Production image and Publish the image all
  **success**.
- **Step 8:** without any login, the GHCR token endpoint plus
  `GET /v2/amanshakya28515/pms-web/manifests/0b0d976` returned **200**:
  the image is already anonymously pullable (it seems to have taken the
  public repository's visibility), so no manual visibility change was
  needed. A PC `docker pull` wasn't run; the manifest check is the same
  registry request.
- **Step 10, server rollout (2026-11-08, user-run, output pasted):**
  checkout `0b0d976`; `dc pull web` pulled 5 layers in 6.4 s with no
  build; images: `ghcr.io/amanshakya28515/pms-web:0b0d976` (241 MB, new)
  next to `pms-web:bd25e63`/`bc7c504`/`7a7006a` (271 MB, kept);
  `migrate`: "No migrations to apply"; `up -d web`: db Healthy, web
  Started in 2.6 s; `ps`: `pms-web-1` on `ghcr.io/…:0b0d976`, port
  `127.0.0.1:8010->8000/tcp`; `pms-db-1` up 2 days (healthy, data
  volume untouched); start log: five Gunicorn INFO lines, no ERROR.
  *Not pasted:* the backup output, the `curl` code, the tunnel check.
- **Step 9, failure demo (2026-11-08):** branch
  `demo/13-broken-dockerfile`, commit `92b3379` appending the same stray
  `r` line as step 12. Run 42466158123: **failure**. Production image
  failed at "Build the production image"; PostgreSQL and SQLite passed
  (they don't use that file); Publish the image **skipped**. GHCR has no
  `:92b3379` (manifest 404). Branch deleted locally and on GitHub; `main`
  untouched (no `r` line). Q-82 is closed by this.
- All implementation steps done; status `built`.

## Review log

### 2026-11-08: review of the build
Scope: `57c2da5..0b0d976` (`ci.yml`, `compose.server.yaml`,
`.dockerignore`, `README.md`) plus the recorded CI, demo and server runs.
All 11 ACs are met, with evidence in Test results. Checked with no
finding:
- **Permissions:** only `publish` has `packages: write`; the token goes
  through an env var and stdin; no stored secrets; no server access.
- **The publish gate:** `if` plus the implicit `success()` on all three
  `needs`; PR events never publish.
- **Concurrency:** grouped per SHA on `main`, so runs aren't cancelled.
- **Throwaway secrets:** masked before use, written outside the
  workspace, never echoed.
- **Shell behaviour:** default `bash -e` without `pipefail`, so
  `logs | grep -q` and `save | gzip` behave as intended. A failed save
  leads to a failed `docker load` and nothing is published (fail-closed).
- **Server file:** no `build:` (fail loud); step 12 recovery keeps working
  through each commit's own Compose file.

| ID | Sev | Where | Finding | Suggested fix |
|---|---|---|---|---|
| Q-85 | Low | `.github/workflows/ci.yml:211` (`publish`) | Tags can be overwritten. Re-running the *whole* workflow for a `main` commit rebuilds the image (dependencies float within `~=`) and pushes it under the same `:<rev>` tag, replacing what the server may already run. Re-running only `publish` reuses the artifact and is safe. | Accept. Note in the README: re-run only failed jobs, never "Re-run all jobs" on an already published `main` commit. A lock file or digest-based deploys would remove it for good (their own step). `open` |
| Q-86 | Low | README "Updating to a new revision" | Old images pile up on the shared server (about 240–270 MB per revision, 4 kept today), and the README gives no safe clean-up command. `docker image prune`/`system prune` are rightly forbidden. | Accept for now. When disk matters, remove specific old tags only (`docker image rm pms-web:7a7006a`), keeping the previous revision for recovery. `open` |

No High or Medium findings. Status → `reviewed`.

### 2026-11-08: closed
Q-85 and Q-86 were accepted (Low, by default) and recorded in CLAUDE.md
Known limitations. Q-80 and Q-82 are closed and removed from there. No code
changed after the 415/415 run, so the suite wasn't re-run.
