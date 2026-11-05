---
step: 12
slug: deployment
spec: .claude/specs/12-deployment.md
status: approved
created: 2026-10-31
approved: 2026-10-31
---

# Plan 12 — Deployment

## Approach
- Use the user's existing Linux server only. First inventory OS/version,
  architecture, Docker/Compose, administrative SSH and free storage; record
  evidence and stop before deployment if access or capacity is insufficient.
- Manually fetch a selected CI-passed revision, build the Step 11 production
  image on the server, and run it with a separate server-side Compose file.
  Bind the application to loopback; verify over an SSH tunnel. No registry,
  CI changes or public HTTP access.
- Store distinct production secrets in an administrator-owned environment file
  outside the checkout/build context. PostgreSQL uses its own persistent named
  volume and has no published port. Migrations remain explicit.
- Demonstrate restart persistence, a manual update with a stated downtime window,
  a protected off-server logical backup and a restore to a disposable database.
  Keep the existing application database untouched during restore verification.
- Document server contents, operations, update/recovery steps and remaining
  HTTPS/static delivery limitations. Do not add dependencies or app features.

## Data model & migrations
No model or migration changes. Apply existing migrations explicitly on the server.

## URLs, views, templates
No application URL/view/template changes. Verify existing access behaviour over
the private SSH tunnel.

## Implementation steps
- [x] 1. Before deployment, connect to the existing server with the user's
  administrative SSH access. Record OS/version, CPU architecture, Docker and
  Compose versions/availability, access method and available persistent storage.
  Do not install, upgrade, provision or purchase anything until gaps are reported
  and the user agrees on next steps.
- [ ] 2. Select a clean, CI-passed Git revision and manually fetch it to a
  deployment directory. Record its commit; ensure the checkout/build context
  contains no local secrets or databases.
- [ ] 3. Add server-side Compose configuration and deployment instructions for
  production web + PostgreSQL, private loopback access, restricted secret file,
  persistent database storage and health readiness. Preserve the Step 11 image
  settings and non-root runtime. Keep local development and CI files unchanged.
- [ ] 4. Deploy manually: build image, start database, run migrations explicitly,
  start web, verify status/logs/database and HTTP through SSH tunnel. Demonstrate
  login, workspace/project/task flow, anonymous redirect, outsider 404 and CSRF.
- [ ] 5. Demonstrate container recreation/restart persistence with a disposable
  record. Confirm application and database ports are private as specified.
- [ ] 6. Demonstrate backup and recovery: create a logical PostgreSQL backup,
  transfer a protected copy off-server, restore to a disposable isolated
  database, and verify the known record without touching the live database.
- [ ] 7. Demonstrate a manual update to another CI-passed revision, with a
  backup, image build, explicit migrations, application recreation and smoke
  checks. Record downtime and recovery limits; do not claim old-image rollback
  can reverse arbitrary schema migrations.
- [ ] 8. Document build versus deployment, server contents, start/stop/restart,
  status/log inspection, revision identification, backup/restore, update steps,
  HTTP tunnel access and remaining public-exposure requirements.
- [ ] 9. Verify locally in the standard order and record local results separately
  from remote server evidence. Confirm CI configuration and local workflows have
  no changes. Review deployment-check output without suppressing warnings.

## Test plan
| AC | Test module / verification | What it asserts |
|---|---|---|
| AC-1 | Remote Compose state, image inspection, HTTP tunnel | Separate web/PG17 services; production image UID, DEBUG, baked code and no source mount. |
| AC-2 | Selected commit and GitHub Actions result | Manually selected revision has a successful existing CI run; no CI/CD changes or auto-deploy. |
| AC-3 | Remote file permissions, Git status, image inspection | Secret file is outside checkout/build context, administrator-restricted and absent from image/history/docs/output. |
| AC-4 | Disposable record across stop/recreate | PostgreSQL named volume retains record; database has no host-published port. |
| AC-5 | Remote deployment/update command record | Explicit migrations run and pass before app verification; server command does not migrate automatically. |
| AC-6 | HTTP tunnel and server/database logs | DB-connected app serves login and member workspace/project/task flow; anonymous redirect, outsider nested 404 and CSRF checks pass. |
| AC-7 | Server Compose and firewall/listener inspection | App bound to loopback, reached only through SSH tunnel; admin access limited to user. |
| AC-8 | Operator runbook rehearsal | Start, stop, restart, status, logs and running revision checks work; record persists. |
| AC-9 | Manual update rehearsal | CI-passed revision selected, backup made, image built, migrations explicitly run, app recreated/checked; downtime and migration rollback limits documented. |
| AC-10 | Backup/restore rehearsal | Off-server backup restored in isolated disposable DB; known record recovered; live DB remains unchanged. |
| AC-11 | Existing local host/Compose/CI-equivalent checks and diff | Existing tests/checks pass; local development and CI configs unchanged; local and remote evidence distinguished. |
| AC-12 | Documentation and `check --deploy` output | Required concepts/commands explained; every warning assessed, public-exposure blockers named. |

## Risks
- **Unknown server and access:** no host/account details or SSH authorization
  are present in the repository. Step 1 requires the user to provide or make
  available the existing server connection and authorize access. Do not guess
  a host or expose credentials in tool output.
- **Server mutation:** deployment changes remote services and writes server data.
  Do not proceed past inventory until the approved plan and the user's authorized
  access are available. Never install upgrades or provision resources implicitly.
- **Public HTTP:** login over public HTTP exposes credentials. Restrict app to
  loopback and verify only through the SSH tunnel; document that it is not public.
- **Persistent data:** named volumes survive container replacement but not every
  disk/server failure. Keep protected off-server backups; avoid destructive volume
  commands and restore only into an isolated disposable database.
- **Update compatibility:** migrations can make old code incompatible. Backup
  first, state downtime, and do not promise image rollback undoes schema changes.
- **Remote verification:** network, SSH, server storage and package/image fetches
  can fail. Record what was measured; never substitute local checks for remote
  evidence or mark an incomplete deployment done.

## Decisions needing approval
- (none; OQ-1 through OQ-5 were explicitly approved with the spec)

## Files changed
- **Created:** `compose.server.yaml`: project `pms`; web image tagged
  `pms-web:${PMS_REVISION}`; `restart: unless-stopped`; port
  `127.0.0.1:8010` only; 512 MB / 1 CPU caps per service; json-file logs
  capped at 3 × 10 MB; `db` with no ports, the TCP health check and the
  `pms_postgres-data` volume. Validated with `docker compose config`;
  missing variables are refused.

Expected repository changes: a deployment-specific Compose file and
`.dockerignore`/README updates only if needed. No changes to existing development
Compose, Dockerfile, application, or CI workflow are planned. Remote server
changes and evidence will be documented without committing secrets.

## Test results
### 2026-10-31 — Build preflight blocked
- Confirmed the spec and plan are approved. The plan's step 1 requires SSH
  inventory before any deployment changes.
- OpenSSH client is installed, but repository inspection found no server address,
  account, SSH configuration or authorized connection details. No server identity
  is present in the available environment.
- Stopped before connecting, installing, provisioning or changing anything.
  No local code, tests, Django checks, build or remote action was performed.
- Status remains `approved`. Provide/make available the existing server's SSH
  target and authorized access, then resume with `/build 12 resume`.

### 2026-11-05 — Step 1 server inventory (user-run, read-only)
**Method change (user's decision):** the server is a shared Hostinger VPS
running 5–6 live projects, so the user runs every command over their own
SSH session and pastes the output. Claude never connects to the server.
All results below are **user-reported**.

| Item | Result |
|---|---|
| OS / arch | Ubuntu 24.04.4 LTS, x86_64 |
| CPU / RAM | 2 cores; 7.8 GiB total, ~5.4 GiB available; 4 GiB swap |
| Disk `/` | 96 G, 64 G free (34% used) |
| Docker / Compose | **Not installed** (gap; see below) |
| Access | root SSH session |
| Firewall | UFW active, default deny incoming, routed disabled; allows 22, 80, 443, 6380 (labelled as an mTLS Redis for another project) |
| Ports in use | public 22/80/443/6380; loopback 3306, 33060, 6380, 8081, 12345, 65529, 53 |
| Networks | only `lo` and `eth0`; no `172.17.0.0/16` in use, so no clash with Docker's default bridge |

**Gap reported (per plan step 1):** Docker and Compose are missing. The
proposed next step is to install Ubuntu's `docker.io` + `docker-compose-v2`
after a Hostinger snapshot, with before/after checks of running services
and listening ports. Awaiting the user's agreement; nothing installed yet.
Our app port must avoid the ports above and stay on `127.0.0.1`.

**Docker installed (user agreed, 2026-11-05):**
- A fresh Hostinger snapshot was taken first (2026-11-05 13:23, expires
  2026-11-06); an older weekly auto-backup also exists.
- `apt-get install docker.io docker-compose-v2`: Docker 29.1.3, Compose
  2.40.3; `hello-world` ran.
- Before/after diff: services added `docker`, `containerd` and
  `packagekit` (started by apt, transient); none removed. Ports added only
  `127.0.0.1:44975` (loopback; containerd's helper). UFW unchanged.
- Rollback without the snapshot: `apt-get remove docker.io docker-compose-v2`.

**Deviation:** Docker was missing, so plan step 1 was extended with this
install, as the spec's OQ-1 allows once the gap is reported and agreed.

## Review log
_(filled in by /review)_
