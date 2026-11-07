---
step: 13
slug: cicd
status: approved
created: 2026-11-07
approved: 2026-11-07
---

# 13 — CI/CD: build once, publish, pull

## Goal
CI builds and verifies the production image itself and, for `main`, publishes
that exact image to GitHub's container registry. The server then updates by
pulling the tested image instead of building its own.

## Context / why now
- Step 10 CI tests the code with the development image, and that image is
  thrown away. Step 12's server builds its own production image from the
  checked-out code, so the image that runs was never tested by CI.
- Q-82: a broken production recipe passed CI and failed only on the server.
- Q-80: CI cancels superseded runs on `main`, so some `main` commits never
  get a result. That matters once a run decides what gets published.
- Building once and pulling everywhere is the standard pattern, and later
  steps (monitoring, Kubernetes) consume images from a registry.

Decided with the user (2026-11-07): the server is updated **by hand**
(continuous delivery, not automatic deployment), and the published image is
**public** (the repository is already public; images hold no secrets).

## User stories
- As the developer, I want CI to build and check the production image, so a
  broken production recipe is caught before it reaches the server.
- As the operator, I want to deploy the exact image CI tested, so what runs
  on the server is what was verified.
- As the operator of a shared server, I want updates to need no building on
  the server, so they are faster and use less of its CPU.

## Acceptance criteria
- **AC-1** Given any push or pull request, when CI runs, then it builds the
  production image from the deployment recipe, and a broken recipe turns the
  run red (closes Q-82).
- **AC-2** Given the built production image, when CI verifies it against a
  temporary PostgreSQL, then: migrations apply; the deployment check reports
  exactly the four known HTTPS warnings (W004, W008, W012, W016) and nothing
  else; the app runs as the non-root user; the login page answers 200; and the
  start log contains no ERROR line. Any failure turns the run red.
- **AC-3** The existing checks (migration drift, system check, full test suite
  on PostgreSQL and on SQLite) still run unchanged and must pass.
- **AC-4** Given a push to `main`, when every check (AC-1 to AC-3) passes, then
  the very image that was verified is published to GitHub Container Registry,
  tagged with the commit's short revision (the same naming as the server's
  `pms-web:<revision>`). If any check fails, nothing is published.
- **AC-5** Given a push to any other branch or a pull request, CI builds and
  verifies the image but never publishes it.
- **AC-6** The published image can be pulled without logging in, and contains
  no secrets: no env files, and no secret values in its layers, history or
  labels.
- **AC-7** Least privilege: only the publishing part on `main` may write to
  the registry; everything else stays read-only. CI uses no other secrets and
  gets no access to the server.
- **AC-8** Every commit pushed to `main` gets a finished CI run; a newer push
  no longer cancels a `main` run. Other branches may still cancel superseded
  runs (closes Q-80).
- **AC-9** Given a published, CI-green revision, when the user updates the
  server, then the server pulls that image and runs it after an explicit
  migration, with no build on the server. The data persists, the previous
  image stays available for recovery, the downtime stays a few seconds, and
  step 12's boundaries are unchanged: loopback only, resource caps,
  root-only secrets file, project-scoped commands.
- **AC-10** The README explains the build-once, pull-to-deploy flow, the
  registry in plain language, how to check that a revision was published,
  and the updated server routine, including what to do when a revision has
  no published image.
- **AC-11** Every external action and image stays pinned as in step 10.

## Out of scope
- Automatic deployment (CD): GitHub gets no SSH key or other access to the
  server.
- A private registry, registry tokens on the server.
- A moving `latest` tag; the server always pulls an exact revision.
- Image signing, SBOMs, vulnerability scanning, multi-architecture images
  (the server is x86_64 only).
- Cleaning up old images in the registry; Dependabot or digest pins.
- Running the full test suite inside the production image (the suite keeps
  running in the existing jobs).
- HTTPS, a domain or public exposure (S-2); monitoring; Kubernetes.
- Any change to the Django application.

## Open questions
- None. No new Python dependency. The plan may use GitHub's or Docker's
  official actions for registry login and image push; each is pinned like
  the existing ones (AC-11).
