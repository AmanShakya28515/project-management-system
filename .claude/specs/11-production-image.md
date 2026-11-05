---
step: 11
slug: production-image
status: done
created: 2026-10-31
approved: 2026-10-31
---

# 11 — Production image

## Goal
Prepare a Docker image suitable for later deployment: it runs Django through
Gunicorn as a non-root user, with DEBUG off and production configuration supplied
through the environment. Keep the existing development workflows unchanged.

## Context / why now
Step 10 automatically verifies the application on PostgreSQL and SQLite. The
current container is for development: it uses Django's development server, runs
as root and mounts the host source code. The next learning step prepares the
application package for deployment; it does not deploy it.

Existing application architecture, access rules and stack constraints in
CLAUDE.md continue to apply.

## User stories
- As a developer, I want a self-contained production image, so that the same
  prepared application can run without my Windows project folder.
- As a learner, I want to understand how production runtime settings differ
  from development settings before deploying to a server.

## Acceptance criteria
- **AC-1** Given a built production image and valid runtime configuration, when
  a container starts, then Gunicorn serves the Django application instead of
  Django's development server.
- **AC-2** Given a running production container, then its application server
  runs as a non-root user.
- **AC-3** Given the production image on a machine without the project source
  folder mounted, then the application starts and serves its existing pages
  using the code packaged in the image.
- **AC-4** Given the production runtime, then DEBUG is off. A configuration
  that attempts to enable DEBUG is rejected rather than serving debug pages.
- **AC-5** Given production startup, then the secret key, allowed hosts and
  PostgreSQL connection settings come from runtime environment values. Missing
  required values, a known development secret or wildcard allowed hosts cause
  startup to fail with a clear error that does not expose secrets. Production
  never silently falls back to SQLite or development credentials.
- **AC-6** Given valid production configuration and PostgreSQL 17, then existing
  authentication, workspace, project and task behaviour remains unchanged.
  Anonymous users still follow the existing login rules, and non-members still
  receive 404 for protected nested resources.
- **AC-7** Given the production configuration, then Django's deployment checks
  are run and assessed. No warning is silently suppressed; any warning that
  depends on later HTTPS or deployment infrastructure is explicitly documented
  with its reason and the work still required before public deployment.
- **AC-8** Given the finished step, then the existing Compose development
  workflow retains its development server, live reload, localhost-only port
  and PostgreSQL database, and the host virtualenv workflow retains SQLite.
- **AC-9** Given the finished step, then the existing CI jobs continue to pass
  migration drift, system checks and the full suite on both databases. Local
  verification also demonstrates that the production image builds and serves
  the application with DEBUG off, as non-root and without a source bind mount.
- **AC-10** Given the production image and tracked configuration, then no real
  secret, local environment file or local database is packaged or committed.
  Production secrets are supplied only at runtime.
- **AC-11** Given the documentation, then a learner can build and run the
  production image locally against PostgreSQL, supply the required environment
  values, run migrations explicitly, inspect logs and stop the container. It
  explains Gunicorn, non-root execution, baked-in code and DEBUG off in plain
  language, and clearly states the remaining deployment limitations.

## Out of scope
- Deployment, automatic delivery, registry publishing or GitHub settings changes
- Nginx, HTTPS termination, certificates, Kubernetes, monitoring or log services
- Application features, model changes, migrations or UI redesign
- Replacing Tailwind Play CDN or introducing a frontend build toolchain
- Additional CI jobs or a broader CI redesign
- Dependency locking, scanning, linters, formatters or unrelated dependencies
- Automatic database migration on application startup

## Open questions
All three proposed decisions below were explicitly approved by the user on
2026-10-31. No open question remains unresolved.

- **OQ-1 — New dependency (approved).** Approve Gunicorn as the production server
  dependency, as requested. No other new dependency is proposed.
- **OQ-2 — Boundary of production readiness (approved).** This step prepares and
  verifies the runtime image locally. Public deployment remains blocked on later
  HTTPS/security configuration and static-asset delivery decisions, including
  the existing Tailwind Play CDN limitation. Deployment-check warnings tied to
  that deferred work are documented, not treated as proof of public readiness.
- **OQ-3 — Production verification in CI (approved).** Retain the existing two CI
  jobs and verify the production image locally in this step. Automated
  production-image checks can be approved in a later CI or deployment step.
