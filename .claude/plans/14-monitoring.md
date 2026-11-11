---
step: 14
slug: monitoring
spec: .claude/specs/14-monitoring.md
status: approved
created: 2026-11-09
approved: 2026-11-09
---

# Plan 14 — Monitoring with Grafana

## Approach
A separate Compose project, **`pms-monitoring`**, next to the app's `pms`
project on the VPS. It has four services:

```
                 server (host network)                 monitoring network
 app 127.0.0.1:8010 <--probe--+                     +--------------------+
 host /proc /sys / ---------->|  alloy             |  prometheus  (metrics, 15 d)
 docker logs + cgroups ------>|  (collector)  ---->|  loki        (logs, 7 d)
                              +--------------------|  grafana     (dashboards)
                                                    +--------------------+
 Your PC --SSH tunnel--> 127.0.0.1:3010 (Grafana)
```

- **D-1 Grafana Alloy as the only collector.** One container does four
  jobs through its built-in components:
  - server metrics (`prometheus.exporter.unix`, node-exporter);
  - container CPU and memory (`prometheus.exporter.cadvisor`);
  - the login-page probe (`prometheus.exporter.blackbox`);
  - Docker logs (`discovery.docker` + `loki.source.docker`).

  It pushes metrics to Prometheus and logs to Loki. The alternative was four
  separate exporters plus Promtail (which is end-of-life): more containers,
  more RAM, and the same host access. This Alloy is a **new container in our
  own project**. The server's existing Alloy (a systemd service, on
  127.0.0.1:12345) is not touched. Ours listens on 127.0.0.1:12346.
- **D-2 Alloy uses the host network.** That is the only way to probe the app
  at `127.0.0.1:8010` without coupling the two projects. Joining the app's
  network would make `/opt/pms/dc down` fail ("active endpoints") and would
  tie the monitoring stack to the app's lifecycle (AC-9). As a consequence,
  Prometheus and Loki publish **loopback-only** ports (127.0.0.1:9095 and
  127.0.0.1:3110) so Alloy can push to them. Grafana reaches them over the
  monitoring network by service name.
- **D-3 Only the `pms` project is collected.** Logs: `discovery.docker`
  keeps only containers labelled `com.docker.compose.project=pms`, and a
  `service` label (web/db) comes from the Compose label. Container metrics:
  a relabel step keeps only `name=~"pms-(web|db)-1"`. Server metrics are
  server-wide by design (AC-5), using only the cpu, meminfo, loadavg,
  filesystem, diskstats and netdev collectors.
- **D-4 Prometheus only stores.** It receives metrics through
  `--web.enable-remote-write-receiver`, has no scrape jobs of its own, and
  keeps data with `--storage.tsdb.retention.time=15d` and
  `--storage.tsdb.retention.size=1GB`.
- **D-5 Loki** runs as a single binary with filesystem storage and the tsdb
  v13 schema. The compactor enforces `retention_period: 168h` (7 days);
  `auth_enabled: false`, because it's loopback- and network-only.
- **D-6 Grafana** is provisioned from the repository: two data sources
  (fixed UIDs) and one dashboard, **"PMS monitoring"**, with four rows:
  - **Uptime:** `probe_success` stat and timeline, `probe_duration_seconds`;
  - **Containers:** CPU rate, working-set memory against
    `container_spec_memory_limit_bytes`;
  - **Server:** CPU %, memory %, root-disk %, load;
  - **Logs:** a Loki logs panel with a `service` variable.

  It runs with anonymous access off, sign-up off, and analytics and update
  checks off. The admin user is `admin`. Its password is generated on the
  server into a root-only env file, `/etc/pms/monitoring.env` (step 12
  pattern), and is read only at Grafana's first start.
- **D-7 Resource caps (AC-8):**

  | Service | Memory | CPU |
  |---|---|---|
  | grafana | 192 MB | 0.5 |
  | prometheus | 256 MB | 0.5 |
  | loki | 256 MB | 0.5 |
  | alloy | 224 MB | 0.5 |
  | **Total** | **928 MB** | |

  Logs are capped at 3 × 10 MB per container, as in step 12. Restart policy:
  `unless-stopped`. Volumes: `prometheus-data`, `loki-data`, `grafana-data`,
  `alloy-data`.
- **D-8 Server helper `/opt/pms/mon`**, like `dc`: it `cd`s into
  `/opt/pms/app` and runs `docker compose -p pms-monitoring -f
  compose.monitoring.yaml --env-file /etc/pms/monitoring.env "$@"`. One
  checkout serves both projects. A configuration change takes effect on
  `mon up -d`.
- **D-9 CI (AC-12):** a new `monitoring` job. It starts the stack on the
  runner with a throwaway, masked Grafana password and checks:
  - Grafana `/api/health` is OK, with both data sources and the dashboard
    provisioned (Grafana API);
  - Loki `/ready` answers;
  - Prometheus has received Alloy's `node_*` and `probe_*` series (the probe
    may report down; the series must exist);
  - each image is pinned.

  It isn't added to `publish`'s `needs`: the app image doesn't depend on
  monitoring configuration.
- **D-10 Pins:** the exact current releases of `grafana/grafana-oss`,
  `prom/prometheus`, `grafana/loki` and `grafana/alloy`, looked up at build
  time and recorded in the plan.

## Data model & migrations
None. No application code, settings, templates or image changes.

## URLs, views, templates
None (the app is unchanged).

## Implementation steps
- [x] 1. Look up and pin the four image versions (D-10).
- [x] 2. `compose.monitoring.yaml` (repository root, beside the other
  Compose files): the four services, the caps, the volumes and the loopback
  ports `127.0.0.1:3010` (Grafana), `127.0.0.1:9095` (Prometheus) and
  `127.0.0.1:3110` (Loki). Alloy uses `network_mode: host` and its listener
  is `127.0.0.1:12346`. Alloy's read-only mounts: `/proc`, `/sys` and `/` (at
  `/host/...`), `/var/lib/docker` and `/var/run/docker.sock`. The Grafana
  password is required: `${GRAFANA_ADMIN_PASSWORD:?…}`.
- [x] 3. `monitoring/` configuration:
  - `alloy/config.alloy` (D-1, D-3);
  - `loki/loki.yaml` (D-5);
  - `grafana/provisioning/datasources/datasources.yaml`;
  - `grafana/provisioning/dashboards/dashboards.yaml`;
  - `grafana/dashboards/pms.json` (D-6).
- [x] 4. `.dockerignore`: add `monitoring/` and `compose.monitoring.yaml`, so
  the app image stays unchanged.
- [x] 5. **CI:** the `monitoring` job (D-9).
- [x] 6. **Local verification:**
  - `compose config --quiet`, `alloy fmt` on the config, Loki
    `-verify-config`, the JSON parses;
  - start the stack on Docker Desktop if host networking is available;
    otherwise CI is the check;
  - the Django suite, drift and `check` (expected unchanged).
- [ ] 7. **Commit and push** (only when the user asks); CI green, including
  the new job.
- [ ] 8. **Server rollout** (user-run, short batches):
  1. **Inventory before:** `ss -ltn` (ports 3010/3110/9095/12346 free) and
     `systemctl is-active alloy nginx`.
  2. Create `/etc/pms/monitoring.env` (root, 600) and the helper
     `/opt/pms/mon`.
  3. The app update routine to the new commit (backup, fetch, checkout,
     `dc pull web`, `up -d web`), because `PMS_REVISION` follows the
     checkout.
  4. `mon pull`, `mon up -d`, `mon ps`, `docker stats --no-stream`.
  5. **Inventory after:** the same commands; only the four new loopback
     ports are added.
- [ ] 9. **Checks** (user-run, results recorded):
  - tunnel `-L 3010:127.0.0.1:3010`; log in; the dashboard shows all four
    rows with data;
  - `dc stop web`: within about a minute Uptime shows down; `dc start web`:
    up again;
  - Logs show a request line and a Gunicorn start line;
  - `mon restart`: data and the login survive;
  - from the PC, `<server-ip>:3010` times out.
- [x] 10. **README:** a "Monitoring (step 14)" section covering the
  components, the first-time setup, everyday `mon` commands, the tunnel, a
  tour of the dashboard, how to update and remove the stack, and safety
  notes. Plus "Monitoring concepts in plain language".

## Test plan
No Django tests: the application doesn't change. Verification is the CI
job, local configuration checks and the user-run server checks.

| AC | Where | What it asserts |
|---|---|---|
| AC-1 | Compose review; step 8 inventory; step 9 PC check | Every published port is `127.0.0.1:`; Alloy listens on loopback; the public IP times out on 3010 |
| AC-2 | CI (anonymous `/api/dashboards` → 401); step 9 | Login is required; sign-up is off; the password is only in `/etc/pms/monitoring.env` (600) and CI's masked value |
| AC-3 | Step 9 stop/start | Uptime shows down within about 1 min, then up; the response-time graph is shown |
| AC-4 | Step 9 dashboard | CPU and memory for `pms-web-1` and `pms-db-1`, plus the 512 MB limit line |
| AC-5 | Step 9 dashboard | Server CPU, memory and root-disk % |
| AC-6 | Step 9 Logs row; config review | A web request line and a Gunicorn start line; filter by service; only project `pms` collected |
| AC-7 | CI (data sources and dashboard via the API); step 9 after `mon down`/`up` | Provisioned automatically, nothing clicked |
| AC-8 | Compose review; step 8 `docker stats` | Caps total ≤ 1 GB; retention flags/config; log caps |
| AC-9 | Step 9 (`dc stop/start` while monitoring runs; `mon restart` leaves `pms-*` untouched); README routine unchanged | The two lifecycles are independent |
| AC-10 | Step 9 `mon restart` | History, logs and the Grafana login survive. A server reboot isn't forced on the shared server (named volumes plus `unless-stopped`, as in step 12) |
| AC-11 | Step 8 before/after inventory | Same services active, only the four new loopback ports, no Docker daemon or firewall change |
| AC-12 | CI `monitoring` job; Compose review | The stack starts and verifies in CI; exact image tags |
| AC-13 | README review | All the listed topics are covered |

## Risks
- **Alloy's host access** (see DA-1): it can read the host filesystem, the
  Docker API and Docker's data. Mitigations: an official image pinned to an
  exact version, read-only mounts, no listener beyond loopback, and a
  configuration that comes only from the repository.
- **Loopback ports without authentication** (see DA-2): local processes on
  the shared server could read the app's metrics and logs, or push junk
  data. The logs hold request lines and no secrets (Django doesn't log
  POST bodies; settings reject DEBUG).
- **Port clash:** the step 8 inventory checks that the four ports are free
  before starting. The known used ports include 12345 (the existing Alloy),
  8000, 8010 and 8081.
- **RAM on a shared server:** 928 MB of caps against about 5.4 GB
  available. If memory is tight, `mon stop` frees it immediately (AC-9).
- **One checkout for both projects:** checking out a step 12 or 13 commit
  for app recovery removes `compose.monitoring.yaml` from the checkout. The
  running monitoring containers keep running; `mon` commands work again
  after checking out a step 14+ commit. This is documented.
- **The Grafana password is used only at first start:** changing the env
  file later doesn't change it. The README gives the `grafana cli admin
  reset-admin-password` command.
- **Docker Desktop** may not support `network_mode: host` locally; CI
  (Linux) is the authoritative check.

## Decisions needing approval
- **DA-1 — Alloy's host access:** host network, plus read-only mounts of
  `/`, `/proc`, `/sys`, `/var/lib/docker` and the Docker socket. Server and
  container metrics and Docker logs can't be collected without this kind of
  access; any collector (node-exporter, cAdvisor, Promtail) needs the same.
  *Recommended: accept, with the mitigations under Risks.*
  **Answer: accepted** (user, `/plan 14 approve`, 2026-11-09).
- **DA-2 — Prometheus and Loki on loopback ports, without authentication**
  (a consequence of DA-1's host network). The alternative is to join the
  app's network, which breaks `dc down` and couples the stacks (AC-9).
  *Recommended: accept.* **Answer: accepted** (user, `/plan 14 approve`,
  2026-11-09).

## Files changed
- Created:
  - `compose.monitoring.yaml`;
  - `monitoring/alloy/config.alloy`;
  - `monitoring/loki/loki.yaml`;
  - `monitoring/prometheus/prometheus.yml`;
  - `monitoring/grafana/provisioning/datasources/datasources.yaml`;
  - `monitoring/grafana/provisioning/dashboards/dashboards.yaml`;
  - `monitoring/grafana/dashboards/pms.json`.
- Modified: `.github/workflows/ci.yml` (new `monitoring` job; not in
  `publish`'s `needs`), `.dockerignore` (monitoring files), `README.md`
  ("Monitoring (step 14)" section and "Monitoring concepts").
- No application code, migrations, tests or app image inputs changed.

**Build decisions and deviations (2026-11-09):**
- **Pins:** `grafana/grafana:13.3.0`, `prom/prometheus:v3.15.1`,
  `grafana/loki:3.6.20`, `grafana/alloy:v1.21.3`.
  - `grafana/grafana`, not the plan's `grafana/grafana-oss`: the `-oss`
    repository stopped at 13.0.2 (June), and `grafana/grafana` is the same
    OSS edition.
  - Prometheus v3.16.0 is 4 days old, so the settled v3.15.1 is used.
- **Memory caps rebalanced (same 928 MB total):** grafana 384, prometheus
  192, loki 192, alloy 160. Measured: Grafana 13 sat at its 192/256 MB
  caps (anon memory about 254 MB, memory.max events, no OOM kill); under
  384 it uses about 246 MB. The others use about 33 (Prometheus), 33–57
  (Loki) and 60–74 MB (Alloy).
- **Extra Alloy mounts:**
  - `/run/containerd/containerd.sock:ro`: cAdvisor's Docker factory failed
    without it on Docker 29 ("unable to create containerd client"), so no
    container metrics were collected. It's the same kind of access as DA-1.
  - `/run/udev/data:ro`: silences diskstats' udev error.
- **Smaller additions:**
  - `cgroup: host` for Alloy;
  - Grafana's preinstalled-plugin download, news feed and update checks
    turned off;
  - a minimal `prometheus.yml` (no scrape jobs);
  - the dashboard has a `search` textbox variable next to `service`.

## Test results
- **Host:** drift "No changes detected"; `check` no issues; full suite
  **415/415 OK**.
- **Configuration checks:**
  - the workflow YAML parses (jobs postgres, sqlite, production, monitoring,
    publish; `publish` needs only the first three);
  - `compose.monitoring.yaml config` OK, with all four images exact;
  - `alloy fmt` OK; Loki `-verify-config` exit 0; the dashboard JSON parses.
- **Local stack on Docker Desktop 29.5.2**, plus the real app image
  `pms-web:0b0d976` run locally as project `pms` with throwaway env files
  (all deleted afterwards):
  - Grafana `/api/health` ok (13.3.0); anonymous `/api/search` → **401**;
    both data-source health checks OK; dashboard "PMS monitoring" in
    folder PMS;
  - Loki ready;
  - Prometheus has `node_*`, `probe_success` = 1 and `probe_duration_seconds`
    (about 2.5 ms);
  - `container_memory_working_set_bytes` and the CPU series exist for
    exactly `pms-web-1` and `pms-db-1`, with a limit of 536870912
    (512 MB);
  - all panel queries return values;
  - Loki holds `service` web and db logs, including "Starting gunicorn"
    and `GET /accounts/login/` lines.
- **AC-3 locally:** `stop web` → `probe_success` 0 seen after **3 s**;
  `start web` → 1 after **16 s**.
- **AC-10 locally:** after recreating the stack, the Grafana login works
  (200) and Prometheus still has 17 probe samples from the last hour.
- Local clean-up: `down -v` on the two local projects only; no `pms*`
  containers left.
- **Pending (needs a push and the user):** step 7 (CI green, including the
  new job), steps 8–9 (server rollout and checks).

## Review log
_(filled in by /review)_
