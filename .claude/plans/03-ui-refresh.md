---
step: 03
slug: ui-refresh
spec: .claude/specs/03-ui-refresh.md
status: done
created: 2026-10-05
approved: 2026-10-05
---

# Plan 03 — UI refresh

## Starting state (checked 2026-10-05)
- Step 02 is `done`, and there are 140 passing tests.
- **Templates:**
  - `templates/base.html`:
    - the Tailwind v4 browser CDN `<script>`;
    - one `text/tailwindcss` block with **unlayered** `.form-field`,
      `.field-errors`, `.btn-primary` and `.btn-secondary` rules (the cause
      of Q-11);
    - a `<nav>` holding the brand and the auth links, with hand-written
      button classes on "Register" and "Log out";
    - one neutral style for messages.
  - `templates/partials/form_body.html` and `form_field.html`.
  - `accounts/templates/accounts/login.html` and `register.html`, both with
    hand-written button classes.
  - `core/templates/core/dashboard.html`.
  - `workspaces/templates/workspaces/workspace_form.html` and
    `workspace_detail.html`.
- **An accessibility gap that already exists:**
  - Django 5.2 adds `aria-invalid="true"` and
    `aria-describedby="<id>_helptext <id>_error"` to inputs
    (`django/forms/boundfield.py:291-310`).
  - But `form_field.html` renders help text and errors **without those IDs**,
    so the references point at nothing.
  - This step fixes that (AC-11, AC-12).
- **Autofill hints (AC-13):**
  - Django's auth forms already set them for username (`username`), the
    login password (`current-password`) and the registration passwords
    (`new-password`).
  - The registration **email** field has none.
- `django.template.context_processors.request` is enabled, so templates can
  read `request.resolver_match` to mark the current page.
- **The skill's design-system output** (preview run on 2026-10-05, query "B2B
  project management SaaS productivity team workspace", with variance 3,
  motion 2 and density 5):
  - style: "Minimalism & Swiss Style";
  - an indigo primary (`#6366F1`), an emerald CTA accent, and Plus Jakarta
    Sans from Google Fonts;
  - a GSAP scroll reveal;
  - a marketing "Trust & Authority" landing pattern.

  Several of those conflict with spec 03 or with accessibility. The table
  under Approach shows how each is handled.
- **Contrast ratios** of the candidate colours, computed with the WCAG
  formula on these exact hex values:

| Pair | Ratio | Pair | Ratio |
|---|---|---|---|
| slate-900 on white | 17.85 | white on indigo-600 | 6.29 |
| slate-700 on white | 10.35 | white on indigo-500 (skill primary) | **4.47 ✗** |
| slate-600 on white | 7.58 | indigo-700 on white | 7.90 |
| slate-600 on slate-50 | 7.24 | indigo-800 on indigo-50 | 8.88 |
| slate-500 on white | 4.76 | indigo-500 (focus ring) on white | 4.47 |
| slate-400 on white | 2.56 | emerald-800 on emerald-50 | 7.29 |
| slate-300 on white | **1.48 ✗** (today's input border) | sky-800 on sky-50 | 7.09 |
| red-700 on white | 6.47 | amber-800 on amber-50 | 6.84 |
| red-800 on red-50 | 7.60 | slate-700 on slate-100 | 9.45 |

## Approach

There are two parts:
1. **Make the design system** with the skill's full workflow and save it.
2. **Rebuild the shared layer once**, then restyle each page on top of it.
   The shared layer is the design tokens, component classes, header and
   navigation, messages and the form partials.

Almost all of the change is in templates and one style block. The only
Python changes are widget *attributes* for autofill (no CSS classes, as
CLAUDE.md requires). No view, URL, model or message wording changes.

| Concern | Choice | Why not the obvious alternative |
|---|---|---|
| Design system | Generate it with `search.py "<query>" --design-system --persist -p "Project Management System" --output-dir <repo root> --variance 3 --motion 2 --density 5`, giving `design-system/project-management-system/MASTER.md`. Add page overrides with `--page auth`, `--page dashboard` and `--page workspace`. Then add a **"Project adjustments (step 03)"** section to `MASTER.md` that records each change made to the generated output and why (next row). | CLAUDE.md requires the persisted design system. Leaving the generated output as it is would conflict with spec 03 (fonts, palette, motion) and with WCAG. Recording the changes in the design system means later steps don't reopen them. |
| What changes from the skill's output | **Fonts:** Plus Jakarta Sans/Google Fonts → a **system font stack** (spec 03, AC-5). **Primary:** `#6366F1` (white text 4.47:1, fails AA) → **indigo-600 `#4F46E5`** (6.29:1). Indigo-500 stays as the focus-ring colour (3:1 or more is enough there). **"On primary: black"** → white. **Emerald CTA accent** → used **only** for the success message kind; buttons stay indigo, keeping the identity (spec 03 context). **Background `#F5F3FF`** → keep slate-50, the existing identity. **GSAP scroll reveal and hover motion** → dropped: no JavaScript, and motion is limited to ≤150ms colour transitions, turned off under reduced motion. **Landing-page pattern** (hero, logos, pricing) → not applicable: this is a signed-in app. | Each change comes from a spec constraint or a contrast failure measured above. The "Minimalism & Swiss" style, spacing rhythm, light mode and visible-focus rules from the generated output are kept. |
| Where tokens live | A `@theme { … }` block in `base.html`'s existing `text/tailwindcss` style. It defines **semantic** tokens as exact hex values: `--color-primary`, `--color-primary-hover`, `--color-on-primary`, `--color-ink`, `--color-muted`, `--color-canvas`, `--color-surface`, `--color-border`, `--color-border-strong`, `--color-ring`, plus `success`, `info`, `warning` and `danger` (each with `-bg`, `-fg` and `-border`). It also sets `--font-sans` (the system stack). Templates use `bg-primary`, `text-muted` and so on. | The skill says "semantic tokens, no raw hex in components". Tailwind v4 turns `@theme` variables into utilities with no build step. Fixed hex values make every contrast ratio exact and testable (AC-20). Tailwind's own palette is OKLCH and only close to these hex values. |
| **Q-11: component layering** | Every shared rule (`.btn-primary`, `.btn-secondary`, `.btn-sm` if needed, `.card`, `.form-field …`, `.field-errors`, `.msg`, `.badge`, `.skip-link`) moves into **`@layer components { … }`**. | Tailwind v4 orders layers `theme, base, components, utilities`. Unlayered CSS beats every layer, which is today's bug. In `components`, a page-level utility (`w-full`, `px-6`) overrides the shared rule while everything else stays shared (AC-4). `@utility` would put them in the utilities layer, where conflicts depend on source order, which is less predictable. |
| One button size (AC-4) | `.btn-primary` and `.btn-secondary` share one base: `inline-flex items-center justify-center gap-2 rounded-lg px-4 min-h-11 text-sm font-semibold` (44px tall), with focus-visible ring, hover colour, a `motion-safe:` 150ms colour transition and `cursor-pointer`. The nav's "Register" and "Log out" use the same classes. | 44px meets the skill's touch guidance and goes well past WCAG's 24px (AC-21). One base removes today's three different sizes. |
| Fonts (AC-5) | `--font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;` Body is 16px (`text-base`) with `leading-relaxed` (1.625) for body copy and `leading-normal` (1.5) for UI text. | Spec 03 forbids external fonts. System fonts load instantly and look native on every platform. |
| Input contrast | Input borders use `--color-border-strong` = slate-500 (4.76:1). Card and divider borders stay slate-200, which is decorative and doesn't identify a control. | WCAG 1.4.11 needs 3:1 for the boundary that identifies a control. Today's slate-300 is 1.48:1. |
| Focus (AC-19) | One rule for all focusable elements: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`, applied through the component classes and a `@layer base` rule for plain `a`, `button`, `input`, `summary`. | Today only some step 02 buttons have it. A base rule covers links in body text too, so no element is missed. |
| Icons (AC-25) | Inline SVG partials in `templates/partials/icons/<name>.html`, included with `{% include "partials/icons/check-circle.html" %}`. The paths are copied from **Heroicons v2 outline (MIT)**, with the licence noted in a comment in each file: a 24px viewBox, 1.5 stroke, `currentColor`, `aria-hidden="true" focusable="false"`. The set: `check-circle`, `information-circle`, `exclamation-triangle`, `x-circle`, `plus`, `arrow-left`, `users`, `folder`, `chevron-right`, `user`. | No package and no download: the SVG is in the HTML. One family, one stroke and one size token satisfy the skill's icon rules. Every icon sits next to visible text, so all are decorative (`aria-hidden`). |
| Header and navigation (AC-6, AC-7, AC-9) | `<header>` → `<nav aria-label="Main">` holding the brand link and the same items as today. The current page is worked out in the template from `request.resolver_match.view_name` (`core:dashboard`, `accounts:login`, `accounts:register`). The current link gets `aria-current="page"` plus a visual underline in the primary colour. At narrow widths the bar uses `flex-wrap`: the brand on one line, items on the next. There is no hamburger (spec 03, OQ-3). | `aria-current` is the standard current-page marker. Wrapping needs no JavaScript and handles at most four items down to 320px. |
| Skip link (AC-8) | The first element in `<body>`, before `<header>`, is `<a href="#main" class="skip-link">Skip to main content</a>`. It's hidden until it gets focus, then shown. `<main id="main" tabindex="-1">` so focus lands there. | It's the first focusable element. It sits **outside** `<nav>`, so the step 01 `nav_html()` helper (first `<nav>…</nav>`) is unaffected. |
| Messages (AC-10) | One `<div role="status" aria-live="polite">` wrapper holds a list. Each item has `class="msg msg-{{ message.level_tag }}"` and contains, in order: an icon matching the kind (`aria-hidden`), a visually hidden kind word ("Success:", "Information:", "Warning:", "Error:" via `sr-only`), then `{{ message }}` **unchanged**. All four kinds are defined in tokens and CSS. Today the app emits only success and info (spec 03, OQ-2). No dismiss button. | The message text is untouched, so the tests that look for exact wording still pass. Kind is shown by colour, icon and hidden text, so never by colour alone. |
| Shared form rendering (AC-11, AC-12) | `form_field.html` is rewritten. **Label:** `<label for="{{ field.id_for_label }}">{{ field.label }}{% if field.field.required %}<span class="required-mark" aria-hidden="true">*</span>{% endif %}</label>`. **Widget:** `{{ field }}`, so Django adds `required`, `aria-invalid` and `aria-describedby`. **Help text:** `<div class="helptext" id="{{ field.auto_id }}_helptext">`. **Errors:** `<ul class="field-errors" id="{{ field.auto_id }}_error">`, each with an `x-circle` icon. **Invalid style:** `.form-field [aria-invalid="true"]` gets a danger border and ring. `form_body.html` adds a single "* Required field" note when any visible field is required, and shows non-field errors in a `.msg msg-error` style box before the fields. | Using the IDs Django already points at fixes the broken references without overriding Django. Styling by `aria-invalid` means the visual and announced states can't disagree. The asterisk is hidden from screen readers because the input's `required` attribute already announces it. |
| Autofill (AC-13) | `RegistrationForm.__init__` sets `autocomplete="email"` on `email`. `AddMemberForm` sets `autocomplete="off"`, `autocapitalize="none"` and `spellcheck="false"` on `username`, because it's someone *else's* username and the browser shouldn't fill in yours. `WorkspaceForm` sets `autocomplete="off"` on `name`. | Attributes only, with no validation or behaviour change. Login and registration already have the right hints from Django. |
| Reduced motion (AC-22) | Transitions are only applied with `motion-safe:`. A `@layer base` rule `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition: none !important; animation: none !important; scroll-behavior: auto !important; } }` is the backstop. | Covers anything added later as well. |
| Landmarks and headings (AC-18) | `base.html` has `<html lang="en">` (already there), `<header>`, `<nav aria-label="Main">` and `<main id="main">`. Each page has one `<h1>`, and sections use `<h2>`. Page titles follow "`<Page>` · Project Management System", with the workspace name for the detail page. | Most of this is already true. The tests make it permanent. |

### Page by page

Each page gets the focused searches listed here, and the build notes record
the results that shaped it (AC-2).

| Page | Layout | Skill searches (domain) |
|---|---|---|
| **Header, nav and messages** (`base.html`) | A white header bar with a bottom border. The brand is on the left: wordmark text, and a small indigo square icon marked `aria-hidden`. Items on the right: username as muted text, "Dashboard" link, and "Log out" as `.btn-secondary`. When anonymous: "Log in" link and "Register" as `.btn-primary`. The content width is `max-w-5xl`, with gutters `px-4 sm:px-6`. | `"navigation active state"` (ux), `"skip link keyboard"` (ux), `"toast alert status message"` (ux), `"color not only indicator"` (ux), `"nav header responsive"` (html-tailwind) |
| **Login and register** | One centred `.card` (`max-w-md`). The `h1` is followed by one line of muted supporting text. Then the form via `form_body.html`, then a full-width `.btn-primary` (`w-full`, which is the Q-11 override in use), then a cross-link line. Register keeps Django's password help list, styled through `.helptext`. | `"login form accessible authentication"` (ux), `"password manager paste"` (ux), `"form label error inline"` (ux), `"form validation"` (html-tailwind) |
| **Dashboard** | A page header with `h1` "Welcome, {{ user.username }}", muted supporting text, and a `.btn-primary` with a `plus` icon reading "Create workspace". Then a `.card` `<section aria-labelledby>` with `h2` "Your workspaces" and a count badge. Rows are full-width links: `folder` icon, workspace name (wraps), `chevron-right`, a hover background and the focus ring. The **empty state** sits inside the section: a `folder` icon, the **existing** text "You don't belong to any workspaces yet.", one supporting line, and its **own** `.btn-primary` "Create workspace" (AC-15, which also covers Q-10). | `"empty state call to action"` (ux), `"list row clickable"` (ux), `"dashboard card hierarchy"` (style), `"spacing rhythm"` (ux) |
| **Create workspace** | The same centred `.card` pattern as the auth pages: `h1`, supporting text, the form, then a button row with a primary "Create workspace" and a secondary "Cancel" link. They stack full-width below `sm`. | `"form single field"` (ux), `"cancel secondary action"` (ux) |
| **Workspace detail** | A "← Back to dashboard" link (`arrow-left`). The `h1` is the name, which wraps. A members `.card` has `h2` "Members" and a count badge. Each row has a `user` icon (`aria-hidden`), the username and an **Owner** or **Member** `.badge`. Owner is indigo, Member is slate, and the text tells them apart. For the owner, a separate "Add a member" `.card` with an `h2`, help line, form and `.btn-primary` "Add member". **Each row holds only the username and label as text** (see Test plan, OQ-7). | `"badge label color alone"` (ux), `"member list avatar"` (ux), `"section grouping cards"` (ux) |

## Data model & migrations
None. No model or field changes. The migration-drift check must stay clean.

## URLs, views, templates
No URL or view changes.

| Template or file | Change | Access rule |
|---|---|---|
| `templates/base.html` | `@theme` tokens; `@layer base` and `@layer components`; skip link; header and nav with `aria-current`; messages with role, icon and hidden kind word | unchanged |
| `templates/partials/form_body.html`, `form_field.html` | The required note, help and error IDs, invalid styling and non-field error box | — |
| `templates/partials/icons/*.html` (10 new) | Inline Heroicons outline SVGs, `aria-hidden` | — |
| `accounts/templates/accounts/login.html`, `register.html` | The auth card pattern, `.btn-primary w-full` | unchanged (anonymous only) |
| `core/templates/core/dashboard.html` | The page header, workspace rows, and the empty state with its own create action | unchanged (login required) |
| `workspaces/templates/workspaces/workspace_form.html`, `workspace_detail.html` | The card pattern, button row, member rows, badges, add-member card | unchanged (members, owner) |
| `accounts/forms.py`, `workspaces/forms.py` | Widget `autocomplete` and related attributes only | — |
| `design-system/project-management-system/MASTER.md`, `pages/auth.md`, `pages/dashboard.md`, `pages/workspace.md` | Generated by the skill, plus the "Project adjustments" section | Documentation (spec 03, OQ-6) |

## Implementation steps
- [x] 1. **Design system.** Run the skill's `--design-system --persist` with
  the query, dials and `-p` above, and `--output-dir` set to the repo root.
  Then run `--page auth`, `--page dashboard` and `--page workspace` the same
  way.
  - First check that `design-system/project-management-system/MASTER.md`
    doesn't exist yet; never use `--force`.
  - Append the **"Project adjustments (step 03)"** section to `MASTER.md`:
    - the semantic token table with hex values;
    - the contrast table for every text and interface pair used, with its
      ratio, computed with the WCAG formula;
    - the system font stack and type scale (12/14/16/18/24/30);
    - spacing (a 4px base: 4/8/12/16/24/32/48);
    - radii (`rounded-lg` for controls, `rounded-2xl` for cards,
      `rounded-full` for badges);
    - the button, field, card, message and badge specs, and the focus rule;
    - the icon rules: Heroicons outline, 24px viewBox, 1.5 stroke,
      `size-5`/`size-4`, `aria-hidden` when next to text;
    - each change from the generated output, with its reason (Approach
      table);
    - a short note on how a later dark mode would map the tokens
      (spec 03, OQ-1).
- [x] 2. **Read `MASTER.md`** and the page files. Then run the focused
  searches from the "Page by page" table plus `--stack html-tailwind`
  searches for `"focus visible"`, `"layer components apply"`,
  `"sr-only"` and `"responsive flex wrap"`. Note the results that will be
  applied, for the build notes.
- [x] 3. **`base.html`:**
  - `@theme` tokens and `--font-sans`;
  - `@layer base`: body text, the focus rule for plain controls, and
    reduced motion;
  - `@layer components`: `.btn-primary`, `.btn-secondary`, `.card`,
    `.form-field …`, `.field-errors`, `.required-mark`, `.helptext`, `.msg`
    and `.msg-{success,info,warning,error}`, `.badge` and its variants,
    `.skip-link`;
  - the skip link, header, `<nav aria-label="Main">` with `aria-current`,
    and nav buttons using the shared classes;
  - `<main id="main" tabindex="-1">`;
  - the messages block, with role, icon, hidden kind word and unchanged
    text.
- [x] 4. **Icons:** create the 10 `templates/partials/icons/*.html` files,
  each with the Heroicons MIT attribution comment.
- [x] 5. **Form partials:** `form_field.html` (label with required mark,
  help and error IDs that match Django's `aria-describedby`) and
  `form_body.html` (required note, non-field error box).
- [x] 6. **Autofill attributes:** `accounts/forms.py` (`email`) and
  `workspaces/forms.py` (`AddMemberForm.username`, `WorkspaceForm.name`).
- [x] 7. **Pages:** `login.html`, `register.html`, `dashboard.html`,
  `workspace_form.html` and `workspace_detail.html`, as in "Page by page".
  Keep every existing visible string that tests or the spec rely on:
  - message text;
  - "Welcome, …" and "You don't belong to any workspaces yet.";
  - "Log in", "Register", "Dashboard", "Log out";
  - "Owner" and "Member";
  - button labels.
- [x] 8. **Self-check:** `manage.py check`, then
  `makemigrations --check --dry-run`, then
  `manage.py test` (the existing 140).
  - Any existing failure is first treated as a **template** mistake.
  - Only if the test checks markup structure rather than behaviour does it
    go to `test-author` under spec 03, OQ-7 (see Test plan).
- [x] 9. **Visual and responsive check (D-1):** check every page, both
  anonymous and signed in, as owner, member and empty-dashboard user, at
  **320, 768 and 1280px**:
  - no sideways scrolling;
  - text is readable;
  - long names wrap;
  - the focus ring is visible when tabbing through each page;
  - the skip link appears.

  Record the results per page.

  **How (D-1, answered):**
  - If the Chrome browser tool (`claude-in-chrome`) is connected, Claude
    runs this check itself, takes screenshots, and records the results.
  - If it isn't available, `/build` **stops here**. It gives you the manual
    checklist below (the same items as step 9a) and waits for your results
    before moving on. Either way, the check happens before `/review`.
- [x] 9a. **Target size (AC-21), checked for every kind of interactive
  target, not only buttons.** Each target must be at least 24 × 24 CSS px,
  measured by its clickable box (in the browser, its bounding rectangle), or
  meet WCAG 2.2 AA's spacing exception: a 24px circle centred on the target
  doesn't overlap any neighbouring target or its circle. Check every
  category at 320px and at 1280px:

  | Target category | Where |
  |---|---|
  | Skip link (while focused) | every page |
  | Brand link | header |
  | Navigation links: "Dashboard", "Log in" | header |
  | Navigation buttons: "Register", "Log out" | header |
  | Auth cross-links: "Create an account" / "Log in" | login, register |
  | Primary and secondary buttons (all submit buttons, "Create workspace" links) | every page with one |
  | Workspace row links | dashboard |
  | Back link: "← Back to dashboard" | workspace detail |
  | Cancel link | create workspace |
  | Form inputs (text, email, password) | all forms |

  Inline links in a sentence (the auth cross-links) may use WCAG's
  **inline** exception. Even so, they get vertical padding so their box
  reaches 24px. The plan gives every link that isn't inline (nav, back,
  cancel, rows) a minimum height of at least 24px. Record a pass or fail
  for each category, with the measured size or the exception used, in the
  build notes (step 11).
- [x] 10. **Pre-delivery checklist:** go through every item of the skill's
  canonical checklist (`references/pro-rules.md`, "Pre-Delivery Checklist")
  and its final pass (`references/quick-reference.md` §1–§3).
  - Record each item as passed, or as not applicable with a reason. For
    example: safe areas, gestures and native "Dynamic Type" are N/A for a
    web app. Dark mode is N/A (spec 03, OQ-1). "Focus a linked error summary
    after submit" needs JavaScript, which this step excludes, so inline
    errors stay and the gap is noted.
  - Also run the generated design system's own checklist: no emoji icons,
    `cursor-pointer`, hover transitions of 150–300ms, contrast,
    focus-visible, reduced motion, and 375/768/1024/1440 widths.
- [x] 11. **Build notes (AC-2):** under Files changed, add a "UI build notes"
  table. For each page it lists the design-system rules applied, the
  searches (query, domain, top result used) and their effect, and the
  checklist outcome. A separate **target-size table** has one row per
  target category from step 9a: category, size at 320px and at 1280px,
  pass or exception used. It also records how step 9 was done (browser tool
  or the user's manual check).
- [x] 12. Hand off to `test-author` (with spec 03, this plan and Files
  changed), then to `test-runner`, following `/build`.

## Test plan

**Existing tests, spec 03 OQ-7.** The goal is that **no existing test needs
changing**. The markup-sensitive helpers, and how the design keeps them valid:

| Test helper or assertion | What it relies on | How the redesign keeps it valid |
|---|---|---|
| `core/tests/test_views.py::nav_html` | The first `<nav>…</nav>` holds the auth items. The anonymous nav doesn't contain "Dashboard" or "Log out", and the signed-in nav doesn't contain "Log in" or "Register" | One `<nav>`. The skip link sits outside it. No other text containing those words goes in the nav. |
| `workspaces/tests/test_views.py::member_rows` | Any `<li>` whose text, with tags stripped, is "`<name>` Owner" or "`<name>` Member" | Member rows hold only the username and the badge as text. The icon is a text-free SVG. No hidden text goes in a row. Message `<li>` items don't end in "Owner" or "Member". |
| `input_tag` / `add_member_form_tag` regexes | `<input … name="…">` and `<form … action="…">` | Unchanged: Django renders the widgets, and the forms keep `action`. |
| `assertContains` on message text, "Welcome, Alice", the empty-state text and escaped names | The exact strings | Kept word for word (AC-10, step 7). |

If one does break, `test-author` may change it only to check the **same
behaviour** in a sturdier way, for example `response.context['members']`
for Q-9. Each change is listed in Files changed and checked at review.
Behaviour assertions are never removed or weakened.

**New tests** go in `core/tests/test_ui.py`, with the module docstring
saying "spec 03" and tags reading "spec 03 AC-n". They run over a page
matrix: login, register, dashboard (with and without workspaces), create
workspace, and workspace detail as owner and as member.

| AC | Test module | What it asserts |
|---|---|---|
| AC-1 | core/test_ui | `design-system/project-management-system/MASTER.md` exists. It contains the "Project adjustments" heading and mentions the font stack, a contrast table, buttons, messages and focus. |
| AC-2 | — (review) | The build notes table exists in the plan, with one row per page and the checklist record. Checked by `quality-reviewer`. |
| AC-3 | core/test_ui | Every page in the matrix renders the same `<header>`, `<nav aria-label="Main">` and `<main id="main">` structure, and uses `.card` for its main panels. |
| AC-4 | core/test_ui | Every submit button and the nav's "Register" and "Log out" carry `btn-primary` or `btn-secondary`. The style block defines both inside `@layer components` (Q-11), and no page uses hand-written button colour classes (`bg-indigo-600` and similar). |
| AC-5 | core/test_ui | No page contains `fonts.googleapis`, `@import url(` or `<link rel="stylesheet"`. The style block sets `--font-sans` to a system stack. |
| AC-6 | (existing) core/test_views nav tests | Step 01 AC-20 and AC-21 still pass unchanged. |
| AC-7 | core/test_ui | `aria-current="page"` is on "Dashboard" on the dashboard, on "Log in" at login, and on "Register" at register. Exactly one per page, and none on the workspace pages. |
| AC-8 | core/test_ui | The first `<a>` or `<button>` in `<body>` is `href="#main"` with the text "Skip to main content", and `id="main"` exists on `<main>`. |
| AC-9, AC-23 | — (step 9 record: by browser tool, or by the user's manual check if the tool isn't available) and core/test_ui | Responsive results are recorded per page. The test checks that the viewport meta is present and that the nav container uses `flex-wrap`, the non-JavaScript way to wrap. |
| AC-10 | core/test_ui | After registering, logging out, creating a workspace and adding a member: the exact message text is present, inside `role="status"`, with the hidden kind word ("Success:" or "Information:") and an `aria-hidden` SVG. No dismiss button appears. |
| AC-11 | core/test_ui | Register: each required field's label has the required mark, the "Required field" note appears once, and password1's `aria-describedby` points to an element with that ID containing the help text. |
| AC-12 | core/test_ui | Each invalid form: an invalid register, a create workspace with an empty name, and add-member with an unknown user. The invalid input has `aria-invalid="true"`. Its `aria-describedby` includes `<id>_error`, and an element with that ID holds the error text. Login's non-field error shows above the fields. |
| AC-13 | core/test_ui | `autocomplete` is `username`/`current-password` at login, `username`/`email`/`new-password`×2 at register, `off` for workspace name and add-member username. The submit labels are "Log in", "Create account", "Create workspace", "Add member". |
| AC-14 | core/test_ui | Login links to register and register links to login, each inside the card, with one `h1`. |
| AC-15 | core/test_ui | The dashboard has a "Create workspace" link. The empty state's section contains the empty text **and** its own link to `workspaces:create`. Rows link to `detail`. |
| AC-16 | core/test_ui and existing step 02 tests | A back link to the dashboard, the member count, Owner and Member text labels, and the "Add a member" section only for the owner. |
| AC-17 | core/test_ui | The create page has a primary "Create workspace" button and a secondary "Cancel" link to the dashboard. |
| AC-18 | core/test_ui | Every page has `lang="en"`, a unique `<title>`, exactly one `<h1>`, headings that never skip a level (parsed in order), `<main>`, and a labelled `<nav>`. |
| AC-19 | core/test_ui | The style block has the `focus-visible` ring rule for `a`, `button` and `input` in `@layer base`, and both button classes include `focus-visible:ring`. |
| AC-20 | core/test_ui | The test reads the `@theme` hex tokens from `base.html` and checks the WCAG ratio for each declared pair: ink/canvas, muted/surface, on-primary/primary, primary/surface (links), each message `fg`/`bg`, badge text/background ≥ 4.5, and border-strong/surface and ring/surface ≥ 3. |
| AC-21 | core/test_ui, plus the step 9a target-size table | **Test:** the button classes include `min-h-11`. Nav links, the back link, the cancel link and workspace row links carry a minimum height of at least 24px (`min-h-6` or larger). **Record:** step 9a's table has every target category, at 320px and 1280px, each passing or naming the WCAG 2.2 AA exception it uses. `quality-reviewer` checks the table is complete. |
| AC-22 | core/test_ui | The style block contains the `prefers-reduced-motion: reduce` rule, and no transition class appears without `motion-safe:`. |
| AC-24 | full suite | All 140 existing tests pass, and any OQ-7 changes are listed. |
| AC-25 | core/test_ui | The only `<script src>` is the Tailwind CDN, and there's no `<link rel="stylesheet">`. Every `<svg>` has `aria-hidden="true"` or a `<title>`. |
| AC-26 | core/test_ui and existing tests | Every `<form method="post">` in the matrix contains `csrfmiddlewaretoken`. Logout is still a POST form (step 01 AC-21 test). The escaping tests from step 02 AC-8 still pass. |

**Verification** (`/build` runs these through `test-runner`, in this order):
- [x] Focused: `.venv/Scripts/python.exe manage.py test core.tests.test_ui`
- [x] Drift: `.venv/Scripts/python.exe manage.py makemigrations --check --dry-run` → "No changes detected"
- [x] Checks: `.venv/Scripts/python.exe manage.py check` → no issues
- [x] Full suite: `.venv/Scripts/python.exe manage.py test`. All pass: the 140
  existing tests plus the new ones.
- [x] Visual and responsive record (step 9), target-size table for each
  category (step 9a) and pre-delivery checklist record (step 10), all
  present in the build notes.

## Risks

| Risk | Mitigation |
|---|---|
| The redesign silently changes behaviour or wording | No view, URL, model or message change is planned. Visible strings the tests rely on are listed in step 7. The full suite runs after the templates change (step 8) and again in verification. |
| A markup change breaks a test that checks behaviour | The design keeps the `nav_html` and `member_rows` assumptions (Test plan table). Any unavoidable change follows spec 03 OQ-7 and is listed. |
| Tailwind v4 browser build doesn't support `@theme` or `@layer components` inside `text/tailwindcss` as expected | Both are documented v4 features. Step 9's visual check catches any failure. Fallback: plain CSS variables plus `@layer components` with explicit values; still no new dependency. |
| The skill's generated output pulls in fonts, GSAP or an accent CTA | Changed and recorded in `MASTER.md` "Project adjustments". The AC-5 and AC-25 tests fail if a font link or a new script slips in. |
| Contrast regresses later | AC-20 checks the ratios from the tokens in code, so a later token change that breaks AA fails the test. |
| Copied Heroicons paths and licensing | MIT licence. Attribution is in each icon partial. No package is installed. |
| `role="status"` content that is already on the page when it loads isn't announced by every screen reader | Accepted as a known limitation of server-rendered messages without JavaScript. Noted in the checklist record. |
| `--persist` overwrites an existing design system | Step 1 checks it doesn't exist first. `--force` is never used without the user's approval (CLAUDE.md). |
| The style block in `base.html` grows large | Acceptable for now. One file is easy to review. A future DevOps step that replaces the Play CDN with a build will move it into a stylesheet. |

## Decisions needing approval

This was answered by the user on 2026-10-05.

- **D-1: How are the visual and responsive checks (AC-9, AC-21, AC-23, part
  of AC-2) carried out?** Django tests can't render layouts.
  - *Answer:* **(a).** During `/build`, Claude uses the Chrome browser tool
    (`claude-in-chrome`), if it's connected:
    - it opens each page at 320, 768 and 1280px;
    - it takes screenshots, tabs through the focus order, and measures the
      targets for each category (step 9a);
    - it records everything in the build notes.

    If the tool isn't available, `/build` stops at step 9 and gives you the
    manual checklist (steps 9 and 9a) before `/review`.
  - The user also asked that AC-21 be checked for **every** kind of
    interactive target, not only buttons (step 9a, Test plan AC-21).

## Files changed
Application, templates and design system (by `/build`, 2026-10-05; steps 1–8):
- created `design-system/project-management-system/MASTER.md`: generated by ui-ux-pro-max `--design-system --persist` (query "B2B project management SaaS productivity team workspace", variance 3, motion 2, density 5), plus the appended "Project adjustments (step 03)" section: changes to the generated output and why, semantic tokens, contrast table (all AA), typography, spacing and radii, components, page overrides, dark-mode note
- created `design-system/project-management-system/pages/auth.md`, `pages/dashboard.md`, `pages/workspace.md`: generated page overrides (`--page`); MASTER's adjustments win where they differ
- modified `templates/base.html`:
  - `@theme` semantic tokens and the system `--font-sans`;
  - `@layer base`: body, the focus-visible ring for plain controls, the reduced-motion rule;
  - `@layer components`: buttons (Q-11), card, link, nav-link with `aria-current`, skip link, form field, required mark, help text, errors, message kinds, badges;
  - skip link; `<header>` with `<nav aria-label="Main">` and `aria-current`; nav buttons use `.btn-*`;
  - `<main id="main" tabindex="-1">`;
  - messages in `role="status"`, each with a matching icon and a hidden kind word, message text unchanged
- created `templates/partials/icons/` (11 files): `check-circle`, `information-circle`, `exclamation-triangle`, `x-circle`, `plus`, `arrow-left`, `users`, `folder`, `chevron-right`, `user`, `rectangle-stack`. Inline Heroicons v2 outline (MIT), `aria-hidden`.
- modified `templates/partials/form_field.html`: label with the required mark (hidden from screen readers); help text and errors carry `<id>_helptext` and `<id>_error`, the IDs Django's `aria-describedby` already points at; error icon
- modified `templates/partials/form_body.html`: one "* Required field" note; non-field errors in a `.msg-error` box
- modified `accounts/forms.py`: `email` widget `autocomplete="email"`
- modified `workspaces/forms.py`:
  - `WorkspaceForm.name`: `autocomplete="off"`;
  - `AddMemberForm.username`: `autocomplete="off"`, `autocapitalize="none"`, `spellcheck="false"`
- modified `accounts/templates/accounts/login.html`, `register.html`: card pattern, supporting line, `.btn-primary w-full`, `.link` cross-link
- modified `core/templates/core/dashboard.html`: page header with a primary "Create workspace" (`plus` icon), workspaces card with count badge, full-width row links (`min-h-11`), and an empty state with its own create action
- modified `workspaces/templates/workspaces/workspace_form.html`: card pattern; Cancel (secondary) and Create (primary) stack on mobile
- modified `workspaces/templates/workspaces/workspace_detail.html`: back link (`min-h-11`), `h1`, members card (icon, count badge), rows with user icon, name and Owner/Member badge (only those as text), owner-only "Add a member" card
- no model, view, URL or message-wording changes; no migration; no new dependencies

Differences from the plan text:
- **Border tokens** are named `--color-line` and `--color-line-strong` (not `border`/`border-strong`), so the utilities read `border-line` rather than `border-border`.
- **Badge tokens** are `owner-*` and `member-*`.
- **An 11th icon,** `rectangle-stack`, is used for the brand mark.
- **The required note** is printed once by `{% ifchanged %}` inside the field loop.
- **Extra tokens** not named in the plan: `--color-link`, `--color-ink-soft`, `--color-subtle` and `--color-danger`. The message tokens use `-line` instead of `-border` (`--color-success-line` and so on). All are documented in MASTER.
- **Extra components** not named in the plan: `.link` (inline text links), `.nav-link` (header links with `aria-current` styling) and `.form-note` (the "Required field" note).
- **Body line height** is `leading-normal` (1.5) on `<body>`, not `leading-relaxed`. The app has short UI text and no long copy, so 1.5 suits it. MASTER's 1.625 "body copy" figure is left for future long-form text (step 03 review Q-22, accepted).
- **Review fixes** (`/build 03 retest`, 2026-10-06): the invalid rule has no danger ring, only a danger border, because a component-layer ring would replace the keyboard focus ring (Q-12). Focus uses `outline-hidden` (Q-13).

**Existing tests:** all 140 still pass with **no test changes** (step 8), so no spec 03 OQ-7 adjustments were needed.

Review fixes (`/build 03 retest`, 2026-10-06: Q-12, Q-13, Q-14, Q-15, Q-16, Q-17, Q-18, Q-23). The ui-ux-pro-max skill was loaded first, as CLAUDE.md requires for template fixes.
- modified `templates/base.html`:
  - Q-12: the invalid rule is now `.form-field input/select/textarea[aria-invalid="true"]`. It has the same specificity as the normal field rule and comes after it, so the danger border actually shows.
  - Q-13: `outline-none` → `outline-hidden` in the base focus rule and the `.btn-*` rule, so forced-colors mode shows focus.
  - Q-14: the nav username gets `min-w-0 max-w-full wrap-anywhere`.
- modified `design-system/project-management-system/MASTER.md` (Q-18, plus notes for Q-12 and Q-13):
  - a precedence note at the top;
  - the adjustments now also override `pages/*.md`;
  - a row rejecting the auth and workspace 1200px/grid overrides;
  - the Focus row explains `outline-hidden` and why the button focus rule repeats the base rule;
  - the Form fields row explains the invalid-rule specificity.
- modified `design-system/project-management-system/pages/auth.md`, `dashboard.md`, `workspace.md` (Q-18): a precedence note at the top, and a correction of the wrong MASTER path in the generated banner.
- modified this plan's build notes:
  - Q-15: stale "pending" rows and the target-size intro;
  - Q-16: the missing searches recorded, plus colour/typography and checklist-scope notes;
  - Q-17: the target table now says sizes were user-reported, not measured, and the cross-link row matches MASTER's inline exception;
  - Q-23: the "Differences from the plan text" list is complete.
- modified `core/tests/test_ui.py` (by `test-author`; 46 → 49 tests):
  - comment-tolerant CSS parsing and a specificity helper;
  - Q-12: the test now proves the invalid rule beats the normal field rule on specificity and source order, in the same layer. It fails against the old selector, which `test-runner` confirmed with an in-memory patch;
  - new: a specificity-helper test, the Q-13 `outline-hidden` test, and the Q-14 long-username wrap test.
- no behaviour, view, URL, model or dependency changes; no migration.

### UI build notes (spec 03 AC-2; plan steps 9–11)

**How step 9 is done:** the Chrome browser tools weren't connected, so under
D-1 the visual and responsive check (step 9) and the target-size check
(step 9a) were **the user's manual check**. The user reported **"all pass"**
on 2026-10-05: every page at 320, 768 and 1280px, and every target category
at 320 and 1280px. Exact sizes weren't reported. Items that depended on it are
marked **user-reported pass** below. Everything else was checked from
the code and the tests.

**Design-system rules and skill guidance for each page.** The rules come from
MASTER.md "Project adjustments", and every page uses the semantic tokens,
system font, focus rule and reduced-motion rule. Searches are given as query
(domain) → result applied.

| Page | Design-system rules applied | Skill searches → effect |
|---|---|---|
| Header, nav and messages (`base.html`) | Navigation, skip-link, message, button (Q-11 layering, one size), focus and motion specs; tokens; `max-w-5xl` with `px-4 sm:px-6` | "navigation active state" (ux) → `aria-current` plus an underline in primary. "skip link keyboard" (ux) → skip link as the first focusable element. "toast alert status message" (ux) → auto-dismiss **rejected** (needs JavaScript; recorded in MASTER). "color not only indicator" (ux) → a matching icon and a hidden kind word for each message. "nav header responsive" (html-tailwind) → `flex-wrap` with no `hidden md:*` swap, so the content doesn't change per breakpoint. "sr-only" (html-tailwind) → hidden kind words. "focus visible" (html-tailwind) → `focus-visible:ring-2`, keyboard only. "layer components apply" (html-tailwind) → the "avoid @apply bloat" advice is accepted only for shared components, which Q-11 and CLAUDE.md need; page layout stays as utilities. "reduced motion" (ux) → `prefers-reduced-motion` base rule |
| Login and register | Auth page override (centred `max-w-md` card, supporting line, full-width primary, cross-link); form-field spec | "login form accessible authentication" (ux) → paste and password managers allowed, Django's `autocomplete` kept. "password manager paste" (ux) → show/hide toggle **rejected** (needs JavaScript; recorded). "form label error inline" (ux) → error under the field, connected with `aria-describedby` (`<id>_error`); the focusable error summary was **rejected** (needs JavaScript; recorded). "form validation" (html-tailwind) → no result; retried as "input error state" → inputs share one height (`min-h-11`) |
| Dashboard | Dashboard override from MASTER (same width, single list; the generated 1400px/12-column override was rejected); card, badge and row specs | "empty state call to action" (ux) → the empty state has its own message and its own "Create workspace" (also fixes Q-10). "list row clickable" (ux) → no result; retried as "clickable card link" → no result, so the skill's **general** rules were used as a fallback: a full-row link, 44px minimum, hover background, focus ring. "spacing rhythm" (ux) → 8px or more between targets, `wrap-anywhere` for long names. "dashboard card hierarchy" (style; run 2026-10-06 in the review-fix round) → top results "Dimensional Layering" and "Bento Box Grid", both "neutral base plus brand accent". The neutral white card on the slate canvas with an indigo primary matches; the bento grid was **not** applied (one short list, same width as other pages). |
| Create workspace | Workspace override (auth card pattern); button pair | "form single field" (ux) → inline error linked to the field. "cancel secondary action" (ux) → no result; retried as "secondary button hierarchy" → only off-topic results (back button, breadcrumbs), so the general rules were used: secondary before primary in the DOM, stacked full width on mobile, side by side from `sm` |
| Workspace detail | Workspace override; card, badge (text carries the meaning), back-link and target specs | "badge label color alone" (ux) → Owner/Member as text badges, `whitespace-nowrap shrink-0`. "responsive flex wrap" (html-tailwind) → `min-w-0` with `wrap-anywhere` on the username, and the badge doesn't shrink. "section grouping cards" (ux) → separate cards for members and "Add a member"; the smooth-scroll suggestion was **rejected** (motion; recorded). "member list avatar" (ux; run 2026-10-06) → no result; retried as "avatar user list" (ux) → off-topic (breadcrumbs, reduced motion). **Fallback** to the general rules: a decorative `user` icon (`aria-hidden`), the username as plain text, and the Owner/Member text badge; no image or initials avatar. |

**Colour and typography for every page.** No colour or typography search was run per page during the build. Every page uses the same tokens and type scale, which came from the `--design-system` run and MASTER's "Project adjustments". Two focused searches were added in the review-fix round (2026-10-06):
- **"saas productivity indigo professional" (color):** top result "Micro SaaS", `#6366F1` indigo primary with an emerald CTA. This confirms the indigo direction. The primary was darkened to `#4F46E5` for AA contrast, and emerald is limited to success messages, as recorded in MASTER.
- **"system font sans readable ui" (typography):** results "Plus Jakarta Sans + System" and "Inter, system fallback". Both are web fonts, so they're **rejected** under spec 03 AC-5. Their "system-first" scale advice (bold headings, 600 subheadings, 1.5 body line height) matches the system stack and weights used.

**Checklist scope.** The pre-delivery checklist below was applied to **every** page in the table above. No item had a page-specific result, so the global record stands for each page.

**Target sizes (AC-21; step 9a).** The "Size from CSS" column is the size the
CSS is designed to produce. It was **not measured**. The 320px and 1280px columns record the user's manual
check (D-1), reported on 2026-10-05 as "all pass" for every category. **No individual sizes were reported**,
so these rows confirm a pass, not a measurement.

| Target category | Where | Size from CSS (designed, not measured) | 320px: user-reported (not measured) | 1280px: user-reported (not measured) | Result or exception |
|---|---|---|---|---|---|
| Skip link (while focused) | every page | `py-3` + `text-sm`, about 44px tall | user-reported pass | user-reported pass | pass |
| Brand link | header | `min-h-11` (44px) | user-reported pass | user-reported pass | pass |
| Nav links (Dashboard, Log in) | header | `.nav-link`: `min-h-11`, `px-2` | user-reported pass | user-reported pass | pass |
| Nav buttons (Register, Log out) | header | `.btn-*`: `min-h-11`, `px-4` | user-reported pass | user-reported pass | pass |
| Auth cross-links | login, register | inline `.link`: `py-1`, 14px text, about 24px tall | user-reported pass | user-reported pass | user-reported pass; inline-link exception (WCAG 2.5.8) applies if under 24px, matching MASTER. Designed to be about 25px tall |
| Primary and secondary buttons | all pages | `min-h-11` (44px) | user-reported pass | user-reported pass | pass |
| Workspace row links | dashboard | full width, `min-h-11` | user-reported pass | user-reported pass | pass |
| Back link | workspace detail | `min-h-11` | user-reported pass | user-reported pass | pass |
| Cancel link | create workspace | `.btn-secondary`, `min-h-11` | user-reported pass | user-reported pass | pass |
| Form inputs | all forms | `min-h-11`, full width | user-reported pass | user-reported pass | pass |

**Pre-delivery checklist (step 10).** This is the skill's canonical
checklist (`references/pro-rules.md`), plus the final pass over
`quick-reference.md` §1–§3 and the generated MASTER checklist.

| Item | Result |
|---|---|
| *Process:* ran only searches relevant to the interface | pass (table above; empty searches retried once, with the fallback stated) |
| *Process:* reviewed quick-reference §1–§3 (accessibility, touch, performance) | pass: contrast tokens, keyboard and focus, labels, target-size rules, no images and no layout shift (no web fonts, inline SVG) |
| *Process:* tested at 375px and in landscape | user-reported pass, covered by the step 9 widths (320/768/1280) |
| *Process:* reduced motion and largest text size | reduced motion: pass (base rule, `motion-safe:` only). Text zoom and reflow: user-reported pass |
| *Process:* dark-mode contrast | N/A: dark mode out of scope (spec 03, OQ-1); token mapping noted in MASTER |
| *Process:* touch targets, nothing hidden behind safe areas | targets: see the table above. Safe areas: N/A (web, no fixed bars) |
| *Visual:* no emoji icons | pass |
| *Visual:* one consistent icon family | pass (Heroicons v2 outline only, 1.5 stroke) |
| *Visual:* official brand assets | N/A (no third-party logos; the brand mark is an icon) |
| *Visual:* pressed state doesn't shift layout | pass (colour-only states, no transforms) |
| *Visual:* semantic tokens, no hard-coded colours per screen | pass (all page colours use tokens; no Tailwind palette colour classes left in templates) |
| *Interaction:* clear pressed and hover feedback | pass (hover and focus colours; `motion-safe` 150ms) |
| *Interaction:* touch target minimum | see the table above |
| *Interaction:* shared timing tokens | pass (one 150ms colour transition) |
| *Interaction:* disabled states | N/A (no disabled controls) |
| *Interaction:* screen-reader order matches visual order, descriptive labels | pass from the DOM: skip link, header, main; labels and button text describe the action. Visual order: user-reported pass |
| *Interaction:* gesture conflicts | N/A (no gestures) |
| *Light/dark:* primary and secondary text at least 4.5:1 | light: pass (MASTER contrast table; checked by a test). Dark: N/A |
| *Light/dark:* dividers and states distinguishable | light: pass (control boundaries 4.76:1, focus ring at least 4.27:1). Dark: N/A |
| *Light/dark:* modal scrim | N/A (no modals) |
| *Layout:* safe areas, sticky bars | N/A (no fixed or sticky UI; skip link is fixed only while focused) |
| *Layout:* small, large and tablet widths | pass: user manual check at 320/768/1280px, reported "all pass" on 2026-10-05 |
| *Layout:* gutters adapt | pass (`px-4 sm:px-6`, `py-8 sm:py-12`) |
| *Layout:* 4/8 spacing rhythm | pass (Tailwind 1/2/3/4/5/6/8/12 steps only) |
| *Layout:* readable text measure | pass (single `max-w-5xl` column; forms `max-w-md`) |
| *A11y:* decorative icons hidden | pass (every SVG has `aria-hidden="true" focusable="false"`) |
| *A11y:* meaningful icons have a text alternative | pass (message icons paired with a hidden kind word; no icon stands alone) |
| *A11y:* icon controls have a name and state | N/A (no icon-only controls) |
| *A11y:* labels, hints, clear errors | pass (visible labels, help text and errors linked with matching IDs) |
| *A11y:* colour isn't the only indicator | pass (message icon and word, Owner/Member text, error icon and text, `aria-current` underline) |
| *A11y:* reduced motion and dynamic text without breakage | reduced motion: pass. Text scaling: user-reported pass |
| *A11y:* sticky UI doesn't hide focus | pass (no sticky UI) |
| *A11y:* drag and swipe alternatives | N/A |
| *A11y:* authentication allows password managers and paste | pass (`autocomplete` hints, no paste blocking) |
| *A11y:* auto-rotating content | N/A |
| *A11y:* failed forms keep inline errors; error summary is focused | inline errors: pass. Focused summary: **not done**, because it needs JavaScript (spec 03 out of scope); gap recorded in MASTER |
| *MASTER list:* `cursor-pointer` on clickable elements | pass for buttons. Links get the pointer by default |
| *MASTER list:* hover transitions 150–300ms | pass (150ms) |
| *MASTER list:* responsive 375/768/1024/1440 | pass: user manual check at 320/768/1280px, reported "all pass" on 2026-10-05 (exact 375/1024/1440 widths not separately checked) |
| *MASTER list:* no horizontal scroll on mobile | pass: user manual check at 320/768/1280px, reported "all pass" on 2026-10-05 |
| *Known limitation:* `role="status"` messages already on the page at load aren't announced by every screen reader | accepted (plan Risks); no JavaScript |

## Test results
Run on 2026-10-05 by `test-runner`. Python 3.12.10, Django 5.2.17.

| Check | Command | Result |
|---|---|---|
| Focused | `manage.py test core.tests.test_ui` | 46/46 OK |
| Drift | `manage.py makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | No issues (0 silenced) |
| Full suite | `manage.py test` | 186/186 OK (140 existing + 46 new) |

- **Test author:** `test-author` wrote `core/tests/test_ui.py`, 46 tests tagged "spec 03 AC-n". It reported no application defects, so there were 0 fix rounds.
- **AC citations:**
  - Every spec 03 AC is cited, except the three the plan covers another way:
    - AC-2, by review of the build notes;
    - AC-6, by the existing step 01 nav tests;
    - AC-24, by the full suite.
  - AC-23 is cited together with AC-9 ("spec 03 AC-9 / AC-23"), for the parts visible in the HTML.
- **Existing tests:** none changed (spec 03 OQ-7 was not needed). Checked against the file modification times, because there's no git.
- **Manual check (D-1):** the browser tools weren't connected, so the user did steps 9 and 9a by hand and reported "all pass" on 2026-10-05. The UI build notes are updated. Nothing is unresolved.

Retest after the review fixes (`/build 03 retest`, 2026-10-06, run by `test-runner`):

| Check | Command | Result |
|---|---|---|
| Focused | `manage.py test core.tests.test_ui` | 49/49 OK |
| Drift | `manage.py makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | No issues (0 silenced) |
| Full suite | `manage.py test` | 189/189 OK (140 existing + 49) |

- 0 application defects and 0 fix rounds.
- One expected test failure, the old Q-12 test that looked up the replaced selector, was rewritten by `test-author`.
- No test outside `core/tests/test_ui.py` changed.

## Review log

### 2026-10-06: full review (security-reviewer + quality-reviewer)

**Scope:**
- the "Files changed" list above (not a git repo);
- views, URLs, models and settings, confirmed untouched by their modification times.

**Security: no findings at any severity.**
- Access control from steps 01 and 02 is unchanged.
- No `|safe`, `autoescape off` or `csrf_exempt` anywhere.
- User text (workspace names, usernames, messages, errors) is escaped everywhere. The icon `class` include variable is escaped and only ever receives literal values.
- Every POST form has a CSRF token, and logout is still POST-only.
- The `next` hidden field on login is escaped.
- No new external resources and no inline event handlers.

Two optional hardening notes, not findings:
- the icon includes could use `only`;
- a regression test could feed a quoted `next` value.

**Quality.** Finding IDs continue after step 02's Q-11, which CLAUDE.md still refers to. The orchestrator confirmed Q-12 (selector specificity) and Q-15 (stale rows) by reading the files.

| ID | Sev | file:line | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| Q-12 | **High** | `templates/base.html:73-74`; test `core/tests/test_ui.py:785-789` | **The invalid-input border never shows.** `.form-field input:not([type="hidden"])` (specificity 0,2,1) beats `.form-field [aria-invalid="true"]` (0,2,0) in the same layer, so `border-line-strong` always wins over `border-danger`. Part of AC-12 ("visibly marked as invalid") fails, against the plan and MASTER. The test only checks that the rule exists. | Give the invalid rule at least equal specificity (e.g. `.form-field input[aria-invalid="true"]`, plus select and textarea), optionally adding the planned ring. `test-author` strengthens the test to check the selector actually outranks the base input rule. | fixed |
| Q-13 | Medium | `templates/base.html:51`, `:59` | In Tailwind v4, `outline-none` means `outline-style: none`; the v3 transparent-outline behaviour is now `outline-hidden`. The focus indicator is a box-shadow ring, which Windows forced-colours (High Contrast) mode removes, so keyboard users in that mode get **no** focus indicator (AC-19). | Use `outline-hidden` instead of `outline-none` in the base focus rule and the `.btn-*` rule. Say in MASTER whether the duplicated focus tokens on `.btn-*` are deliberate. | fixed |
| Q-14 | Medium | `templates/base.html:106` | The nav username has no `min-w-0` or `wrap-anywhere`. A long username with no spaces (up to 150 characters) can push the page sideways at 320px (AC-23). Every other place that shows user text has `wrap-anywhere`. | Add `min-w-0 wrap-anywhere` (or `max-w-full`) to the nav username `<span>`. | fixed |
| Q-15 | Medium | plan `:403`, `:445`, `:462`, `:463` | Three checklist rows still say "pending (manual, step 9)", and the target-size intro reads "pass (user manual check) until you report it". That contradicts "all pass" / "nothing unresolved", and AC-2 requires each item to be passed or N/A. | Change them to "pass (user manual check, 2026-10-05)" and fix the sentence. | fixed |
| Q-16 | Medium | plan `:109`, `:111` vs build notes `:398`, `:400` | Two planned searches aren't recorded: "dashboard card hierarchy" (style) and "member list avatar" (ux). No colour or typography search is recorded for any page. The per-page table has no checklist-outcome column (step 11). AC-2 and the CLAUDE.md full-workflow rule are only partly evidenced. | Run and record the two searches, or say why not. Note that colour and typography come from the `--design-system` run and MASTER's adjustments, or run focused searches. State that the global checklist applies to every page, or add a per-page note. | fixed |
| Q-17 | Medium | plan `:402-416`; `MASTER.md:370` | **AC-21 evidence wording.** The 320/1280 columns say "pass (user manual check)", but no sizes were measured, and "Size from CSS" is an estimate. The cross-link row claims "no exception needed", which the user's report doesn't support, and it contradicts MASTER (inline exception). Acceptable in kind under D-1, but overstated. | Retitle the columns "User-reported result (sizes not measured)". Mark the cross-link row "inline exception (WCAG 2.5.8); about 25px expected", matching MASTER. Or ask the user for measured sizes. | fixed |
| Q-18 | Medium | `MASTER.md:3-5`; `pages/auth.md:7`, `dashboard.md:7`, `workspace.md:7` | **Precedence between the design-system files is unclear.** The generated banners say page files override MASTER, and they point to the wrong path. Only line 240 says the adjustments override everything; readers meet Google Fonts, the emerald CTA and GSAP first. The auth and workspace page files' "1200px, responsive grid" overrides aren't listed as rejected. | Add a note at the very top of MASTER.md and of each page file: "Project adjustments override everything else here and in pages/*.md". Add a row rejecting the 1200px/grid overrides for auth and workspace. | fixed |
| Q-19 | Low | `core/templates/core/dashboard.html:18`, `workspaces/templates/workspaces/workspace_detail.html:16` | The count badges reuse `.badge-member` (the role badge). Screen readers hear a bare number. | Add a neutral `.badge-count`, and optionally an sr-only word ("members", "workspaces"). | accepted (user, 2026-10-06) |
| Q-20 | Low | `login.html:6-9`, `register.html:6-9`, `workspace_form.html:6-9`, `dashboard.html:9`, `workspace_detail.html:9` | The h1 class string is copied into 5 templates, and the form-card structure into 3. | Add a `.page-title` component (or an `h1` base rule). Consider a shared form-card base template. | accepted (user, 2026-10-06) |
| Q-21 | Low | `templates/partials/form_body.html:9` | The one-line `{% ifchanged %}` idiom is dense. It prints the required note **before** non-field errors, while CLAUDE.md says "non-field errors first". | Split it over several lines, or accept it and update CLAUDE.md's order description at `/done`. | accepted (user, 2026-10-06) |
| Q-22 | Low | `MASTER.md:339`, `:344`; plan `:447` | Docs and code disagree: MASTER says body copy is 1.625 line-height (code uses `leading-normal`) and a spacing scale of 1/2/3/4/6/8/12 (templates also use 0.5/1.5/2.5/5); the build notes list yet another scale. | Bring MASTER and the notes into line with the code, or the code with MASTER. | accepted (user, 2026-10-06) |
| Q-23 | Low | plan `:85` vs `base.html:15-47`, `:66-77` | "Differences from the plan text" is incomplete. It's missing the `link`, `ink-soft`, `subtle` and `danger` tokens, the `-border` → `-line` rename for the message tokens, the `.link`, `.nav-link` and `.form-note` components, and the body `leading-normal` instead of `leading-relaxed`. | Add them to the list. | fixed |
| Q-24 | Low | `templates/base.html:7` with the `wrap-anywhere` uses | `wrap-anywhere` needs Tailwind 4.1+, but the CDN tag `@4` is unpinned. | Pin `@4.1` or later, or record it for the DevOps step that replaces the Play CDN. | accepted (user, 2026-10-06) |
| Q-25 | Low | `core/tests/test_ui.py:451-459` | The Q-11 override test only checks that `btn-primary` and `w-full` appear together. `w-full` overrides nothing `.btn-*` sets, so the layer fix isn't actually exercised. | Accept it as a limit of HTML tests and note it, or record a manual check with a conflicting utility (e.g. `px-6`). | accepted (user, 2026-10-06) |
| Q-26 | Low | `core/tests/test_ui.py:199-207`, `:391`, `:337` | Small brittleness points: `apply_rules` only parses one-line rules; the 3-digit hex check would flag an anchor like `#add`; `DesignSystemDocumentTests` uses `TestCase` without touching the database. | Require a colour context for the hex check, and use `SimpleTestCase` for the document tests. | accepted (user, 2026-10-06) |

**For `/done`:** the quality reviewer flagged CLAUDE.md text this step makes stale:
- the Templates note "step 01 pages haven't moved to them yet";
- the Q-11 known limitation (now resolved);
- the form_body order (see Q-21);
- the missing tokens, layers, icons, help/error IDs and design-system precedence;
- the "Steps landed" entry for 03.

**Result:** High 1 · Medium 6 · Low 8. **One High (Q-12) is open, so the
status stays `built`.**


### 2026-10-06: recheck after review fixes (security-reviewer + quality-reviewer)

**Scope:**
- Q-12 to Q-18 and Q-23;
- the files under "Review fixes" in Files changed: `base.html`, MASTER.md, `pages/*.md`, `core/tests/test_ui.py` and this plan's build notes.

**Security: no findings.**
- The fixes are CSS classes and documentation only.
- The nav username is still escaped.
- Logout is still POST with CSRF.
- No new scripts or resources.
- Views, URLs, models and forms are untouched.
- No secrets in the docs.

**Quality: all eight fixes confirmed resolved**, each with file:line evidence:
- **Q-12:** equal specificity (0,2,1), later in the same layer, and the test proves it.
- **Q-13:** `outline-hidden` gives a visible outline under forced-colors in Tailwind v4.0+.
- **Q-14:** the span can shrink and wrap inside the flex-wrap nav.
- **Q-15 to Q-18 and Q-23:** the records are accurate. Q-18 is "mostly", see Q-27 and Q-28.

The fixes added no High or Medium issues. They added six Low documentation and consistency items, numbered here after Q-26:

| ID | Sev | file:line | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| Q-27 | Low | `design-system/project-management-system/MASTER.md:5-7` | The generated "LOGIC" banner, right under the new precedence note, still says page files override MASTER and gives the wrong path (`design-system/pages/…`). The page files got a path correction; MASTER didn't. | Add the same one-line path and precedence correction under MASTER's precedence note. | accepted (user, 2026-10-06, at /done) |
| Q-28 | Low | `MASTER.md:378` | "see the dashboard row in the table above". There are now two override rows (auth/workspace and dashboard). | Change it to "see the page-override rows in the table above". | accepted (user, 2026-10-06, at /done) |
| Q-29 | Low | `MASTER.md:368`; comment at `templates/base.html:51` | The stated reason for repeating the ring on `.btn-*` is wrong for Tailwind v4: shadow and ring utilities combine through variables, so the repetition is just redundant. "outline-hidden keeps a transparent outline" is imprecise: the transparent outline exists only under forced-colors. The behaviour is correct. | Reword it as "redundant with the base rule, kept as belt-and-braces" (or drop it in a later step). Describe `outline-hidden` precisely. | accepted (user, 2026-10-06, at /done) |
| Q-30 | Low | plan, target-size table, auth cross-links row | The row says "about 24px tall" in the size column and "about 25px" in the result column. | Use one figure (about 25px) in both cells. | accepted (user, 2026-10-06, at /done) |
| Q-31 | Low | plan, full-review "Result" line | Still reads "One High (Q-12) is open, so the status stays `built`", which is stale now that Q-12 is fixed. | Superseded by this entry's result line. No further change needed. | closed (superseded by the recheck result line) |
| Q-32 | Low (optional) | `templates/base.html:51`, `:75`; `core/tests/test_ui.py:183-196` | The new notes are CSS comments, so they ship in every page's HTML with internal review IDs, while the header note uses `{% comment %}`. `css_block()` doesn't strip comments, so a future comment containing a brace would break its brace matching. | Switch the notes to `{% comment %}`, or have `css_block` strip comments first. | accepted (user, 2026-10-06, at /done) |

**Result:** High 0 · Medium 0 · Low 6 (new). Q-12, the only High, is
fixed, so **no High findings are open and the status is `reviewed`**.
Q-31 is closed by this result line.
