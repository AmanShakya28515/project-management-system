---
step: 07
slug: task-status
spec: .claude/specs/07-task-status.md
status: done
created: 2026-10-07
approved: 2026-10-07
---

# Plan 07 — Task status

Token-efficient workflow. This mirrors step 06's assignment flow; the access
chain, no-replay, CSRF and design-system rules are reused as documented in
CLAUDE.md.

## Approach

| Concern | Decision | Why |
|---|---|---|
| Data | `Task.Status(models.TextChoices)`: `TODO='todo'` "To do", `IN_PROGRESS='in_progress'` "In progress", `DONE='done'` "Done". `Task.status = CharField(max_length=20, choices=Status.choices, default=Status.TODO)`. | Exactly three values, with stable stored keys and display labels in one place. The default makes new **and existing** tasks To do (OQ-1, AC-1). |
| Database integrity | `CheckConstraint(condition=Q(status__in=Status.values), name='tasks_task_status_valid')` (D-1) | It works on any database and stops any future write path from storing an unknown status. |
| Form | `TaskStatusForm(ModelForm)` with `fields = ('status',)` and the label "Status". There's a default and the field isn't blank, so Django renders exactly the three options with no empty choice, and any other value fails as an invalid choice (AC-3, AC-6). | No custom validation is needed. |
| View | `TaskStatusView`, built **exactly like** `TaskAssignView`: `LoginRequiredNoReplayMixin, MemberProjectMixin, TaskPageMixin, SingleObjectMixin, FormView`, with `http_method_names = ['post']`. The previous status is captured before validation. If it's the same: no write and `messages.info("Status is already <label>.")` (AC-5). If it's different: `save(update_fields=['status'])` and `messages.success("Status changed to <label>.")` (AC-4, AC-7). Then redirect to `tasks:detail`. An invalid value shows the page again with a field error (AC-6). | The scope resolves first (wrong or missing → 404, AC-8), POST only (a GET gets 405, AC-10), anonymous POSTs aren't replayed (AC-9), CSRF comes from the form (AC-10). There's a separate view rather than a shared base class, so step 06's code isn't refactored. |
| URL | `tasks:status`, `…/tasks/<pk>/status/` | Next to `assign`. |
| Page context | `TaskPageMixin.get_context_data` also adds `status_form`, unless the view passes a bound one. | One place builds the task page. |
| Task page UI | A new **Status** `.card` (`aria-labelledby="status-heading"`). It shows the current status as a text badge, then a select through `form_body.html` and a `.btn-secondary` "Save status". The Status and Assignee cards sit side by side from `sm` up (`grid sm:grid-cols-2 gap-6`) and stack on mobile, after Description (OQ-3). | It reuses the card, form partial and button. The layout keeps both controls together. |
| Status badges | New `.badge-status-todo` (member tokens, slate), `.badge-status-progress` (info tokens) and `.badge-status-done` (success tokens), in `@layer components` in `base.html`. The text label is always shown. | They reuse existing token pairs, already checked for AA: member 9.45:1, info 7.09:1, success 7.29:1. No new colours. Colour is never the only signal (AC-2, AC-11). |
| Project page rows | Each task row gets the status badge before `chevron-right` (`shrink-0`, so the title still wraps). The order stays `in_creation_order()` (AC-2). | Text plus badge. |

## Data model & migrations
- `tasks/models.py`: `Task.Status`, `Task.status` and the check constraint.
- `tasks/migrations/0003_task_status.py`, from `makemigrations tasks`. It adds
  the field with default `'todo'`, so existing rows become To do, and then
  the constraint. No data migration is needed.

## Files
- **Modified:**
  - `tasks/models.py`, `tasks/forms.py` (`TaskStatusForm`);
  - `tasks/views.py` (`TaskStatusView`; `status_form` in `TaskPageMixin`);
  - `tasks/urls.py`;
  - `tasks/templates/tasks/task_detail.html`;
  - `projects/templates/projects/project_detail.html` (the row badge);
  - `templates/base.html` (three badge rules);
  - `design-system/project-management-system/MASTER.md` (a short note).
- **Created:**
  - `tasks/migrations/0003_task_status.py`;
  - `tasks/tests/test_status.py`.

## Implementation steps
- [x] 1. Model, constraint, migration, `migrate`.
- [x] 2. `TaskStatusForm`, `TaskStatusView`, `status_form` context and the `status` URL.
- [x] 3. UI: read MASTER, then the Status card, the side-by-side layout with Assignee, the row badges and the three badge rules. Reuse the existing components; no skill searches unless a design question comes up.
- [x] 4. Tests in `tasks/tests/test_status.py`. Update existing row-text assertions only where AC-2 deliberately adds the status (see the Test plan).
- [x] 5. Verify: focused (`tasks projects`), drift, `check`, then the full suite.
- [x] 6. Manual visual check (D-2).
- [x] 7. Record "Files changed" and "Test results", then set `built`.

## Test plan
Written directly in `/build`, in `tasks/tests/test_status.py`, reusing
`tasks/tests/data.py` (task T in Apollo/Roadmap; Alice owner, Bob member,
Carol and Dave outsiders).

| AC | Asserts |
|---|---|
| AC-1 | A new task, and T (created before the field existed in test terms), have `status == 'todo'`. The task page shows "To do". |
| AC-2 | The project page rows show each task's status label, in creation order. Tasks set to Done and In progress show those labels. |
| AC-3 | The select's options are exactly ["To do", "In progress", "Done"], with the current one selected. |
| AC-4 | Bob POSTs `in_progress` → 302 to the detail page, the status is updated, and a success message names "In progress". |
| AC-5 | Re-POSTing the current status → no write (the status is unchanged) and an info message. |
| AC-6 | POSTing `archived`, `''` or `TODO` → 200, a field error with `aria-invalid`, and the status unchanged. A direct ORM save of an invalid value fails the check constraint (`IntegrityError`). |
| AC-7 | After a change, the title, description and assignee are unchanged. |
| AC-8 | Non-members (Carol, Dave), the wrong workspace or project, or a missing task → 404, with nothing changed. |
| AC-9 | Anonymous POST → 302 to exactly the login URL, nothing changed. |
| AC-10 | No CSRF token → 403; a GET → 405; no change. |
| AC-11 | The select is labelled, the button is `.btn-secondary`, the badge's text equals the status label, and the badge rules are in `@layer components` and use only tokens. The layout comes from the manual check. |
| AC-12 | Full suite. **Expected deliberate updates:** `tasks/tests/test_views.py:284-285` and `:304` compare exact row text (e.g. `['Zeta', 'alpha', 'Mid']`). With the badge, a row reads "Zeta To do". These assertions are updated to check the title part (or title + status) with the same order requirement, and listed in "Files changed". No other change is expected. |

## Risks
- **An invalid status from a future write path:** the database check
  constraint (D-1), plus the form's choices.
- **Overwriting other fields:** `update_fields=['status']` (AC-7 test).
- **IDOR:** the same scoped chain as assignment (AC-8 tests).
- **Duplicate code** between the assign and status views: accepted for now;
  two small views are clearer than an early abstraction. A shared base can
  come if a third single-field update appears.

## Decisions needing approval
The user answered these on 2026-10-07.
- **D-1:** *Answer:* **(a) yes**, add the database check constraint limiting `status` to the three values.
- **D-2:** *Answer:* **(a) a short manual checklist for you**, the same as step 06.

## Files changed
By `/build`, 2026-10-07:
- **Modified:**
  - `tasks/models.py`: `Task.Status` (TextChoices), `Task.status` (default
    To do) and the `tasks_task_status_valid` check constraint.
  - `tasks/forms.py`: `TaskStatusForm`.
  - `tasks/views.py`: `TaskStatusView` (POST only, like `TaskAssignView`);
    `TaskPageMixin` adds `status_form`.
  - `tasks/urls.py`: `status` (`<pk>/status/`).
  - `tasks/templates/tasks/task_detail.html`: the Status card, beside the
    Assignee card in a `sm:grid-cols-2` grid. The Assignee form lost its
    `sm:max-w-sm`, since it now sits in a half-width card.
  - `projects/templates/projects/project_detail.html`: a status badge on
    each task row.
  - `templates/base.html`: `.badge-status-todo`, `-progress` and `-done`
    (existing tokens).
  - `design-system/project-management-system/MASTER.md`: the "Task status
    (step 07)" note.
- **Created:**
  - `tasks/migrations/0003_task_status.py` (applied; existing tasks become
    To do);
  - `tasks/templates/tasks/partials/status_badge.html` (one badge partial,
    used on both pages);
  - `tasks/tests/test_status.py` (12 tests, written directly from the spec).
- **Existing tests updated on purpose:**
  - `tasks/tests/test_views.py`: the creation-order test now expects rows to
    read "<title> To do" (spec 07, AC-2), with the order unchanged.
  - `tasks/tests/test_models.py`: `test_duplicate_titles_allowed` now
    asserts there's no **uniqueness** constraint instead of no constraints
    at all, because D-1 adds the status check.

**Deviations:**
- The constraint lists the three values as literals. The inner `Meta` class
  can't reference `Task.Status`, so `Status.values` couldn't be used; the
  behaviour is the same.
- The plan didn't name the badge partial. It was added so the badge markup
  isn't copied into two templates (review lesson Q-53).

## Test results
Run directly by `/build` on 2026-10-07:
- Focused: `tasks.tests.test_status`: 12/12 OK. The task and project tests
  passed after the two deliberate updates.
- Drift: no changes detected. `check`: no issues.
- Full suite: **403/403 OK** (391 existing + 12 new).
- Manual visual check (D-2): the browser tools weren't used. The user
  checked the Status and Assignee cards, the row badges and focus at 320px
  and 1280px, and reported "all pass" on 2026-10-07. Sizes weren't measured.

## Review log

### 2026-10-07: review (one concise pass, no sub-agents)

**Scope:** the "Files changed" list above.

**Checked, no issues:**
- **Access:** `TaskStatusView` resolves the scope through `MemberProjectMixin` and `TaskPageMixin.get_queryset()` before the form runs (wrong or missing scope → 404). It's POST only (a GET gets 405), anonymous POSTs aren't replayed, and CSRF is in the form.
- **Data:** the choices plus the database check constraint reject unknown values. `update_fields=["status"]` leaves the other fields alone, and the no-op uses the value captured before validation.
- **Page:** the two forms use distinct field IDs (`id_status`, `id_assignee`), so there are no label or error ID clashes.
- **Accessibility:** the badges always show text, and their token pairs are already AA (`core/tests/test_ui.py` checks them). Labels and errors come from `form_body.html`. Rows keep `in_creation_order()`.

| ID | Sev | file:line | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| Q-72 | Low | `tasks/models.py` (check constraint) and `tasks/templates/tasks/partials/status_badge.html` | The three stored values (`todo`, `in_progress`, `done`) are written out again in the constraint and the badge partial, in addition to `Task.Status`. If a status is added later, the constraint would reject it (a loud failure, so it's safe) and the badge would fall back to the To do style. | Accept. If statuses ever change, take the constraint list from one module-level constant, and pass a badge class from the model instead of comparing strings in the template. | accepted (user, 2026-10-07); noted in CLAUDE.md Known limitations |

**Result:** High 0 · Medium 0 · Low 1. No High findings are open, so the status is `reviewed`.
