---
step: 01
slug: user-authentication
spec: .claude/specs/01-user-authentication.md
status: done
created: 2026-10-01
approved: 2026-10-01
---

# Plan 01 — User authentication

## Starting state (checked 2026-10-01)
- The repo holds only `CLAUDE.md` and `.claude/`. There is no Django project,
  no `.venv` and no `requirements.txt`.
- Python on this machine (`py -0p`): **3.13 and 3.11 only. 3.12 is not
  installed.** Per D-1, the user installs 3.12 before `/build` (step 0).

So this step also bootstraps the project.

## Approach

Use **Django's built-in auth wherever it already meets the spec**. Add custom
code only where the spec goes beyond Django's defaults: case-insensitive
usernames and emails, the registration flow, and the logout message.

| Concern | Choice | Why not the obvious alternative |
|---|---|---|
| User model | `accounts.User(AbstractUser)`, created **before the first `migrate`** | Changing Django's user model after the first migration is very hard (CLAUDE.md). Subclassing `AbstractUser` keeps every built-in auth view, form and admin working unchanged. |
| Case-insensitive uniqueness (username, email) | **Database** `UniqueConstraint(Lower(...))` on the model, **plus** field-level checks in the registration form | The form check alone could be beaten by two simultaneous sign-ups. The database constraint alone would show the error at the top of the form instead of next to the field (AC-3/4 want it on the field). Since Django 4.1, ModelForms also check model constraints, so the admin is covered too. `Lower()` constraints work on both SQLite and PostgreSQL, so the later database switch is safe. Usernames stay Unicode (D-3). The SQLite limitation where only ASCII letters ignore case is accepted and documented (see Risks). |
| Case-insensitive login (AC-9) | Override `UserManager.get_by_natural_key()` to look up `username__iexact` | Django's standard login backend already calls this method. Overriding one method gets case-insensitive login in the login page, the admin and `createsuperuser`, without writing a custom backend. The backend's protection against timing attacks on unknown usernames stays in place. This is safe because the constraint guarantees at most one match. |
| Display casing | The username is stored exactly as typed at registration and never changed when someone logs in | Matching ignores case. Storage and display keep the original casing (AC-9/14/21). |
| Login | Django's `LoginView` with `redirect_authenticated_user=True` | It already provides: safe `next` handling (it only follows links to this site → AC-17), the generic error message (AC-10), keeping the typed username (AC-10), rejecting inactive users (AC-11), and a fresh session ID on login. |
| Logout | A small subclass of Django's `LogoutView`. Its `post()` calls `super().post()` **first**, which logs the user out, flushes the session and builds the redirect. **Only then** does it add the message. | Since Django 5.0, `LogoutView` only accepts POST, so a GET gets 405 (AC-13). Adding the message *after* logout means it is stored in the new, post-logout request state, so nothing depends on a pre-logout message surviving the flush (AC-12). |
| Registration | `RegisterView(FormView)` with `RegistrationForm(UserCreationForm)` | `UserCreationForm` already provides password confirmation, the password-strength checks (AC-6), password hashing (AC-22) and clearing the password fields when the form is shown again (AC-7). We add a required email field and the case-insensitive checks. |
| Dashboard and root | A new **`core`** app | The dashboard will grow project and task content in later steps. Putting it in `accounts` would mean moving it later. `accounts` is for identity only. |
| Protected pages | `LoginRequiredMixin` plus `LOGIN_URL = "accounts:login"` | The standard pattern. It adds `?next=` automatically (AC-15), and later steps will use it too. |
| Form styling | Tailwind `@apply` rules in a `<style type="text/tailwindcss">` block in `base.html`, targeting the form wrapper | Keeps CSS classes out of Python form code without adding `django-widget-tweaks` (not allowed). The Tailwind v4 browser build supports `@apply` in the page. |
| View style | Class-based views everywhere in both apps (the root redirect is a `RedirectView` subclass) | CLAUDE.md: one view style per app. |

## Data model & migrations

**`accounts.User(AbstractUser)`** has no new fields. Its `Meta.constraints` are:
- `UniqueConstraint(Lower("username"), name="accounts_user_username_ci_unique",
  violation_error_message="A user with that username already exists.")`
- `UniqueConstraint(Lower("email"), condition=~Q(email=""),
  name="accounts_user_email_ci_unique",
  violation_error_message="A user with that email already exists.")`. The
  condition excludes blank emails because `createsuperuser` allows a blank
  email. Registration always requires one.

**`accounts.UserManager(django.contrib.auth.models.UserManager)`** overrides
only `get_by_natural_key(username)` →
`self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})`.

**Migrations:**
- `accounts/migrations/0001_initial.py`, generated by `makemigrations accounts`
  **after** `AUTH_USER_MODEL` is set and **before** any `migrate`.
- `core` has no models, so no migrations.
- The first `migrate` also applies the built-in `admin`, `auth`,
  `contenttypes` and `sessions` migrations to `db.sqlite3`.
- Recovery: if `migrate` accidentally runs before the custom user model
  exists, delete `db.sqlite3` and start again. There is no data at risk yet.

## URLs, views, templates

| URL name | Path | View | Template | Access rule |
|---|---|---|---|---|
| `core:home` | `/` | `HomeRedirectView(RedirectView)` | — | Anyone: logged in → `core:dashboard`, anonymous → `accounts:login` (AC-19) |
| `core:dashboard` | `/dashboard/` | `DashboardView(LoginRequiredMixin, TemplateView)` | `core/dashboard.html` | Logged-in users only; anonymous → login with `?next=` (AC-14/15) |
| `accounts:register` | `/accounts/register/` | `RegisterView(FormView)` | `accounts/register.html` | Anonymous only; logged in → dashboard (AC-18) |
| `accounts:login` | `/accounts/login/` | `LoginView.as_view(template_name="accounts/login.html", redirect_authenticated_user=True)` | `accounts/login.html` | Anonymous only; logged in → dashboard (AC-18) |
| `accounts:logout` | `/accounts/logout/` | `LogoutWithMessageView(LogoutView)` | — | POST only; GET → 405 (AC-13) |
| `admin:*` | `/admin/` | Django admin | — | Staff only. Used to deactivate accounts (AC-11). |

**Settings:**
- `LOGIN_URL = "accounts:login"`
- `LOGIN_REDIRECT_URL = "core:dashboard"`
- `LOGOUT_REDIRECT_URL = "accounts:login"`
- `AUTH_USER_MODEL = "accounts.User"`

**Templates** (base under `templates/`, app templates under
`<app>/templates/<app>/`):
- `templates/base.html`:
  - The Tailwind v4 browser CDN script
    (`https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4`).
  - A `text/tailwindcss` style block with the form `@apply` rules.
  - The nav:
    - Logged in: the username, a `Dashboard` link, and `Log out` as a
      `<form method="post">` containing `{% csrf_token %}` and a button
      (AC-21).
    - Anonymous: `Log in` and `Register` links (AC-20).
  - The messages list, and `{% block content %}`.
- `templates/partials/form_field.html`: label, widget, help text and that
  field's errors. Included in a loop, so every form renders errors next to
  the field (AC-3/4/5/6).
- `accounts/templates/accounts/register.html`: the form, `{% csrf_token %}`,
  and non-field errors.
- `accounts/templates/accounts/login.html`: the form, `{% csrf_token %}`, a
  hidden `next` input (`{{ next }}`, needed for AC-16), non-field errors, and
  a "Register" link (AC-8).
- `core/templates/core/dashboard.html`: "Welcome, {{ user.username }}" (AC-14).

**Messages:**
- After registration: `messages.success` → "Welcome, <username>! Your account
  has been created." (AC-2)
- After logout: `messages.info` → "You have been logged out." (AC-12). The
  order inside `LogoutWithMessageView.post()` is:
  1. `response = super().post(request, ...)`. This calls `logout()`: the old
     session is flushed and replaced with a new, empty one, and `request.user`
     becomes anonymous. It also builds the redirect to `LOGOUT_REDIRECT_URL`.
  2. `messages.info(request, "You have been logged out.")`. The message is
     queued on this request *after* the flush, so it can't be lost by the
     flush.
  3. `return response`. On the way out, `MessageMiddleware` saves the queued
     message using the default storage, which tries the cookie first and then
     the new session. The login page shows it after the redirect.

  Never add the message before calling `super().post()`.

**Forms (`accounts/forms.py`):**
- `RegistrationForm(UserCreationForm)`, with `Meta.model = User` and
  `fields = ("username", "email")`. Email is required.
  - `clean_username` rejects a username matching an existing one under
    `iexact` (AC-3).
  - `clean_email` strips spaces and rejects an email matching an existing one
    under `iexact` (AC-4).
  - Passwords are checked by `AUTH_PASSWORD_VALIDATORS`, using the four
    defaults `startproject` creates. `UserAttributeSimilarityValidator`
    compares the password against the username and email (AC-6).
- Login uses Django's `AuthenticationForm` unchanged.

**Registration flow:**
1. GET shows the empty form.
2. POST with a valid form → `form.save()` → `login(request, user)` → success
   message → redirect to `core:dashboard` (AC-2).
3. POST with an invalid form → the form is shown again with errors. Username
   and email are kept and the password fields are blank (AC-5/6/7).
4. `RegisterView` deliberately **does not** read `next`, so there's no second
   path for redirect handling.

## Implementation steps
- [x] 0. **Prerequisite (D-1, done by the user):** install Python 3.12, e.g.
  `winget install Python.Python.3.12` or the python.org installer.
  `/build` first runs `py -3.12 --version`. If it fails, `/build` **stops**
  and reports. It must not fall back to 3.13 or 3.11.
- [x] 1. **Environment.** Run `py -3.12 -m venv .venv`, then
  `.venv/Scripts/python.exe -m pip install --upgrade pip`. Confirm with
  `.venv/Scripts/python.exe --version`, which must print 3.12.x.
- [x] 2. Create `requirements.txt` with one line, `Django~=5.2.0` (D-2). Then
  run `.venv/Scripts/python.exe -m pip install -r requirements.txt` and
  confirm with `.venv/Scripts/python.exe -m django --version`, which must
  print 5.2.x.
- [x] 3. Create `.gitignore` covering `.venv/`, `db.sqlite3`, `__pycache__/`,
  `*.pyc` and `.env`.
- [x] 4. Run `.venv/Scripts/python.exe -m django startproject config .`. This
  creates `manage.py` and `config/{__init__,settings,urls,asgi,wsgi}.py`.
- [x] 5. Run `.venv/Scripts/python.exe manage.py startapp accounts` and
  `... startapp core`. Delete the generated `accounts/tests.py` and
  `core/tests.py`; `test-author` creates `tests/` packages instead.
- [x] 6. Edit `config/settings.py`:
  - `SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")`
  - `DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"`
  - `ALLOWED_HOSTS` from `DJANGO_ALLOWED_HOSTS`, defaulting to
    `localhost,127.0.0.1`
  - Add `accounts` and `core` to `INSTALLED_APPS`
  - `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]`
  - `AUTH_USER_MODEL`, `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`
- [x] 7. `accounts/models.py`: `UserManager` and `User`, with the
  constraints above. `accounts/admin.py`: `admin.site.register(User, UserAdmin)`.
- [x] 8. Run `.venv/Scripts/python.exe manage.py makemigrations accounts`.
  Confirm it creates `0001_initial.py` with both constraints. Then run
  `manage.py migrate`. **No `migrate` may run before this point.**
- [x] 9. Create `accounts/forms.py` with `RegistrationForm`.
- [x] 10. Create `accounts/views.py` with `RegisterView` and
  `LogoutWithMessageView`. Create `accounts/urls.py` with
  `app_name = "accounts"` and register, login and logout.
- [x] 11. Create `core/views.py` with `HomeRedirectView` and `DashboardView`.
  Create `core/urls.py` with `app_name = "core"` and home and dashboard.
- [x] 12. Edit `config/urls.py`: `admin/`, `accounts/` → `accounts.urls`,
  `""` → `core.urls`.
- [x] 13. Create the templates: `templates/base.html`,
  `templates/partials/form_field.html`, `accounts/templates/accounts/{register,login}.html`
  and `core/templates/core/dashboard.html`.
- [x] 14. Run `manage.py check` and `manage.py makemigrations --check --dry-run`.
  Both must be clean.
- [x] 15. Hand off to `test-author`, then `test-runner`, following `/build`.

## Test plan

Test modules:
- `accounts/tests/test_models.py`: constraints, manager, password hashing
- `accounts/tests/test_forms.py`: `RegistrationForm` validation
- `accounts/tests/test_views.py`: the register, login and logout flows
- `core/tests/test_views.py`: dashboard, root redirect, nav

| AC | Test module | What it asserts |
|---|---|---|
| AC-1 | accounts/test_views | Anonymous GET register → 200; form has username, email, password1 and password2 fields |
| AC-2 | accounts/test_views | A valid POST creates exactly 1 user, redirects to `core:dashboard`, the session is logged in as that user, and the success message is shown |
| AC-3 | accounts/test_forms, accounts/test_models | With "Alice" existing, "alice" and "ALICE" are rejected with an error on the `username` field and no user is created. The database constraint also rejects a direct create (`IntegrityError`) |
| AC-4 | accounts/test_forms, accounts/test_models | With `a@x.com` existing, `A@X.com` is rejected on the `email` field. The database constraint rejects a direct duplicate. Two users with a blank email are still allowed |
| AC-5 | accounts/test_forms | Missing username, missing email, an invalid email and mismatched passwords each give an error on the right field, and no user is created |
| AC-6 | accounts/test_forms | A short, common, all-numeric, or username-like password each fails on `password2` with a reason |
| AC-7 | accounts/test_views | After a failed POST, the response holds the typed username and email, and the password inputs have no value |
| AC-8 | accounts/test_views | Anonymous GET login → 200; username and password fields; a link to `accounts:register` |
| AC-9 | accounts/test_views, accounts/test_models | A user registered as "Alice" logs in with "alice", "ALICE" or "Alice" → redirect to dashboard. The wrong-case password "PASSWORD" fails. `username` stays "Alice" after login. `get_by_natural_key("aLiCe")` returns that user |
| AC-10 | accounts/test_views | A wrong password and an unknown username give the **same** non-field error text, the user is not logged in, and the typed username is kept |
| AC-11 | accounts/test_views | `is_active=False` with the correct password → not logged in, and the login page is shown again |
| AC-12 | accounts/test_views | POST logout → redirect to login, session logged out, and the "logged out" message appears on the login page when following the redirect (`follow=True`) |
| AC-13 | accounts/test_views | GET logout → 405, and the user is still logged in (dashboard still 200) |
| AC-14 | core/test_views | A logged-in user (registered "Alice", logged in as "alice") sees "Alice" on the dashboard |
| AC-15 | core/test_views | Anonymous GET dashboard → 302 to `accounts:login` with `?next=/dashboard/` |
| AC-16 | accounts/test_views | POST login with `next=/dashboard/` (and the page HTML contains the hidden `next` input) → redirect to that page |
| AC-17 | accounts/test_views | POST login with `next=https://evil.example.com/` → redirect to `core:dashboard`, not the external URL |
| AC-18 | accounts/test_views | A logged-in GET of login or register → redirect to `core:dashboard` |
| AC-19 | core/test_views | `/` anonymous → login page; `/` logged in → dashboard |
| AC-20 | core/test_views | Anonymous login and register pages contain "Log in" and "Register" links and not "Log out" or "Dashboard" |
| AC-21 | core/test_views | The logged-in dashboard contains the username (original casing), "Dashboard" and a logout **form** (POST), and no "Log in" or "Register" links |
| AC-22 | accounts/test_models | The stored `password` ≠ the raw password, `check_password(raw)` is True, and the raw password appears in no response |
| AC-23 | accounts/test_views | Using `Client(enforce_csrf_checks=True)`: register, login and logout POSTs without a token → 403 with no side effects (no user created, not logged in, still logged in) |

**Test data note (D-3):** case-insensitivity tests (AC-3, AC-4, AC-9, AC-14)
use ASCII names such as "Alice" and "alice". Tests must **not** assert that
non-ASCII letters with different case (e.g. "Ä" and "ä") count as the same,
because SQLite won't match them (a known, accepted limitation). Unicode
usernames themselves are valid. One test in AC-1/AC-2's group registers a
Unicode username (e.g. "José") and confirms it succeeds.

**Verification checklist** (`/build` runs these through `test-runner`, in this
order):
- [x] Focused: `manage.py test accounts core` — all pass, every AC-1…AC-23 is
  tagged in at least one test docstring
- [x] Drift: `manage.py makemigrations --check --dry-run` → "No changes detected"
- [x] Checks: `manage.py check` → "System check identified no issues"
- [x] Full suite: `manage.py test` — all pass
- [ ] Manual smoke test, optional and done by you: `runserver`, register "Alice",
  log out, log in as "alice", see "Welcome, Alice", log out

## Risks

| Risk | Mitigation |
|---|---|
| `migrate` runs before `AUTH_USER_MODEL` is set, which locks in `auth.User` | Step order (6 → 8). Recovery: delete `db.sqlite3`; there is no data yet. |
| **SQLite's `LOWER()` and `LIKE` only fold ASCII letters to the same case.** Usernames keep Django's default Unicode validator, so on SQLite "Ä" and "ä" count as **different** for the uniqueness and login rules. On PostgreSQL they count as the same. | **Accepted for local development (D-3).** Recorded in CLAUDE.md → Stack constraints → SQLite. ASCII letters (all the spec's examples) behave correctly on both databases. When the PostgreSQL DevOps step lands, the database applies full Unicode case-folding automatically, with no code change. Tests avoid asserting the non-ASCII case. |
| Duplicate registrations submitted at the same moment | The database constraint is the backstop. The form check gives the friendly error. |
| Open redirect through `next` | Only Django's `LoginView` handles `next`, and it validates with `url_has_allowed_host_and_scheme`. `RegisterView` ignores `next`. AC-17's test covers it. |
| Revealing which accounts exist | Login shows one generic error (AC-10), and the standard backend runs the password hasher even for unknown usernames. Registration necessarily reveals that a username or email is taken. Accepted; rate limiting is out of scope per the spec. |
| `DEBUG` defaults to on, and the fallback `SECRET_KEY` is insecure | Local only and clearly labelled `django-insecure-dev-only`. A later DevOps step makes the environment settings mandatory. |
| A third-party script from the Tailwind CDN | Already accepted in CLAUDE.md. Revisit in a DevOps step. |
| The logout message is lost when the session is flushed | The message is added **after** `logout()` has flushed the session (see Messages), so the flush can't remove it. AC-12's test proves it arrives. |
| Python 3.12 isn't installed on the dev machine | Step 0 is a hard prerequisite. `/build` stops instead of using another interpreter. |

## Decisions needing approval

All three were answered by the user on 2026-10-01.

- **D-1: Python 3.12 is not installed** (the machine has 3.11 and 3.13).
  - *Answer:* **(a)** Keep Python 3.12 as the locked interpreter. The user
    installs 3.12 before the venv is created (step 0). No fallback to another
    version.
- **D-2: Django 5.1 is end-of-life** (security support ended December 2025).
  - *Answer:* **(b)** Use Django 5.2 LTS (`Django~=5.2.0`, security support
    until April 2028). CLAUDE.md and the subagent prompts were updated to
    5.2 as part of this revision.
- **D-3: Restrict usernames to ASCII?**
  - *Answer:* **(b)** No. An ASCII-only rule would be user-visible behaviour
    that the approved spec doesn't contain. Usernames stay Unicode, and the
    SQLite limitation (only ASCII letters ignore case) is accepted for local
    development and recorded in CLAUDE.md and under Risks.

## Files changed
Application and config (by `/build`):
- created `requirements.txt`: `Django~=5.2.0` (installed 5.2.17)
- created `.gitignore`
- created `manage.py`, `config/__init__.py`, `config/asgi.py`, `config/wsgi.py` (startproject, unchanged)
- created `config/settings.py`: env-based `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`, apps, template dirs, auth settings
- created `config/urls.py`: admin, `accounts/`, root → `core`
- created `accounts/__init__.py`, `accounts/apps.py`, `accounts/migrations/__init__.py` (startapp, unchanged)
- created `accounts/models.py`: `UserManager`, `User` with two case-insensitive unique constraints
- created `accounts/admin.py`: `User` registered with `UserAdmin`
- created `accounts/migrations/0001_initial.py`: `User` + both constraints
- created `accounts/forms.py`: `RegistrationForm`
- created `accounts/views.py`: `RegisterView`, `LogoutWithMessageView`
- created `accounts/urls.py`: `register`, `login`, `logout`
- created `accounts/templates/accounts/register.html`, `accounts/templates/accounts/login.html`
- created `core/__init__.py`, `core/apps.py`, `core/models.py`, `core/admin.py`, `core/migrations/__init__.py` (startapp, unchanged; no models)
- created `core/views.py`: `HomeRedirectView`, `DashboardView`
- created `core/urls.py`: `home`, `dashboard`
- created `core/templates/core/dashboard.html`
- created `templates/base.html`: Tailwind CDN, nav, messages
- created `templates/partials/form_field.html`
- deleted `accounts/tests.py`, `core/tests.py` (startapp stubs, replaced by `tests/` packages)
- local only, gitignored: `.venv/`, `db.sqlite3` (all migrations applied)

Tests (by `test-author`):
- created `accounts/tests/__init__.py`
- created `accounts/tests/test_models.py`: constraints, `get_by_natural_key`, hashing (AC-3/4/9/22)
- created `accounts/tests/test_forms.py`: `RegistrationForm` (AC-1–6, 22)
- created `accounts/tests/test_views.py`: register/login/logout/CSRF flows (AC-1–13, 15–18, 22, 23)
- created `core/tests/__init__.py`
- created `core/tests/test_views.py`: dashboard, root redirect, nav (AC-14, 15, 19–22)

Review fixes (`/build 01 retest`, 2026-10-01):
- modified `accounts/models.py`: `USERNAME_TAKEN_MESSAGE` / `EMAIL_TAKEN_MESSAGE` constants used by the constraints (Q-4); `get_by_natural_key` comment now points to S-1
- modified `accounts/forms.py`: uses the shared message constants (Q-4)
- modified `accounts/views.py`: `RegisterView.get_success_url()` → `resolve_url(settings.LOGIN_REDIRECT_URL)`; hard-coded `success_url` removed (Q-3)
- modified `core/views.py`: `HomeRedirectView` uses `settings.LOGIN_REDIRECT_URL` / `settings.LOGIN_URL` (Q-3)
- created `templates/partials/form_body.html`: non-field errors + field loop (Q-2)
- modified `accounts/templates/accounts/login.html`, `register.html`: include `form_body.html` (Q-2)
- no migration (constraint message text unchanged; drift clean); no test files changed

Review fix Q-11 (`/build 01 retest`, 2026-10-01):
- modified `templates/partials/form_body.html`: loops `form.visible_fields` through `form_field.html`; outputs `form.hidden_fields` without the wrapper, still showing their errors

## Test results
Run on 2026-10-01 by `test-runner`, then confirmed by an independent full run.
Python 3.12.10, Django 5.2.17.

| Check | Command | Result |
|---|---|---|
| Focused | `manage.py test accounts.tests.test_models accounts.tests.test_forms accounts.tests.test_views core.tests.test_views` | 66/66 OK |
| Drift | `manage.py makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | No issues (0 silenced) |
| Full suite | `manage.py test` | 66/66 OK |

- Every AC from AC-1 to AC-23 is cited in at least one test docstring.
- Test-author reported no application defects, so there were 0 fix rounds.
- Test-author made one deliberate change from the plan. The AC-16 test
  targets `/dashboard/?from=link`, so it proves `next` is followed rather
  than coincidentally matching the default redirect.
- Notes for review, not blockers:
  - AC-7, 8, 11, 13, 17, 20 and 21 are each covered by a single test.
  - The manual smoke test in the browser (`runserver`) is still for the user
    to do.
- Unresolved: none.

**Retest (2026-10-01, after the Q-2/Q-3/Q-4 fixes, run by `test-runner`):**
- Focused 66/66 OK, drift "No changes detected", check "no issues", full
  suite 66/66 OK.
- These were refactors only, with no behaviour change, so test-author wasn't
  re-run. The existing tests cover AC-2, 3, 4, 18 and 19, which the changes
  touched.

**Retest 2 (2026-10-01, after the Q-11 fix, run by `test-runner`):**
- Focused 66/66 OK, drift clean, check "no issues", full suite 66/66 OK.
- Template-only change. Login and register have no hidden fields, so the
  pages render the same, and test-author wasn't re-run.

## Review log

### 2026-10-01 — full review (security-reviewer + quality-reviewer)
Scope: the "Files changed" list (not a git repo). Result: **0 High,
2 Medium, 10 Low.**

**User decision (2026-10-01):**
- Fix Q-2, Q-3 and Q-4.
- Accept Q-1 and Q-5 to Q-10 as non-blocking.
- Defer S-1 to the PostgreSQL step and S-2 to the DevOps/production security
  step.

| ID | Sev | Location | Finding | Suggested fix | State |
|---|---|---|---|---|---|
| Q-1 | Medium | accounts/forms.py:22-28 | `clean_username` duplicates Django 5.2's built-in `UserCreationForm.clean_username`, which already rejects usernames differing only in case (`iexact`) with a field error. **Verified** at django/contrib/auth/forms.py:272. The plan asked for this explicit check, so it's plan-sanctioned but redundant. | Remove the override and rely on the parent method, with the AC-3 tests as the guard. Or keep it with a comment saying it's a deliberate guard. | accepted |
| Q-2 | Medium | accounts/templates/accounts/login.html:6-20, register.html:6-19 | The card wrapper, the non-field-error block, the field loop and the submit button are duplicated, and every future form would copy them. | Add a `templates/partials/form_errors.html` (or `form_body.html`) include. | fixed (retest 2026-10-01) |
| S-1 | Low | accounts/models.py:12 vs :23-27 | Login matches with `__iexact`, which uses `UPPER()` on PostgreSQL, but the constraint uses `LOWER()`. After the PostgreSQL move, names like "admın" (dotless ı) and "admin" could both exist (via the admin or createsuperuser), and logging in as "admin" would then hit `MultipleObjectsReturned`, a 500. Can't happen on SQLite, and nobody gets into another account. | Make login match the constraint (filter on `Lower(username) == value.lower()`), or treat `MultipleObjectsReturned` as "user not found". Do it before or during the PostgreSQL step. | deferred → PostgreSQL step (documented in accounts/models.py comment) |
| S-2 | Low | config/settings.py:25-38 | There are no env-driven HTTPS or cookie settings (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS). `check --deploy` gives W004, W008, W012 and W016 even with `DEBUG` off. Related: with `DJANGO_DEBUG=0` and no `DJANGO_SECRET_KEY`, the app quietly uses the publicly known fallback key. | In the DevOps step, tie these settings to `not DEBUG` or to env vars, and refuse to start when `DEBUG` is off with the fallback key. | deferred → DevOps/production security step |
| Q-3 | Low | accounts/views.py:21,25; core/views.py:11-12 | The redirect target comes from two places: `settings.LOGIN_REDIRECT_URL` in one spot and hard-coded `'core:dashboard'` / `'accounts:login'` in others. | Use one source throughout (`resolve_url(settings.LOGIN_REDIRECT_URL)` / `settings.LOGIN_URL`). | fixed (retest 2026-10-01) |
| Q-4 | Low | accounts/forms.py:26,34 vs models.py:26,33 | The duplicate-username and duplicate-email messages are copied into both the form and the model. | Define them once as constants in `models.py` and import them in the form. | fixed (retest 2026-10-01) |
| Q-5 | Low | accounts/forms.py:31 | `.strip()` in `clean_email` does nothing, because form fields already strip whitespace. | Remove it, or add a comment. | accepted |
| Q-6 | Low | accounts/tests/test_views.py:23-24 | The helper `message_texts()` is never used. | Delete it (test-author). | accepted |
| Q-7 | Low | accounts/tests/test_views.py:216 | The response is assigned but never asserted, inconsistent with line 214. | Assert the status code or drop the assignment (test-author). | accepted |
| Q-8 | Low | login.html:21; register.html:20 | Wording differs from the plan: the login page's register link says "Create an account", and the register page has an extra "Log in" link. Both are harmless and AC-8 is still met. | Accept as built, or change the text to "Register". | accepted |
| Q-9 | Low | accounts/tests/test_models.py:93-96 | `test_stored_username_keeps_original_casing` is tagged AC-9 but never logs in. Real coverage is at test_views.py:205-209. | Retag it as a storage sanity check, or remove it (test-author). | accepted |
| Q-10 | Low | core/models.py, core/admin.py | Unchanged startapp stubs. | Leave them until `core` gets models. | accepted |

### 2026-10-01 — recheck (security-reviewer + quality-reviewer)
Scope: the files changed by the review-fix retest (see "Files changed →
Review fixes"). Result: **0 High, 0 Medium, 1 Low (new).**

Earlier findings:
- **Q-2: resolved.** The error block and field loop live only in
  `partials/form_body.html`. The card and button stay per page, as agreed.
- **Q-3: resolved.** The redirect route names appear only in
  `config/settings.py`, and every view resolves the settings.
- **Q-4: resolved.** The constants are used by the constraints and the form.
  The only other copies of the text are the frozen literals in
  `0001_initial.py`, which is normal.
- **S-1 / S-2:** no worse than before. The S-1 comment in
  `accounts/models.py` is accurate.

The security recheck found no regressions. Specifically:
- Neither new redirect reads anything from the request.
- `RegisterView` still ignores `next`.
- Auto-escaping is intact in the new partial, with no `|safe`.
- CSRF tokens and the hidden `next` input are still present.

The quality recheck re-ran the checks: `check` clean, drift clean, 66/66 tests
pass.

| ID | Sev | Location | Finding | Suggested fix | State |
|---|---|---|---|---|---|
| Q-11 | Low | templates/partials/form_body.html:10-12 | The shared partial loops over every field, including hidden ones, so a future form with a hidden field would get a stray label and wrapper. Login and register have no hidden fields, so nothing is affected today. | Loop over `form.visible_fields` with `form_field.html`, then output `form.hidden_fields` bare. | fixed (retest 2, 2026-10-01) |

### 2026-10-01 — recheck 2 (security-reviewer + quality-reviewer)
Scope: `templates/partials/form_body.html` (the Q-11 fix). Result: **0 High,
0 Medium, 1 Low (new).**

- **Q-11: resolved.** Only visible fields get the wrapper. Hidden fields are
  output without it, and their errors are still shown. Both pages include the
  partial unchanged.
- **Security:** no findings.
  - Auto-escaping is intact throughout the partials and pages.
  - There is exactly one CSRF token per form.
  - The hidden `next` input in login.html is unaffected, and the new loop
    can't add a second `next`.
  - The change is display-only.

| ID | Sev | Location | Finding | Suggested fix | State |
|---|---|---|---|---|---|
| Q-12 | Low | templates/partials/form_body.html:17-21 | Errors on hidden fields show only the bare message, without the field's name. Django's own rendering adds "(Hidden field X)" and puts them at the top of the form. Nothing is affected today, because no current form has hidden fields. Optional polish. | Prefix the message with `({{ field.name }})`, or merge these errors into the top-of-form error list. Fine to accept. | accepted (/done, 2026-10-01) |

Security reviewer confirmed sound:
- `LoginRequiredMixin` on the dashboard.
- POST-only logout with CSRF on every form, and no `csrf_exempt`.
- `next` is only read by `LoginView`.
- No raw SQL, no `|safe` or `mark_safe`.
- The form exposes only `username` and `email`.
- The session ID is rotated on login, and the session is flushed on logout before the message is added.
- The admin works with the custom user model and its constraints.
