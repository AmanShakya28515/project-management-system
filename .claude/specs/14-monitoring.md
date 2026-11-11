---
step: 14
slug: monitoring
status: approved
created: 2026-11-09
approved: 2026-11-09
---

# 14 — Monitoring with Grafana

## Goal
The operator can open private Grafana dashboards that show whether the
deployed app is up, how much CPU, memory and disk it and the server use,
and the app's and database's logs, all in one place, without SSHing in to
run `docker stats` or `logs`.

## Context / why now
- Step 12 deployed the app privately on the shared VPS. Step 13 made updates
  pull a CI-verified image. Today the only way to see the app's health is to
  run commands by hand on the server.
- Monitoring is the next DevOps stage in CLAUDE.md's roadmap. It needs a
  running deployment to watch, and step 12 provides one.

Decided with the user (2026-11-09):
- the monitoring stack runs **on the VPS, privately**, beside the app, like
  step 12, reached only through the SSH tunnel;
- **no application code changes**: what is measured comes from outside the
  app (containers, server, logs, a probe);
- **dashboards only**, with no alerts.

## User stories
- As the operator, I want to see at a glance whether the app is up and how
  fast its login page answers, so I notice an outage without logging in to
  the server.
- As the operator of a shared server, I want to see the app's and the whole
  server's CPU, memory and disk use, so I know the app and its monitoring
  don't crowd out the other sites.
- As the operator, I want to search the app's and the database's logs in
  one place, so I can find an error without running commands on the server.

## Acceptance criteria
- **AC-1 Private access.** Grafana is reachable only from the server itself
  and through the operator's SSH tunnel, like the app. From the internet,
  Grafana and every other monitoring component give no response. None of
  them publishes a port beyond the server's loopback.
- **AC-2 Login.** Grafana needs a login. Anonymous access and self-sign-up
  are off. The admin password is generated on the server, kept in a
  root-only file outside the checkout, and never appears in Git, an image
  or the docs.
- **AC-3 Uptime.** A dashboard shows whether the app's login page answers
  200, and its response time, over time. When the app is stopped, the
  dashboard shows it as down within about a minute; when it is started
  again, as up.
- **AC-4 Containers.** A dashboard shows CPU and memory over time for the
  app and database containers, next to their 512 MB limits.
- **AC-5 Server.** A dashboard shows the whole server's CPU, memory and disk
  use over time, so the effect on the other sites is visible.
- **AC-6 Logs.** The app's and the database's container logs can be viewed
  and searched in Grafana, filtered by service, including a recent
  request line and a Gunicorn start line. Only this project's containers'
  logs are collected; other sites' logs aren't.
- **AC-7 Dashboards as code.** The data sources and dashboards come from
  the repository and appear automatically on a fresh start, with no manual
  clicking. Recreating the stack keeps them.
- **AC-8 Bounded resources.** Every monitoring component has a memory and
  CPU cap, with a total memory budget of at most 1 GB. Stored metrics and
  logs are kept for a limited time (about 15 days for metrics, 7 days for
  logs), and the components' own logs are capped like the app's.
- **AC-9 Independent of the app.** The monitoring stack can be started,
  stopped, updated or removed without restarting or changing the app or
  its database, and the step 12/13 update routine is unchanged. Stopping
  monitoring loses only monitoring data.
- **AC-10 Persistence.** Metrics, logs and Grafana's own state survive a
  restart of the monitoring stack and a server reboot.
- **AC-11 Shared-server safety.** Nothing already on the server changes:
  the existing Grafana Alloy agent, nginx, the other sites, the firewall
  and Docker's settings stay as they are. Every command is scoped to the
  monitoring project; the user runs every server command, as in step 12.
- **AC-12 Pinned and checked.** Every monitoring image is pinned to an exact
  version. CI checks that the monitoring configuration is valid, so a
  broken configuration is caught before it reaches the server.
- **AC-13 Documented.** The README explains, in plain language: what each
  component does; how to start, stop, update and remove the stack; how to
  open Grafana through the tunnel; how to read each dashboard; and the
  monitoring concepts (metrics, logs, scraping, retention, probes).

## Out of scope
- Alerts and notifications (email, chat): a later step.
- Metrics from inside Django (request counts, error rates, latency per
  view), or any change to the application or its images.
- Public access, a domain, HTTPS or nginx in front of Grafana (S-2).
- Grafana Cloud or any data leaving the server.
- Monitoring the other sites, their logs, or nginx/PHP/MySQL internals
  (server-wide CPU, memory and disk only).
- Tracing, profiling, long-term storage or high availability.
- Automatic deployment of the monitoring stack; Kubernetes.

## Open questions
- None. No new Python dependency. The monitoring components are new
  container images, pinned per AC-12; the plan names and justifies each.
