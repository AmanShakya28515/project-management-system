---
step: 02
slug: workspace-membership
spec: .claude/specs/02-workspace-membership.md
status: done
created: 2026-10-05
approved: 2026-10-05
---

# Plan 02 — Workspaces and membership

## Starting state (checked 2026-10-05)
- Step 01 is `done`. The apps are `accounts` (the `User` model with
  case-insensitive unique constraints and `UserManager.get_by_natural_key`
  using `username__iexact`) and `core` (`HomeRedirectView`, and
  `DashboardView(LoginRequiredMixin, TemplateView)`). There are 66 tests.
- Both apps use only class-based views.
- The URL namespaces are `accounts:` at `/accounts/` and `core:` at `/`.
- `LOGIN_URL = 'accounts:login'` and `LOGIN_REDIRECT_URL = 'core:dashboard'`.
- Forms render through `templates/partials/form_body.html`.
- `base.html` shows messages in one neutral style.
- `core/templates/core/dashboard.html` only greets the user. No test checks
  its body text beyond "Welcome, <username>".

## Approach

A new **`workspaces`** app holds the models, forms, views and templates, under
the `workspaces:` namespace at `/workspaces/`. The `core` dashboard reads the
user's workspaces from it. All views are class-based, matching the other two
apps.

| Concern | Choice | Why not the obvious alternative |
|---|---|---|
| Where the code lives | A new `workspaces` app | `accounts` is identity only, and `core` is the signed-in home (CLAUDE.md). Projects will later belong to a workspace, so it gets its own app. |
| Who the owner is | A non-null `Workspace.owner` foreign key is the **only** record of ownership. `Membership` has no role field. | With a role field, "exactly one owner" (AC-27) would need extra checks to stop zero or two owners. A single non-null foreign key makes that state impossible. The labels "Owner" and "Member" come from comparing against `owner`. |
| The owner is also a member | `Workspace.objects.create_with_owner(name, owner)` creates the workspace **and** the owner's `Membership` in one `transaction.atomic()` block. Views never call `Workspace.objects.create` directly. | A workspace whose owner has no membership row would be invisible to its owner, because access is decided by membership. One atomic manager method means neither row can exist without the other (AC-2, AC-27). No feature in this step removes memberships, so the invariant holds afterwards. |
| Access control | `Workspace.objects.for_user(user)` returns only workspaces the user has a membership in. Every workspace view gets its object through it. | This is the CLAUDE.md convention: a forgotten check fails closed. A non-member and a missing ID both produce Django's normal 404 from the same query, so the two can't be told apart (AC-21). |
| Owner-only action | The add-member view first loads the workspace through `for_user` (a non-member gets 404). It then raises `PermissionDenied` (403) if `workspace.owner_id != request.user.pk`. | This order follows spec decision OQ-6: non-members never learn the workspace exists, and members get an honest refusal (AC-20). |
| No duplicate memberships | A database `UniqueConstraint(fields=['workspace', 'user'])`, **plus** a form check that gives a field error, **plus** `get_or_create` in `Workspace.add_member()` | The form check gives the friendly error (AC-15). The constraint is the real guarantee, as in step 01 (AC-26). `get_or_create` already handles an `IntegrityError` when two requests arrive at once by fetching the existing row again. The view therefore treats `created=False` as "already a member" and never returns a 500. |
| Finding the user to add | `User.objects.filter(username__iexact=..., is_active=True)`. Anything other than exactly one result counts as "not found". | Letter case is ignored, as at login (OQ-2). Inactive users can't be added (OQ-3). Treating more than one match as "not found" already covers deferred finding **S-1** for this lookup, so the PostgreSQL step won't find a 500 error here. |
| Anonymous GET vs. POST (AC-22, AC-23) | A small mixin, `LoginRequiredNoReplayMixin(LoginRequiredMixin)`, in `core/mixins.py`. For GET and HEAD it behaves exactly like `LoginRequiredMixin` (redirect to login with `?next=`). For any other method it redirects to `LOGIN_URL` **with no `next`**. `LoginView` then falls back to `LOGIN_REDIRECT_URL`, which is the dashboard. | Plain `LoginRequiredMixin` puts the POST URL into `next`. After login, the browser would then GET a POST-only URL (405) or a form page, which goes against AC-23. Leaving out `next` keeps `LoginView` as the only code that reads `next` (CLAUDE.md), and nothing is stored, so nothing can be replayed. It goes in `core` because projects and tasks will reuse it. |
| Ordering the member list | `Workspace.member_list()` returns memberships with the user loaded. It is ordered owner first, then by `Lower('user__username')`, using `Case/When` on `user_id = owner_id`. | Business rules belong on models, not templates (CLAUDE.md). It uses only ORM functions that work on any database, so it's ready for PostgreSQL. |
| Ordering the dashboard list | `for_user(user).order_by(Lower('name'), 'pk')` | The spec doesn't set an order. Alphabetical by name is predictable, and `pk` breaks ties because names can repeat (OQ-1). |
| Feedback | `messages.success` after creating a workspace and after adding a member. Field errors for an unknown user, an inactive user, a duplicate member or an empty username. | Uses the existing messages block and `form_body.html` with no new markup. AC-15's "clear message" appears next to the username field. |
| Page design | The **`ui-ux-pro-max`** skill is loaded before writing `workspace_form.html`, `workspace_detail.html` and the dashboard changes (CLAUDE.md → Frontend and UI work). Its guidance is applied only through Django templates, Tailwind CDN utility classes and `partials/form_body.html`, building on the existing card, slate and indigo look. | Writing the markup without guidance risks inconsistent spacing and accessibility gaps. The skill's React, shadcn and npm suggestions are ignored, because they break the stack constraints. |
| Admin | **Not** registered in the admin this step. | The spec says no admin tooling beyond the defaults. An admin "add workspace" form would also skip `create_with_owner` and break AC-27. |

## Data model & migrations

**`workspaces.Workspace`**
- `name`: `CharField(max_length=100)`, required.
  - No unique constraint (OQ-1, AC-5).
  - Trimming happens in the form: Django's `CharField` strips leading and
    trailing spaces by default, so a name of only spaces arrives empty and
    fails the required check (AC-3).
- `owner`: `ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name='owned_workspaces')`. Why `PROTECT`: see D-1.
- `members`: `ManyToManyField(settings.AUTH_USER_MODEL, through='Membership', related_name='workspaces')`
- `created_at`: `DateTimeField(auto_now_add=True)`
- `objects = WorkspaceManager.from_queryset(WorkspaceQuerySet)()`:
  - `WorkspaceQuerySet.for_user(user)` → `self.filter(memberships__user=user)`.
    It needs no `.distinct()` because the unique constraint allows at most
    one row per user. For an anonymous user it returns `self.none()`, a
    defensive guard even though views require login first.
  - `WorkspaceManager.create_with_owner(name, owner)`: inside
    `transaction.atomic()`, it creates the workspace, then
    `Membership.objects.create(workspace=ws, user=owner)`, and returns the
    workspace.
- Methods:
  - `is_owner(user)` → `user.pk == self.owner_id`
  - `add_member(user)` → `Membership.objects.get_or_create(workspace=self, user=user)`, returning `(membership, created)`
  - `member_list()` → as described under Approach
- `__str__` returns `name`.

**`workspaces.Membership`**
- `workspace`: `ForeignKey(Workspace, on_delete=CASCADE, related_name='memberships')`
- `user`: `ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='workspace_memberships')`
- `joined_at`: `DateTimeField(auto_now_add=True)`, stored but not displayed
  (OQ-5).
- `Meta.constraints`: `UniqueConstraint(fields=['workspace', 'user'], name='workspaces_membership_unique_user')`

**Migrations:**
- `workspaces/migrations/0001_initial.py`, from `makemigrations workspaces`.
  It depends on `accounts` through `AUTH_USER_MODEL`.
- No changes to the `accounts` or `core` models, so no other migrations.
- No raw SQL. Every query uses ORM functions that work on any database.

## URLs, views, templates

`config/urls.py` gains `path('workspaces/', include('workspaces.urls'))`.

| URL name | Path | View | Template | Access rule |
|---|---|---|---|---|
| `workspaces:create` | `/workspaces/new/` | `WorkspaceCreateView(LoginRequiredNoReplayMixin, CreateView)` with `form_class = WorkspaceForm` | `workspaces/workspace_form.html` | Logged in. Anonymous GET → login with `?next=` (AC-22). Anonymous POST → login without `next`, nothing created (AC-23). |
| `workspaces:detail` | `/workspaces/<int:pk>/` | `WorkspaceDetailView(LoginRequiredNoReplayMixin, DetailView)` with `get_queryset() = Workspace.objects.for_user(request.user)` | `workspaces/workspace_detail.html` | Members (owner included) → 200. Non-member or unknown ID → 404 (AC-21). Anonymous → login with `?next=` (AC-22). GET only (`http_method_names = ['get', 'head', 'options']`). |
| `workspaces:add_member` | `/workspaces/<int:pk>/members/add/` | `AddMemberView(LoginRequiredNoReplayMixin, WorkspaceMemberListMixin, SingleObjectMixin, FormView)` with `http_method_names = ['post']` | Shows `workspaces/workspace_detail.html` again on invalid input | POST only, so GET → 405 (AC-25). Non-member → 404. Member who isn't the owner → 403 (AC-20). Anonymous → login without `next` (AC-23). CSRF required (AC-24). |
| `core:dashboard` | `/dashboard/` (existing) | `DashboardView`, extended | `core/dashboard.html` (existing) | Unchanged |

**View details:**
- `WorkspaceCreateView.form_valid`:
  - `self.object = Workspace.objects.create_with_owner(form.cleaned_data['name'], request.user)`
  - Then `messages.success(f'Workspace "{name}" was created.')` and redirect
    to `workspaces:detail` (AC-2).
  - It doesn't call `form.save()`, so the owner and membership always come
    from the manager.
- `WorkspaceMemberListMixin.get_context_data` adds:
  - `members = self.object.member_list()`
  - `is_owner = self.object.is_owner(request.user)`
  - `add_member_form`, **only when** `is_owner` is true. This is a new form,
    unless the view passes the bound form with errors.

  Both the detail view and the add-member view use it, so the page looks the
  same when the add form has errors.
- `AddMemberView.get_queryset()` returns
  `Workspace.objects.for_user(self.request.user)`, **the same scoping as
  `WorkspaceDetailView`**. It never uses `Workspace.objects.all()` or
  `get_object_or_404(Workspace, pk=…)`. `SingleObjectMixin.get_object()`
  then filters that queryset by `pk`. A non-member and a workspace ID that
  doesn't exist therefore both raise the same `Http404`, **before** any
  owner check runs. So a non-member can never get a 403, which would reveal
  that the workspace exists.
- `AddMemberView.post`, in this order:
  1. `self.object = self.get_object()`, through the scoped `get_queryset()`
     above. A non-member or a missing ID gets 404, and nothing after this
     step runs.
  2. If the user isn't the owner (`not self.object.is_owner(request.user)`),
     `raise PermissionDenied` (403). Only members can reach this check.
  3. Build `AddMemberForm(data, workspace=self.object)`.
     - Valid → `self.object.add_member(form.user)`.
       - If `created`: `messages.success(f'{user.username} was added to the workspace.')`
         and redirect to `workspaces:detail` (Post/Redirect/Get).
       - If not `created` (two requests at once): add the "already a member"
         error to the field and show the page again.
     - Invalid → show `workspace_detail.html` again with the bound form and
       status 200.
- `DashboardView.get_context_data` adds
  `workspaces = Workspace.objects.for_user(user).order_by(Lower('name'), 'pk')`.
  The `core` app imports from `workspaces`. That direction is fine: `core`
  is the home page that brings the apps together.
- `core/mixins.py`: `LoginRequiredNoReplayMixin.handle_no_permission()`.
  - For an anonymous GET or HEAD, it calls `super()`.
  - Otherwise it returns `redirect(settings.LOGIN_URL)`, which can be
    resolved by name through `redirect` (this matches how
    `resolve_url(settings.…)` is used elsewhere).
  - A logged-in user who isn't allowed is never redirected: they get a 404
    or 403, as above.

**Forms (`workspaces/forms.py`):**
- `WorkspaceForm(ModelForm)` with `fields = ('name',)`.
  - Label: "Workspace name".
  - `CharField` strips spaces, so an all-space name fails as required (AC-3).
  - The model's `max_length=100` gives Django's "Ensure this value has at
    most 100 characters (it has N)." message on the field (AC-4).
- `AddMemberForm(forms.Form)` with `username = CharField(max_length=150)`,
  label "Username". It takes `workspace` as a keyword argument.
  `clean_username`:
  - It filters users by `username__iexact` and `is_active=True`, and fetches
    at most 2 rows.
  - If it doesn't find exactly 1, it raises `ValidationError('No user with that username was found.', code='not_found')` (AC-16).
  - If the user is already a member, it raises
    `ValidationError(f'{user.username} is already a member of this workspace.', code='already_member')`.
    This covers the owner's own name too, because the owner is a member
    (AC-15).
  - It sets `self.user` and returns the username as typed.
- The message strings are module-level constants in `workspaces/forms.py`,
  so the view's race-condition path reuses the exact same text.
- The username to add is filled in again from the bound form when the page
  is shown with errors (AC-16).

**Templates** (all three are designed with the `ui-ux-pro-max` skill, within
the stack limits; see Approach):
- Accessibility, as CLAUDE.md requires:
  - every input has a visible label from `form_field.html`;
  - buttons and links have a visible focus ring;
  - text has enough contrast;
  - each page has one `<h1>`, and sections use `<h2>`;
  - the member list is a real list, and the "Owner"/"Member" label is text,
    not only colour.
- The page content below is fixed by the spec. The skill decides only layout
  and styling.
- `workspaces/templates/workspaces/workspace_form.html`: built like
  `register.html`.
  - A card with a "Create a workspace" heading.
  - A `<form method="post" novalidate>` with `{% csrf_token %}` and
    `{% include "partials/form_body.html" %}`.
  - A "Create workspace" button and a "Cancel" link to the dashboard.
- `workspaces/templates/workspaces/workspace_detail.html`:
  - The workspace name as `<h1>{{ workspace.name }}</h1>`. Auto-escaping
    handles AC-8; no `|safe` is used anywhere.
  - The member list as a `<ul>`. Each `<li>` holds `{{ m.user.username }}`
    and a label: "Owner" when `m.user_id == workspace.owner_id`, otherwise
    "Member".
  - When `is_owner`, an "Add a member" card. Its form posts to
    `{% url 'workspaces:add_member' workspace.pk %}` with `{% csrf_token %}`
    and includes `form_body.html` with `form=add_member_form`.
- `core/templates/core/dashboard.html`:
  - Keeps the "Welcome, {{ user.username }}" greeting.
  - Adds a "Your workspaces" section. It is either a `<ul>` of links to each
    workspace (`{{ ws.name }}` → `workspaces:detail`) or the empty text
    "You don't belong to any workspaces yet." (AC-10).
  - Always shows a "Create workspace" link to `workspaces:create`.
  - The "later steps" sentence is removed.
- The nav in `base.html` is unchanged.

## Implementation steps
- [x] 1. `.venv/Scripts/python.exe manage.py startapp workspaces`.
  - Delete the generated `workspaces/tests.py`; `test-author` creates a
    `tests/` package.
  - Delete the generated `workspaces/admin.py` stub, or leave it empty (no
    registration).
  - Add `'workspaces'` to `INSTALLED_APPS` after `'core'`.
- [x] 2. `workspaces/models.py`: `WorkspaceQuerySet`, `WorkspaceManager`,
  `Workspace` and `Membership`, exactly as under Data model.
- [x] 3. `.venv/Scripts/python.exe manage.py makemigrations workspaces`.
  Check that `0001_initial.py` contains both models, the
  `workspaces_membership_unique_user` constraint and `on_delete=PROTECT` on
  `owner`. Then run `manage.py migrate`.
- [x] 4. `core/mixins.py`: `LoginRequiredNoReplayMixin`.
- [x] 5. `workspaces/forms.py`: `WorkspaceForm`, `AddMemberForm` and the
  message constants.
- [x] 6. `workspaces/views.py`: `WorkspaceMemberListMixin`,
  `WorkspaceCreateView`, `WorkspaceDetailView` and `AddMemberView`.
  `workspaces/urls.py`: `app_name = 'workspaces'` with `create`, `detail`
  and `add_member`.
- [x] 7. `config/urls.py`: add `path('workspaces/', include('workspaces.urls'))`
  **before** the `''` → `core.urls` entry.
- [x] 8. Templates:
  - Load the `ui-ux-pro-max` skill (`ui-ux-pro-max:ui-ux-pro-max`) first.
  - Create `workspace_form.html` and `workspace_detail.html`, and update
    `core/dashboard.html`, using its guidance within the stack limits: Django
    templates and Tailwind CDN classes only, with no new JS, icon packages or
    fonts.
  - If it suggests a new shared style, add it as an `@apply` rule in
    `base.html` and list it under Files changed.
- [x] 9. `core/views.py`: `DashboardView.get_context_data` adds `workspaces`.
- [x] 10. Run `manage.py check` and `manage.py makemigrations --check --dry-run`.
  Both must be clean.
- [x] 11. Hand off to `test-author` (with spec 02 and this plan), then to
  `test-runner`, following `/build`.

## Test plan

Test modules:
- `workspaces/tests/test_models.py`: `create_with_owner`, `for_user`,
  `add_member`, `member_list` and the constraints
- `workspaces/tests/test_forms.py`: `WorkspaceForm` and `AddMemberForm`
  validation
- `workspaces/tests/test_views.py`: create, detail and add-member flows,
  access rules and CSRF
- `core/tests/test_views.py` (extended): the dashboard's workspace list

Test data: users "Alice" (owner), "Bob" (member), "Carol" (signed in but not
a member) and "Dave" (inactive), all with ASCII names (see the step 01
SQLite limitation). They are built in `setUpTestData`, with workspaces created
through `create_with_owner`.

| AC | Test module | What it asserts |
|---|---|---|
| AC-1 | workspaces/test_views | A logged-in GET of `workspaces:create` → 200, uses `workspace_form.html`, and the form has a `name` field |
| AC-2 | workspaces/test_views, test_models | A POST of "Apollo" creates exactly 1 workspace with `owner` = Alice and exactly 1 membership (Alice). It redirects to that workspace's `detail` page, and following the redirect shows the success message. `create_with_owner` produces the owner's membership |
| AC-3 | workspaces/test_forms, test_views | `""` and `"   "` → error on `name`, and the workspace count doesn't change. `"  Apollo  "` is saved as `"Apollo"` |
| AC-4 | workspaces/test_forms, test_views | 101 characters → an error on `name` that mentions 100, no workspace is created, and the typed value is in the shown form. 100 characters is accepted |
| AC-5 | workspaces/test_views | Alice creates "Apollo" twice, and Bob creates "Apollo" too → 3 separate workspaces, each with its own owner |
| AC-6 | workspaces/test_views | The owner and a member each GET `detail` → 200. The page contains the workspace name and every member's username. A member registered as "Bob" is shown as "Bob" |
| AC-7 | workspaces/test_models, test_views | With owner "Zed" and members "carol", "Bob" and "alice": `member_list()` gives Zed, alice, Bob, carol. The page shows "Owner" once, next to Zed, and "Member" next to the others |
| AC-8 | workspaces/test_views, core/test_views | **Workspace name:** `<script>alert(1)</script>` → the page holds `&lt;script&gt;alert(1)&lt;/script&gt;` and not the raw tag, on both the detail page and the dashboard. **Username:** a member whose username is `<b>x</b>` → the member list on the detail page holds `&lt;b&gt;x&lt;/b&gt;` and not the raw `<b>x</b>`. The success message after adding them is escaped the same way. That username breaks Django's normal username rule (letters, digits and `@.+-_` only), so the test builds it on purpose with `User.objects.create_user(...)`, which skips form validation. This is test data only; the username product rules don't change |
| AC-9 | core/test_views | The dashboard lists links to the `detail` page of each of the user's workspaces, plus a link to `workspaces:create` |
| AC-10 | core/test_views | A user with no workspaces sees "You don't belong to any workspaces yet." and the create link |
| AC-11 | core/test_views, workspaces/test_models | Bob owns W1, is a member of W2, and isn't in W3 → the dashboard lists W1 and W2 but not W3. `for_user(bob)` gives exactly {W1, W2}. Each `detail` page → 200 for Bob |
| AC-12 | workspaces/test_views | The owner's `detail` page contains a form posting to `add_member` with a `username` field |
| AC-13 | workspaces/test_views | Alice POSTs "Bob" → a membership exists, it redirects to `detail`, the message names "Bob", and the list shows Bob as "Member" |
| AC-14 | workspaces/test_views, test_forms | Alice POSTs "BOB" → Bob (stored as "Bob") is added. The list shows "Bob" |
| AC-15 | workspaces/test_forms, test_views | Adding an existing member, or Alice's own name ("alice"), → a field error saying they are already a member, and the membership count doesn't change. `add_member()` called twice gives `created=False` the second time and still 1 row |
| AC-16 | workspaces/test_forms, test_views | An unknown "nobody" and the inactive "Dave" → the same "No user with that username was found." field error, nobody is added, and the typed username is in the shown form |
| AC-17 | workspaces/test_forms, test_views | An empty username → error on `username`, and the membership count doesn't change |
| AC-18 | workspaces/test_views, core/test_views | After Alice adds Bob, Bob's dashboard lists the workspace and Bob's `detail` GET → 200, showing him as "Member" |
| AC-19 | workspaces/test_views | Member Bob's `detail` page → 200, with the name and members, but **no** add-member form and no `add_member` URL |
| AC-20 | workspaces/test_views | Member Bob POSTs to `add_member` with "Carol" → 403, and Carol is not a member |
| AC-21 | workspaces/test_views | Non-member Carol: `detail` → 404, and the response doesn't contain the workspace name. An `add_member` POST → 404 (**not** 403) with no membership change. Missing IDs give the same 404: a GET of `detail` and an `add_member` POST, from both a non-member and the owner of another workspace |
| AC-22 | workspaces/test_views | Anonymous GET of `create` and `detail` → 302 to `login?next=<that path>`. Logging in with that `next` lands on the page: Alice → 200 on `detail`, Carol → 404. Nothing is created |
| AC-23 | workspaces/test_views | Anonymous POSTs to `create` and `add_member` → 302 to exactly `reverse('accounts:login')` with no `next`, and no workspace or membership is created. A login POST afterwards lands on `core:dashboard`, and the counts are still unchanged |
| AC-24 | workspaces/test_views | With `Client(enforce_csrf_checks=True)` and a logged-in user, `create` and `add_member` POSTs without a token → 403, with no workspace or membership created |
| AC-25 | workspaces/test_views | A GET of `add_member` with `?username=Bob` → 405 and Bob isn't added. A GET of `create` with `?name=X` → only shows the form, and no workspace is created |
| AC-26 | workspaces/test_models | Creating a duplicate `Membership` directly raises `IntegrityError`. `add_member()` on an existing member returns `created=False` and leaves 1 row. The view's `created=False` path (simulated by adding the member between the form check and the save, e.g. by patching `AddMemberForm.clean_username` to skip its check) gives the "already a member" error and not a 500 |
| AC-27 | workspaces/test_models | After `create_with_owner`, `owner` is set and the owner has a membership. `owner` can't be null (`IntegrityError`). If `Membership.objects.create` fails inside `create_with_owner` (patched), then no `Workspace` row remains either (atomicity) |

**Verification checklist** (`/build` runs these through `test-runner`, in this
order):
- [x] Focused: `.venv/Scripts/python.exe manage.py test workspaces core`. All
  pass, and every AC from AC-1 to AC-27 is tagged in at least one test
  docstring.
- [x] Drift: `.venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  → "No changes detected"
- [x] Checks: `.venv/Scripts/python.exe manage.py check` → "System check
  identified no issues"
- [x] Full suite: `.venv/Scripts/python.exe manage.py test`. All pass, including
  the 66 step 01 tests.
- [ ] Manual smoke test, optional and done by you:
  1. Run `runserver`, sign in as Alice and create "Apollo".
  2. Add "BOB".
  3. Log in as Bob: the dashboard lists Apollo, and there's no add form.
  4. Log in as Carol and open Apollo's URL: 404.

## Risks

| Risk | Mitigation |
|---|---|
| **A member gains access to a workspace they shouldn't see (IDOR)** by changing the ID in the URL | Every workspace lookup goes through `for_user()`. There's no `get_object_or_404(Workspace, pk=…)` anywhere. Tests check non-member access to both `detail` and `add_member` (AC-21). |
| A non-owner adds members by sending the POST themselves | `AddMemberView` checks the owner on the server after the membership lookup. Hiding the form isn't the protection. Covered by AC-20's test. |
| Duplicate memberships from two submissions at once | The database unique constraint, plus `get_or_create`, which handles the `IntegrityError` race. The view turns `created=False` into the normal field error (AC-26). |
| A workspace exists without its owner's membership | Only `create_with_owner` creates workspaces, inside `transaction.atomic()`. There's no admin registration and no feature to remove members. The database can't enforce "the owner is a member" across two tables without triggers, so it's covered by tests (AC-27) and listed for review. |
| Owner-only data leaks to a non-member through error pages | 404s use Django's standard not-found response, which contains no workspace data. DEBUG pages only exist locally (S-2 is already recorded). |
| An anonymous POST is replayed after login | `LoginRequiredNoReplayMixin` doesn't put the POST target into `next`, and no form data is stored. AC-23's test proves the counts don't change after login. |
| XSS through the workspace name or username | Template auto-escaping. No `|safe` or `mark_safe`. The success messages are plain strings, and `base.html` already outputs `{{ message }}` escaped. Covered by AC-8's test. |
| **S-1** (Unicode letter-case mismatch on PostgreSQL) affects the add-member lookup | The lookup treats anything other than exactly one result as "not found", so there's never a `MultipleObjectsReturned` 500. The login part of S-1 stays deferred, as recorded. |
| Revealing which usernames exist through add-member | Only owners can reach the form. Registration already reveals whether a username is taken (OQ-3). Accepted. |
| Deleting a user who owns a workspace | `on_delete=PROTECT` (D-1): the admin refuses with a "protected objects" page instead of silently deleting the workspace and all its members. Deleting a member user removes only their membership rows (`CASCADE`). |
| `core` importing `workspaces` creates a circular import | `workspaces` doesn't import from `core`, except `core/mixins.py`, which itself has no model imports. The import graph has no cycle. `manage.py check` and the test run would catch one. |
| The `ui-ux-pro-max` skill suggests things outside the stack (React, shadcn, npm, icon or font packages) | Its suggestions are applied only through templates and Tailwind CDN classes. Anything that would need a new dependency is left out and mentioned in the build report, not added. Reviewers check for new `<script>` or `<link>` tags. |
| Changing the dashboard breaks step 01 tests | Only "Welcome, <username>" and the template name are checked, and both stay. The full suite run confirms it. |

## Decisions needing approval

This was answered by the user on 2026-10-05.

- **D-1: What happens when someone tries to delete a user who owns a
  workspace?** The spec doesn't say: deactivation is out of scope, and there
  is no delete feature. But the foreign key needs an `on_delete` rule, and
  the admin can delete users.
  - *Answer:* **(a) `PROTECT`.** Deleting a user is refused while they own a
    workspace, so nothing is lost silently, and it is easy to relax later.
    The alternative, (b) `CASCADE`, which would delete their workspaces and
    everyone's memberships in them, was rejected.

  Deleting a *member* (not the owner) always removes just their memberships
  (`CASCADE`). It can't break any rule.

## Files changed
Application and config (by `/build`, 2026-10-05):
- created `workspaces/__init__.py`, `workspaces/apps.py`, `workspaces/migrations/__init__.py`, `workspaces/admin.py` (startapp, unchanged; `admin.py` registers nothing)
- deleted `workspaces/tests.py` (startapp stub; `test-author` creates a `tests/` package)
- modified `config/settings.py`: `'workspaces'` added to `INSTALLED_APPS`
- created `workspaces/models.py`: `WorkspaceQuerySet.for_user`, `WorkspaceManager.create_with_owner`, `Workspace` (`owner` PROTECT, `is_owner`, `add_member`, `member_list`), `Membership` + unique constraint
- created `workspaces/migrations/0001_initial.py`: both models, `workspaces_membership_unique_user`, `owner` PROTECT (applied)
- created `core/mixins.py`: `LoginRequiredNoReplayMixin`
- created `workspaces/forms.py`: `WorkspaceForm`, `AddMemberForm`, `USER_NOT_FOUND_MESSAGE`, `ALREADY_MEMBER_MESSAGE`
- modified `workspaces/views.py` (startapp stub replaced): `WorkspaceMemberListMixin`, `WorkspaceCreateView`, `WorkspaceDetailView`, `AddMemberView`
- created `workspaces/urls.py`: `create`, `detail`, `add_member`
- modified `config/urls.py`: `workspaces/` → `workspaces.urls`
- created `workspaces/templates/workspaces/workspace_form.html`
- created `workspaces/templates/workspaces/workspace_detail.html`
- modified `core/templates/core/dashboard.html`: greeting kept; "Create workspace" link, "Your workspaces" list, empty state
- modified `core/views.py`: `DashboardView.get_context_data` adds `workspaces`
- `base.html` not changed: no new shared style was needed

UI notes: the templates were designed after loading `ui-ux-pro-max`, using
its accessibility guidance:
- `focus-visible` rings on every button and link;
- an empty state with a message and an action;
- "Owner"/"Member" written as text badges that don't wrap, not colour alone;
- `<section>` regions labelled by their `<h2>`, and one `<h1>` per page;
- long names wrap with `break-words`.

No scripts, fonts or icon packages were added.

Review fixes (`/build 02 retest`, 2026-10-05: Q-1, Q-2, Q-4, Q-5, Q-6):
- modified `templates/base.html`: `.btn-primary` and `.btn-secondary` `@apply` rules, with focus-visible rings (Q-1)
- modified `workspaces/templates/workspaces/workspace_form.html`, `workspace_detail.html`, `core/templates/core/dashboard.html`: use `.btn-primary`/`.btn-secondary` instead of copied class strings (Q-1)
- modified `workspaces/models.py`: the `member_list()` annotation was renamed `is_workspace_owner`, and the docstring says the template uses it (Q-4)
- modified `workspaces/templates/workspaces/workspace_detail.html`:
  - the row label uses `membership.is_workspace_owner`;
  - the owner-only section uses `viewer_is_owner` (Q-4)
- modified `workspaces/views.py`:
  - `WorkspaceMemberListMixin` was renamed `WorkspacePageMixin`, and now also owns the single members-only `get_queryset()`; both copies were removed (Q-5);
  - the context flag was renamed `viewer_is_owner` (Q-4)
- modified `core/mixins.py`: the no-`next` redirect now applies only to anonymous non-GET/HEAD requests when `raise_exception` is false. Every other case goes to `AccessMixin.handle_no_permission()` (Q-6)
- tests (by `test-author`):
  - Q-2:
    - created `core/tests/test_dashboard_workspaces.py`: the spec 02 dashboard tests, moved unchanged;
    - modified `core/tests/test_views.py`: back to spec 01 tests only;
    - modified `workspaces/tests/test_forms.py`, `test_models.py`, `test_views.py`: AC tags now read "spec 02 AC-n".
  - Q-6: created `core/tests/test_mixins.py`, 5 regression tests for `LoginRequiredNoReplayMixin`.
- product behaviour unchanged; no migration (the annotation isn't a model field)

## Test results
Run on 2026-10-05 by `test-runner`. Python 3.12.10, Django 5.2.17.

| Check | Command | Result |
|---|---|---|
| Focused | `manage.py test workspaces.tests.test_models workspaces.tests.test_forms workspaces.tests.test_views core.tests.test_views` | 77/77 OK |
| Drift | `manage.py makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | No issues (0 silenced) |
| Full suite | `manage.py test` | 135/135 OK |

- **Where the 135 tests come from:**
  - 66 step 01 tests, all unchanged and still passing.
  - 69 new step 02 tests: 15 model, 10 form and 39 view tests in
    `workspaces`, plus 5 dashboard tests added to `core`.
  - The focused run's 77 is the 69 new tests plus the 8 step 01 tests
    already in `core/tests/test_views.py`.
- Every AC from AC-1 to AC-27 is cited in at least one test docstring.
- `test-author` reported no application defects, so there were 0 fix rounds.
- `test-author`'s first run had 3 failures, all caused by its own tests.
  It fixed them before handing over:
  - one expected an escaped apostrophe that the template doesn't produce;
  - two read the success message after `assertRedirects` had already fetched
    the page, which used the message up.
- Nothing unresolved.

Retest after the review fixes (`/build 02 retest`, 2026-10-05, run by `test-runner`):

| Check | Command | Result |
|---|---|---|
| Focused | `manage.py test workspaces.tests.test_models workspaces.tests.test_forms workspaces.tests.test_views core.tests.test_views core.tests.test_dashboard_workspaces core.tests.test_mixins` | 82/82 OK |
| Drift | `manage.py makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | No issues (0 silenced) |
| Full suite | `manage.py test` | 140/140 OK |

- 140 = 66 step 01 tests plus 74 step 02 tests (the 69 from the first build
  plus 5 new mixin tests).
- Every AC from spec 02 AC-1 to AC-27 is still cited, now as "spec 02 AC-n".
- `core/tests/test_views.py` holds only spec 01 tests.
- 0 fix rounds; no application defects.

## Review log
### 2026-10-05: full review (security-reviewer + quality-reviewer)

Scope: the "Files changed" list above. This is not a git repo.

Both reviewers ran `check` and `makemigrations --check`, and both were clean.
Neither found any High finding.

The security reviewer found no access-control, CSRF, XSS, injection or
replay problems:
- every workspace lookup goes through `for_user()`;
- the 404 check runs before the 403 owner check;
- there is no `|safe`;
- the unique constraint plus `get_or_create` prevents duplicate memberships;
- S-1 and S-2 are not made worse.

Security finding IDs continue after S-1 and S-2, which CLAUDE.md already uses.

| ID | Sev | file:line | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| Q-1 | Medium | `workspaces/templates/workspaces/workspace_form.html:13`, `workspace_detail.html:35`, `core/templates/core/dashboard.html:9` | The primary-button class string (with focus ring) is copied three times, and differs from `register.html`, which has no focus ring. The Frontend rules and plan step 8 said shared styles go in `base.html` as `@apply`. | Add `.btn-primary` and `.btn-secondary` `@apply` rules in `base.html` and use them in the three new templates. Restyling the step 01 pages is outside this plan (step 03 ui-refresh). | fixed |
| Q-2 | Medium | `core/tests/test_views.py:1`, `:128-227` | The spec 02 dashboard tests are in a module whose docstring says "spec 01", and their AC tags reuse spec 01 numbers with different meanings, so the tags are ambiguous. | Move them to `core/tests/test_dashboard_workspaces.py` with a spec 02 docstring, or prefix their tags with "spec 02". | fixed |
| S-3 | Low | `workspaces/views.py:79-81`, `workspaces/forms.py:35-49`, `core/templates/core/dashboard.html:18` | Owners can add any active user without that user agreeing, and the user can't leave. A misleading workspace name then appears on their dashboard: spam or social engineering, not XSS. This is by design in spec 02. | No change now. A later spec could add invitations or "leave workspace". Record it as a known limitation in CLAUDE.md at `/done`. | accepted as a limitation of approved spec 02 behaviour (user, 2026-10-05) |
| S-4 | Low | `workspaces/models.py:85-89` | "The owner is always a member" (AC-27) is enforced only by the app never deleting memberships. Deleting the owner's membership row (from the shell, or a future remove-member feature) would lock the owner out of their own workspace. | Before any remove-member feature, add a model-level guard that refuses to remove the owner's membership. Already listed in Risks. | deferred until removing members or leaving a workspace exists (user, 2026-10-05) |
| Q-3 | Low | `core/tests/test_views.py:131` | A mid-file import with `# noqa: E402`, which does nothing because there's no linter. | Move it to the top, or let Q-2's new module fix it. | accepted (user, 2026-10-05) |
| Q-4 | Low | `workspaces/models.py:71`, `workspaces/views.py:20`, `workspace_detail.html:18,28` | `is_owner` means three different things: a model method, an annotation used only for sorting, and the context flag "the viewer is the owner". The template also works out row ownership a fourth way. | Rename the context flag to `viewer_is_owner`, and either use the annotation in the template or rename it `owner_first`. | fixed |
| Q-5 | Low | `workspaces/views.py:48-50`, `:63-66` | Two copies of the scoped `get_queryset()`, which is the key authorization rule. | Move it into one shared mixin. | fixed |
| Q-6 | Low | `core/mixins.py:15-18` | `handle_no_permission` always redirects for non-GET requests, skipping `AccessMixin`'s 403 branch (`raise_exception`, or a logged-in user). It's safe today but could trip future reuse. | Take the no-`next` path only when the user is anonymous and `raise_exception` is false; otherwise call `super()`. | fixed |
| Q-7 | Low | `workspaces/forms.py:7` | The comment says both message constants are shared with the view; only `ALREADY_MEMBER_MESSAGE` is. | Reword the comment. | accepted (user, 2026-10-05) |
| Q-8 | Low | `workspaces/forms.py:23` | `max_length=150` is hard-coded from `AbstractUser.username`. | Read it from the user model's `username` field. | accepted (user, 2026-10-05) |
| Q-9 | Low | `workspaces/tests/test_views.py:33-45` | `member_rows()` parses `<li>` text with a regex, which is brittle to markup changes. | Assert order and labels through `response.context['members']`, and keep one rendered-label check. | accepted (user, 2026-10-05) |
| Q-10 | Low | `core/templates/core/dashboard.html:22-25`; Files changed "UI notes" | The note claims the empty state includes an action, but the only action is the header button. AC-10 is still met. | Add a link inside the empty state, or correct the note. | accepted (user, 2026-10-05) |

**Result:** High 0 · Medium 2 · Low 10. There are no open High findings, so
the status is `reviewed`. Choose which findings to fix with
`/build 02 retest`, or accept them at `/done 02`.

### 2026-10-05: recheck after review fixes (security-reviewer + quality-reviewer)

Scope:
- Q-1, Q-2, Q-4, Q-5 and Q-6;
- the files listed under "Review fixes" in Files changed.

Both reviewers also ran the checks themselves: `check` and drift were clean,
and 140/140 tests passed.

**Security: no new findings.**
- Both views resolve `get_queryset` to `WorkspacePageMixin`'s `for_user`
  scoping (confirmed by printing their MRO).
- The 404 still comes before the 403.
- The owner-only form is gated by `viewer_is_owner`.
- Anonymous POST replay is still prevented.
- No new XSS or scripts.
- S-3 and S-4 are unchanged in risk.

**Quality:**
- Q-1, Q-2, Q-4, Q-5 and Q-6 are confirmed resolved, with file:line evidence.
- Q-3 is also resolved: the mid-file import went away with the Q-2 move.

| ID | Sev | file:line | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| Q-11 | Low | `templates/base.html:14-15`; extra classes used at `core/templates/core/dashboard.html:9`, `workspaces/templates/workspaces/workspace_form.html:13` | `.btn-*` rules in the `text/tailwindcss` block are unlayered, so they always beat utilities. A utility added next to them that sets the same property (e.g. `px-3`, `bg-red-600`) would be silently ignored. Today's `text-sm` and `flex-1` work only because the rules don't set those properties. The dashboard button is `text-sm` while the others are the default size. | Define the buttons with `@utility` or inside `@layer components` so utilities can override them, or allow only layout classes next to `.btn-*`. Decide on one button size. A natural fit for step 03 ui-refresh. | deferred to step 03 ui-refresh (user, 2026-10-05) |

**Result:** High 0 · Medium 0 · Low 1 (new). There are no open High
findings, so the status is `reviewed`.
