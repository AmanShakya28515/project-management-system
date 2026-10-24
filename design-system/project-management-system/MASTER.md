# Design System Master File

> **PRECEDENCE (read first).** The approved **"Project adjustments (step 03)"** section at the end of `design-system/project-management-system/MASTER.md` overrides **everything else** in MASTER.md and in every `pages/*.md` file. Where the generated text below disagrees (for example Google Fonts / Plus Jakarta Sans, the GSAP scroll reveal, the emerald CTA button, lavender cards, hover lifts, the landing-page pattern, or the 1200px/1400px and grid page widths), follow the Project adjustments. The generated text is kept only as a record of the skill's output (review finding Q-18).

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Project Management System
**Generated:** 2026-10-05 22:44:04
**Category:** Micro SaaS
**Design Dials:** Variance 3/10 (Centered / Minimal) | Motion 2/10 (Subtle) | Density 5/10 (Standard)

---

## Global Rules

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#6366F1` | `--color-primary` |
| On Primary | `#000000` | `--color-on-primary` |
| Secondary | `#818CF8` | `--color-secondary` |
| On Secondary | `#0F172A` | `--color-on-secondary` |
| Accent/CTA | `#059669` | `--color-accent` |
| On Accent/CTA | `#000000` | `--color-on-accent` |
| Background | `#F5F3FF` | `--color-background` |
| Foreground | `#1E1B4B` | `--color-foreground` |
| Card | `#FFFFFF` | `--color-card` |
| Card Foreground | `#1E1B4B` | `--color-card-foreground` |
| Muted | `#EBEFF9` | `--color-muted` |
| Muted Foreground | `#475569` | `--color-muted-foreground` |
| Border | `#E0E7FF` | `--color-border` |
| Destructive | `#DC2626` | `--color-destructive` |
| On Destructive | `#FFFFFF` | `--color-on-destructive` |
| Ring | `#6366F1` | `--color-ring` |

**Color Notes:** Indigo primary + emerald CTA [Accent adjusted from #10B981]

### Typography

- **Heading Font:** Plus Jakarta Sans
- **Body Font:** Plus Jakarta Sans
- **Mood:** friendly, modern, saas, clean, approachable, professional
- **Google Fonts:** [Plus Jakarta Sans + Plus Jakarta Sans](https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
```

### Spacing Variables

*Density: 5/10 — Standard*

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |
| `--space-3xl` | `64px` / `4rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #059669;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #6366F1;
  border: 2px solid #6366F1;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: #F5F3FF;
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #6366F1;
  outline: none;
  box-shadow: 0 0 0 3px #6366F120;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Minimalism & Swiss Style

**Keywords:** Clean, simple, spacious, functional, white space, high contrast, geometric, sans-serif, grid-based, essential

**Best For:** Enterprise apps, dashboards, documentation sites, SaaS platforms, professional tools

**Key Effects:** Subtle hover (200-250ms), smooth transitions, sharp shadows if any, clear type hierarchy, fast loading

### Page Pattern

**Pattern Name:** Trust & Authority + Conversion

- **Conversion Strategy:** Security badges. Case studies. Transparent pricing. Low-friction form. Provide pause/stop and stop the logo carousel on focus, hover, and reduced motion. Previous/next controls provide the keyboard equivalent; pause offscreen/hidden and render a static logo set under reduced motion.
- **CTA Placement:** Contact Sales / Get Quote (primary) + Nav
- **Section Order:** Hero (mission/credibility) > Proof (logos, certs, stats) > Solution overview > Clear CTA path

---

## Motion

**Scroll Reveal** (Subtle) — Trigger: scroll (viewport enter) | Duration: 300-400ms | Easing: `power1.out`

```js
gsap.from(el, { opacity: 0, y: 12, duration: 0.35, ease: 'power1.out', scrollTrigger: { trigger: el, start: 'top 90%', toggleActions: 'play none none reverse' } });
```

**Framework notes:** Requires the ScrollTrigger plugin registered once via gsap.registerPlugin(ScrollTrigger); Use matchMedia('(prefers-reduced-motion: reduce)') to skip non-essential motion and render the final state immediately

- ✅ Keep the y offset small (8-16px) so it reads as a fade, not a slide
- ❌ Don't reveal below-the-fold content needed for SEO/crawlers as invisible-by-default without a no-JS fallback
- ⚡ toggleActions 'play none none reverse' avoids re-triggering on every scroll direction change

---

## Anti-Patterns (Do NOT Use)

- ❌ Static design
- ❌ No video
- ❌ Poor mobile

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile

---

## Project adjustments (step 03)

> **These rules override the generated sections above and every `pages/*.md` file.** The generated
> output conflicted with spec 03 (no external fonts, no new JavaScript, keep
> the indigo/slate identity) and in places with WCAG 2.2 AA. Each change
> below gives its reason. They were recorded in plan 03 and approved with
> it. Change them only through an approved step.

### Changes to the generated output

| Generated | Adjusted to | Reason |
|---|---|---|
| Primary `#6366F1` with "on primary" `#000000` | Primary **`#4F46E5`** (indigo-600) with **white** text | White on `#6366F1` is 4.47:1, which fails AA for normal text. White on `#4F46E5` is 6.29:1. `#6366F1` stays as the **focus-ring** colour, where 3:1 is enough. |
| Accent/CTA emerald `#059669` on primary buttons | Buttons stay **indigo**. Emerald tones are used **only** for the success message kind. | Spec 03 keeps indigo/slate as the identity. Two competing CTA colours would weaken the hierarchy. |
| Background `#F5F3FF` (lavender); cards `#F5F3FF` | Canvas **`#F8FAFC`** (slate-50); cards **white** with a slate-200 border | Keeps the existing look, and white cards separate clearly from the canvas. |
| Plus Jakarta Sans from Google Fonts | **System font stack** (below) | Spec 03 AC-5: no external fonts. |
| `transition: all`, `translateY` hover lift on buttons and cards, `cursor:pointer` on cards | Colour-only transitions, 150ms, `motion-safe:` only. No movement. `cursor-pointer` only on real controls. | The generated anti-patterns forbid layout-shifting hovers. Cards here aren't clickable. Spec 03 AC-22 covers reduced motion. |
| GSAP scroll reveal | **None** | Spec 03: no new JavaScript. Content is visible immediately. |
| "Trust & Authority + Conversion" landing pattern (hero, logos, pricing) | Not used | This is a signed-in application with forms and lists, not a marketing page. |
| Inputs: border `#E2E8F0`, 12/16px padding | Border **`#64748B`** (border-strong), `min-h-11`, `px-3` | `#E2E8F0` is 1.23:1 against white, but WCAG 1.4.11 needs 3:1 for a control's boundary. Inputs share the 44px button height. |
| Toast "auto-dismiss after 3–5 s" (ux search) | Messages stay until the next page | Auto-dismissing needs JavaScript (excluded), and timed content is an accessibility risk anyway. |
| "Show/hide password toggle" (ux search) | Not added | Needs JavaScript (excluded by spec 03). The password field still allows paste and password managers. |
| "Focusable error summary" (ux search) | Inline errors linked to their field. Non-field errors appear in a box above the fields. No focus move. | Moving focus needs JavaScript (excluded). Inline errors connected by `aria-describedby` satisfy the core rule. |
| "Smooth scroll for anchor links" (ux search) | Not used | It's motion. The skip link should jump instantly, and reduced-motion users must never get it. |
| Auth and workspace page overrides: Max Width 1200px, responsive grid | Same `max-w-5xl` page width as every page. Auth and create-workspace use a centred `max-w-md` card, and workspace detail is a single column | One width keeps the product consistent (spec 03 AC-3). A narrow form card is easier to scan than a 1200px grid, and these pages have no grid content. |
| Dashboard page override: 1400px or full width, 12-column grid, high density | Same `max-w-5xl` width as every page, single-column list | The dashboard is a short list today. One width keeps the product consistent (spec 03 AC-3). Revisit when projects and tasks add data views. |

### Semantic tokens

They are defined once, in the base template's `@theme` block, as the
utilities `bg-*`, `text-*`, `border-*` and `ring-*`. Never write raw hex
values in templates.

| Token | Hex | Use |
|---|---|---|
| `--color-primary` | `#4F46E5` | Primary buttons, current-page marker |
| `--color-primary-hover` | `#4338CA` | Primary button hover |
| `--color-on-primary` | `#FFFFFF` | Text on primary |
| `--color-link` | `#4338CA` | Text links |
| `--color-ink` | `#0F172A` | Headings and body text |
| `--color-ink-soft` | `#334155` | Secondary emphasis, secondary-button text |
| `--color-muted` | `#475569` | Supporting text, help text |
| `--color-canvas` | `#F8FAFC` | Page background |
| `--color-surface` | `#FFFFFF` | Cards, header, inputs |
| `--color-subtle` | `#F1F5F9` | Hover backgrounds |
| `--color-line` | `#E2E8F0` | Decorative card and divider borders |
| `--color-line-strong` | `#64748B` | Control boundaries (inputs, secondary buttons) |
| `--color-ring` | `#6366F1` | Focus ring |
| `--color-danger` | `#B91C1C` | Field error text, required mark, invalid border |
| `--color-success-fg` / `-bg` / `-line` | `#065F46` / `#ECFDF5` / `#A7F3D0` | Success messages |
| `--color-info-fg` / `-bg` / `-line` | `#075985` / `#F0F9FF` / `#BAE6FD` | Information messages |
| `--color-warning-fg` / `-bg` / `-line` | `#92400E` / `#FFFBEB` / `#FDE68A` | Warning messages (defined for later steps) |
| `--color-danger-fg` / `-bg` / `-line` | `#991B1B` / `#FEF2F2` / `#FECACA` | Error messages, non-field form errors |
| `--color-owner-fg` / `-bg` | `#3730A3` / `#EEF2FF` | "Owner" badge |
| `--color-member-fg` / `-bg` | `#334155` / `#F1F5F9` | "Member" badge |

The border tokens are named `line` and `line-strong`, not `border`, so the
utilities read `border-line` and `border-line-strong` rather than the
confusing `border-border`.

### Contrast (WCAG 2.2 AA)

Computed with the WCAG relative-luminance formula on the exact hex values
above. A test recomputes these from the template's tokens (spec 03, AC-20).

| Pair (text or UI on background) | Hex | Ratio | Needs | Result |
|---|---|---|---|---|
| ink on canvas | `#0F172A` / `#F8FAFC` | 17.06:1 | 4.5:1 | pass |
| ink on surface | `#0F172A` / `#FFFFFF` | 17.85:1 | 4.5:1 | pass |
| ink-soft on surface | `#334155` / `#FFFFFF` | 10.35:1 | 4.5:1 | pass |
| muted on surface | `#475569` / `#FFFFFF` | 7.58:1 | 4.5:1 | pass |
| muted on canvas | `#475569` / `#F8FAFC` | 7.24:1 | 4.5:1 | pass |
| link on surface | `#4338CA` / `#FFFFFF` | 7.90:1 | 4.5:1 | pass |
| link on canvas | `#4338CA` / `#F8FAFC` | 7.55:1 | 4.5:1 | pass |
| link on subtle (row hover) | `#4338CA` / `#F1F5F9` | 7.21:1 | 4.5:1 | pass |
| on-primary on primary | `#FFFFFF` / `#4F46E5` | 6.29:1 | 4.5:1 | pass |
| on-primary on primary-hover | `#FFFFFF` / `#4338CA` | 7.90:1 | 4.5:1 | pass |
| ink-soft on subtle | `#334155` / `#F1F5F9` | 9.45:1 | 4.5:1 | pass |
| danger on surface | `#B91C1C` / `#FFFFFF` | 6.47:1 | 4.5:1 | pass |
| success-fg on success-bg | `#065F46` / `#ECFDF5` | 7.29:1 | 4.5:1 | pass |
| info-fg on info-bg | `#075985` / `#F0F9FF` | 7.09:1 | 4.5:1 | pass |
| warning-fg on warning-bg | `#92400E` / `#FFFBEB` | 6.84:1 | 4.5:1 | pass |
| danger-fg on danger-bg | `#991B1B` / `#FEF2F2` | 7.60:1 | 4.5:1 | pass |
| owner badge (owner-fg on owner-bg) | `#3730A3` / `#EEF2FF` | 8.88:1 | 4.5:1 | pass |
| member badge (member-fg on member-bg) | `#334155` / `#F1F5F9` | 9.45:1 | 4.5:1 | pass |
| line-strong on surface (control boundary) | `#64748B` / `#FFFFFF` | 4.76:1 | 3:1 | pass |
| ring on surface (focus) | `#6366F1` / `#FFFFFF` | 4.47:1 | 3:1 | pass |
| ring on canvas (focus) | `#6366F1` / `#F8FAFC` | 4.27:1 | 3:1 | pass |
| primary on surface (button boundary) | `#4F46E5` / `#FFFFFF` | 6.29:1 | 3:1 | pass |

### Typography

- **Font stack:** `ui-sans-serif, system-ui, -apple-system, "Segoe UI",
  Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif`. Nothing is
  downloaded.
- **Scale:**
  - 12px for badges only;
  - 14px (`text-sm`) for UI text: labels, nav, buttons, help text;
  - 16px (`text-base`) for body text;
  - 18px for `h2`;
  - 24px, rising to 30px at `sm` and up, for `h1`.
- **Weights:** 400 body, 500 labels and nav, 600 buttons and `h2`, 700 `h1`.
- **Line height:** 1.5 for UI text, 1.625 for body copy. Use unitless line
  heights so text reflows.

### Spacing, radius and layout

- **Spacing:** a 4px base. Use 4/8/12/16/24/32/48 (Tailwind `1/2/3/4/6/8/12`).
  Leave at least 8px (`gap-2`) between adjacent targets.
- **Radius:**
  - `rounded-lg` (8px) for buttons and inputs;
  - `rounded-2xl` (16px) for cards;
  - `rounded-full` for badges.
- **Layout:**
  - one content width, `max-w-5xl`, with gutters `px-4 sm:px-6`;
  - form pages use a centred `max-w-md` card;
  - user content (workspace names, usernames) wraps with `wrap-anywhere`
    inside `min-w-0` flex children.

### Components

| Component | Rule |
|---|---|
| **Buttons** | `.btn-primary` and `.btn-secondary` in `@layer components`, so page utilities override them (Q-11). Shared base: `inline-flex`, centred, `gap-2`, `rounded-lg`, `px-4`, **`min-h-11` (44px)**, `text-sm`, `font-semibold`, `cursor-pointer`, a `motion-safe` 150ms colour transition, and the focus ring. Primary: `bg-primary text-on-primary hover:bg-primary-hover`. Secondary: `bg-surface text-ink-soft border border-line-strong hover:bg-subtle`. One size everywhere, the nav included. |
| **Cards** | `.card`: `bg-surface`, `border border-line`, `rounded-2xl`, `shadow-sm`, padding `p-6 sm:p-8`. Not clickable and no hover effect. |
| **Form fields** | Label above, 14px, weight 500. A required field shows a danger-coloured `*`, hidden from screen readers because the input's `required` attribute announces it. One "* Required field" note per form. Input: `min-h-11`, `px-3`, `border-line-strong`, `rounded-lg`, focus ring. Help text in muted 14px with `id="<field>_helptext"`. Errors in danger 14px with an `x-circle` icon and `id="<field>_error"`. Invalid inputs (`aria-invalid="true"`) get a danger border. The invalid rule targets `input`, `select` and `textarea` with the same specificity as the normal field rule, and comes after it, so it wins (review Q-12). There's no danger ring, because a component-layer ring would replace the focus ring. |
| **Messages** | `.msg` plus `.msg-success`, `.msg-info`, `.msg-warning` or `.msg-error`: a tinted background, a border and fg colours from the tokens, with a matching icon (`check-circle`, `information-circle`, `exclamation-triangle`, `x-circle`) and a visually hidden kind word ("Success:", "Information:", "Warning:", "Error:"). The wrapper has `role="status"`. The message text itself is never changed. No dismiss button. |
| **Badges** | `.badge`: `rounded-full`, `px-2.5`, `py-0.5`, 12px, weight 500, `whitespace-nowrap`, `shrink-0`. `.badge-owner` and `.badge-member` use the badge tokens. The text, not the colour, carries the meaning. |
| **Focus** | Every focusable element shows `ring-2 ring-ring ring-offset-2` on `:focus-visible`, through `@layer base` for plain elements. The button classes repeat it **deliberately**, so a button keeps its ring even if a page adds its own shadow utility. Always use `outline-hidden`, never `outline-none`: Tailwind v4's `outline-hidden` keeps a transparent outline, which Windows forced-colors (High Contrast) mode draws visibly after it removes box-shadow rings (review Q-13). Never remove an outline without replacing it. |
| **Navigation** | `<header>` holds `<nav aria-label="Main">`. The current page gets `aria-current="page"`, with primary text and a 2px primary underline. Items wrap below the brand at narrow widths. No hamburger, because that needs JavaScript. Nav links are `min-h-11` with `inline-flex items-center`. |
| **Skip link** | The first focusable element. Visually hidden until it has focus, then shown as a primary pill at top left. It targets `#main` (`<main tabindex="-1">`). |
| **Icons** | Inline SVG copied from Heroicons v2 outline (MIT): 24px viewBox, 1.5 stroke, `currentColor`, `size-5` (or `size-4` in compact text). Always next to visible text, so always `aria-hidden="true" focusable="false"`. One icon family only, and no emoji. |
| **Motion** | Only colour and background transitions, 150ms, behind `motion-safe:`. A `prefers-reduced-motion: reduce` base rule turns off every transition and animation. |
| **Targets** | Buttons and inputs are 44px tall. Nav, back, cancel and row links are at least 44px tall (`min-h-11`). Inline sentence links get `py-1` padding and use WCAG's inline exception. Adjacent targets are at least 8px apart. |

### Page overrides

The generated files in `pages/` are kept for reference. Where they differ
from this section, **this section wins** (see the dashboard row in the table
above). Page-specific choices:

- **auth** (login, register): a centred `max-w-md` card, `h1` plus one line
  of muted supporting text, a full-width primary button (`w-full`, which
  shows Q-11's override working), and a cross-link line underneath.
- **dashboard:** a page header (`h1` greeting, supporting text, primary
  "Create workspace"), then one card with `h2` "Your workspaces", a count,
  full-width row links, and an empty state with its own call to action.
- **workspace** (create, detail):
  - Create uses the auth card pattern with primary and secondary buttons.
  - Detail has a back link, `h1` name, a members card (rows with a user
    icon, name and badge), and the owner-only "Add a member" card.

### Project pages (step 04)

These follow the existing components; no new colours or tokens.

- **Workspace page, projects section:** placed between the page header and
  the members card, because projects are the page's main content.
  - It's a `.card` `<section aria-labelledby="projects-heading">`. The header
    holds a `clipboard-document-list` icon, `h2` "Projects" and a count
    badge.
  - When projects exist, a `.btn-primary` "New project" (`plus` icon) sits on
    the right.
  - Rows are full-width `min-h-11` links (icon, name with `wrap-anywhere`,
    `chevron-right`), sorted alphabetically.
  - The empty state is the dashboard's dashed panel: "No projects yet.", one
    supporting line, and its own `.btn-primary` "New project".
    *(Step 05 changed this from "Create a project", review Q-41.)*

  Only one create button shows at a time, so the action is never duplicated.
- **Create project:** the auth-style centred `max-w-md` card.
  - `h1` "New project", with a muted "in <workspace>" line.
  - Fields: name (required) and "Description (optional)" as a textarea.
  - Buttons: secondary Cancel (back to the workspace page) and primary
    "Create project", stacked on mobile.
- **Project page:** a back link reading "Back to <workspace name>"
  (`arrow-left`, `min-h-11`, the name in its own `wrap-anywhere` span;
  step 05 changed it from the bare workspace name, review Q-40), the `h1`
  name (`wrap-anywhere`), then a `.card` with `h2` "Description".
  - The description is shown with `linebreaksbr`, which escapes first, in a
    `max-w-prose leading-relaxed` paragraph.
  - With no description, a muted "No description".
  - Long text is shown in full and wraps. The skill's "truncate with an
    expand option" advice was **rejected**, because expanding needs
    JavaScript.
- **Icons:** projects use `clipboard-document-list` (Heroicons v2 outline,
  MIT). Workspaces keep `folder`, so the two are easy to tell apart.
- **Textarea:** `.form-field textarea` adds `min-h-28 py-2` on top of the
  shared field rule, in `@layer components`. It has the same border, focus
  and invalid styling as other fields.

### Task pages (step 05)

These follow the step 04 project patterns; no new colours or tokens.

- **Action labels (rule), for projects and tasks:** a link or button that
  **opens** a create form reads "New <thing>" ("New project", "New task"),
  both in a section header and in its empty state. The form's **submit**
  button reads "Create <thing>". Only one create action shows at a time: the
  header one when items exist, the empty-state one otherwise.
  - **Known exception:** workspaces still use step 03's wording. The
    dashboard's buttons say "Create workspace", and the workspace form's
    `h1` says "Create a workspace". Spec 05 kept the dashboard out of scope
    (OQ-7), so it isn't renamed yet; a later UI step can bring it in line
    (review Q-51). Until then, apply the rule only to projects, tasks and new
    item types.
- **Icons:** `list-bullet` (Heroicons v2 outline, MIT) means tasks. The
  meanings are: `folder` = workspace, `clipboard-document-list` = project,
  `list-bullet` = tasks, `check-circle` = success message only.
- **Project page, tasks section:** placed after the Description card.
  - A `.card` `<section aria-labelledby="tasks-heading">`, with a header
    showing `list-bullet`, `h2` "Tasks", a count badge, and "New task" when
    tasks exist.
  - Rows are full-width `min-h-11` links (title with `wrap-anywhere`, then
    `chevron-right`), with **no leading icon**, in creation order, oldest
    first. No dates are shown.
  - The empty state is the dashed panel: "No tasks yet.", one supporting
    line, and its own "New task".
- **Create task:** the centred `max-w-md` card: `h1` "New task", the muted
  line "in <project> · <workspace>", title and "Description (optional)",
  then secondary Cancel (back to the project page) and primary
  "Create task".
- **Task page:** a back link "Back to <project>" (`arrow-left`, `min-h-11`).
  - A muted plain-text location line "<workspace> · <project>" stands in for
    a breadcrumb. The skill advises breadcrumbs from three levels deep; the
    linked breadcrumb is left for a later step, and the back link is the
    way out.
  - Then the `h1` title and a Description `.card` (`linebreaksbr`,
    `max-w-prose`), or "No description".
- **Back links** always read "Back to <destination name>". The project page
  now uses "Back to <workspace>" (changed in step 05, review Q-40).

### Assignee section (step 06)

The task page has an "Assignee" `.card` after Description. It shows the
current assignee (the `user` icon and the username with `wrap-anywhere`, or
a muted "Unassigned"), then a select through `form_body.html` (label
"Assignee", "Unassigned" first) and a `.btn-secondary` "Save assignee".
Existing components only; no new tokens or icons.

### Task status (step 07)

The task page shows a **Status** `.card` beside the Assignee card from `sm`
up (`grid sm:grid-cols-2 gap-6`), stacked on mobile. It holds the current
status badge, a select ("To do", "In progress", "Done") and a
`.btn-secondary` "Save status". Project page task rows show the same badge
before the chevron. The badge is one partial,
`tasks/templates/tasks/partials/status_badge.html`, and always shows the
text label:
- `.badge-status-todo`: member tokens, slate, 9.45:1;
- `.badge-status-progress`: info tokens, 7.09:1;
- `.badge-status-done`: success tokens, 7.29:1.

No new colours.

### Dark mode (not built; spec 03, OQ-1)

When a later step adds it, keep the same semantic token names and redefine
their values under `@media (prefers-color-scheme: dark)`, for example canvas
`#0F172A`, surface `#1E293B`, ink `#F1F5F9`, muted `#CBD5E1`, primary
`#818CF8` with ink text. Recompute every contrast pair; never assume
light-mode results carry over.
