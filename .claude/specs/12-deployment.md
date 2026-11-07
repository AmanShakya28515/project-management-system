---
step: 12
slug: deployment
status: done
created: 2026-10-31
approved: 2026-10-31
---

# 12 — Deployment

## Goal
Deploy the Step 11 production application to one real Linux server using Docker
Compose. Keep the deployment manual and understandable as a DevOps learning step.

## Context / why now
Step 11 packages Django with Gunicorn, DEBUG off, non-root execution, baked-in
code, runtime configuration and PostgreSQL support. It has been verified locally,
but no application is running on a remote server yet.

This step learns how that package becomes a running remote application, what
stays on the server, and how to operate and update it. Existing application
architecture, access controls and development conventions in CLAUDE.md apply.
HTTPS and static-asset delivery remain unresolved deployment boundaries unless
explicitly approved here.

## User stories
- As a learner, I want to run the application on one remote server, so that I
  understand the difference between building an image and deploying it.
- As an operator, I want repeatable manual start, stop, update and backup
  procedures, so that I can manage the application without automatic CD.

## Acceptance criteria
- **AC-1** Given the approved server choice and working administrative access,
  then the application runs on one real Linux server through Docker Compose,
  with Django/Gunicorn and PostgreSQL 17 in separate containers. The application
  retains Step 11's non-root execution, DEBUG off and baked-in code; no host
  source bind mount is required for the running application.
- **AC-2** Given a deployment, then its source revision is identifiable and is
  selected manually from a revision with successful existing CI checks. Building
  or deploying does not change CI triggers or start automatic deployment.
- **AC-3** Given server startup, then required production configuration and
  secrets are supplied from server-side storage, excluded from Git and image
  builds, and readable only by the deployment administrator and required system
  processes. Secrets are not included in documentation or verification output.
- **AC-4** Given the application and database containers are stopped, restarted
  or recreated without an explicit data-deletion action, then PostgreSQL data
  remains available. Persistence is demonstrated with a disposable application
  record. The database has no published host port.
- **AC-5** Given a first deployment or an update requiring migrations, then the
  operator runs migrations explicitly and checks their result before verifying
  the application. Server startup does not automatically run migrations.
- **AC-6** Given the running deployment, then verification demonstrates server
  startup, database connectivity, readable application/database logs and HTTP
  access over the approved access path. Login and an authenticated
  workspace/project/task flow work; anonymous redirects, non-member nested 404
  responses and CSRF protection retain their existing behaviour.
- **AC-7** Given the approved HTTP-only boundary, then the application is not
  openly reachable from the public Internet. Administrative access is restricted
  to the operator, and the documented access method permits remote verification
  without exposing the application port publicly (see OQ-3).
- **AC-8** Given an operator following the documentation, then they can start,
  stop and restart the services, inspect their state/logs and verify the running
  revision. A restart is demonstrated without losing the disposable record.
- **AC-9** Given a newly released, CI-passed revision, then the documented
  manual update flow covers selecting that revision, taking a backup, preparing
  its image, explicitly applying migrations, recreating the application and
  checking its behaviour. One manual redeployment is demonstrated; no product
  feature change is needed to demonstrate it. Expected downtime and recovery
  steps are stated, including that an old image cannot safely undo arbitrary
  database migrations.
- **AC-10** Given the learning deployment's backup procedure, then an operator
  can create a PostgreSQL backup, keep a protected copy off the server, and
  restore it into a disposable database to demonstrate recovery of a known
  record. Normal operation and the restore demonstration do not overwrite or
  delete the running application database (see OQ-5).
- **AC-11** Given the finished step, then host SQLite development, local
  development Compose and the existing CI workflow remain unchanged. Existing
  application tests and required Django checks remain green; remote deployment
  evidence is recorded separately from local verification.
- **AC-12** Given the documentation, then it explains build versus deployment,
  what resides on the server (images, containers, configuration, database data
  and backups), server-side Compose, environment values, persistence, explicit
  migrations and the manual update lifecycle in plain language. It lists what
  remains before safe public exposure: HTTPS/security settings, static-asset
  delivery including the existing Tailwind Play CDN limitation, and any
  deployment-check warnings still unresolved. No warning is silently suppressed.

## Out of scope
- Automatic CD, changes to GitHub CI or automatic deployment on push
- Kubernetes, monitoring, centralized logging, load balancing or autoscaling
- Multiple servers, managed database services or zero-downtime deployment
- Application features, model changes, UI redesign or frontend build tooling
- Domain/DNS, Nginx or HTTPS unless explicitly approved by revising this spec
- Registry publishing under the proposed server-build approach
- Automated backup scheduling, point-in-time recovery or a high-availability setup
- Infrastructure-as-code tooling or automatic purchase/provisioning of paid resources

## Open questions
All five proposed decisions were explicitly approved by the user on
2026-10-31. No open question remains unresolved.

- **OQ-1 — Server/provider (approved).** Use the user's existing real Linux
  server. Do not provision or purchase another server. During planning, inspect
  and record its actual OS/version, CPU architecture, Docker and Compose
  availability, administrative SSH access, and available storage before
  deployment work proceeds. If any requirement is missing, report it and agree
  on next steps before deployment.
- **OQ-2 — Getting code/image to the server (approved).** Manually fetch a selected
  CI-passed Git revision onto the server and build the Step 11 production image
  there. Then run that image with server-side Compose. This teaches build and
  deployment as separate actions without a registry. Do not copy local secrets
  or databases, depend on an uncommitted working tree, or imply that rebuilding
  floating dependency ranges produces byte-identical images. Preserve the prior
  image/revision for recovery; no GitHub write credential is needed for public
  source access.
- **OQ-3 — HTTP-only or HTTPS/Nginx (approved).** HTTP-only private learning
  deployment, with the application port bound to server loopback and reached
  through an SSH tunnel. Do not expose plain HTTP login publicly. No Nginx,
  certificate or domain is introduced; retain the documented Step 11 HTTPS
  warnings and static-asset limitations. This moves the app to a real server
  without claiming it is ready for public users.
- **OQ-4 — Server environment storage (approved).** A separate administrator-owned
  environment file on the server, outside the source checkout/build context,
  with restrictive permissions. Generate distinct server secrets there; do not
  reuse local rehearsal credentials. No external secrets manager in this step.
- **OQ-5 — Persistence/backups (approved).** A dedicated PostgreSQL named volume
  on persistent server disk, plus manual logical backups before updates and a
  tested restore into an isolated disposable database. Keep at least one
  protected off-server copy under the user's control. A volume is persistence,
  not a backup; server/disk deletion may destroy it. No automated retention or
  disaster-recovery guarantee is claimed for this learning deployment.
