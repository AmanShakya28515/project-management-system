---
step: 03
slug: ui-refresh
status: done
created: 2026-10-05
approved: 2026-10-05
---

# 03 — UI refresh

## Goal
Every existing page looks and behaves like part of one coherent, accessible
product. The pages are the navigation, messages, login, registration,
dashboard, create workspace, and workspace detail with member management.
Nothing the app *does* changes.

## Context / why now
Steps 01 and 02 delivered working authentication and workspaces, with 140
passing tests. The step 01 pages were styled by hand. The step 02 pages used
only part of the ui-ux-pro-max guidance. The result is visible
inconsistencies, such as focus rings on some buttons and not others, and
different button sizes. Step 02's review deferred one finding here (Q-11):
the shared button styles can't be adjusted per page, and the sizes differ.

CLAUDE.md now requires the skill's **full** workflow for UI work. That
workflow uses a design system saved in the project, focused guidance per
page, and the skill's pre-delivery checklist. Doing this before projects and
tasks arrive means those pages start from a finished design system instead
of copying today's mix.

## User stories
- As any visitor, I want every page to look like it belongs to the same
  product, so that the app feels trustworthy and easy to learn.
- As a keyboard or screen-reader user, I want to reach, understand and
  operate every page without a mouse, so that I can use the app fully.
- As a phone user, I want every page to fit my screen without sideways
  scrolling, so that I can use the app on the go.
- As a user filling in a form, I want clear labels, clear required fields and
  errors next to the field, so that I can fix mistakes quickly.
- As a future contributor, I want a written design system, so that new pages
  (projects, tasks) match without guesswork.

## Acceptance criteria

### Design system and process
- **AC-1** Given this step is finished, then a design-system document for the
  project exists in the location CLAUDE.md requires. It was produced by the
  skill's design-system workflow, and states at least:
  - the colour palette, built on the existing indigo and slate identity, with
    the text and background pairs it allows;
  - the system font stack and the type scale;
  - spacing and corner-radius rules;
  - button, form-field, card, message and badge styles;
  - focus-indicator rules.
- **AC-2** Given the build notes for this step, then for each page they record
  which design-system rules and which focused guidance (UX, colour,
  typography, forms, navigation, empty states, implementation) shaped it. They
  also confirm the skill's pre-delivery checklist was completed, listing each
  item as passed, or as not applicable with a reason.

### Consistency
- **AC-3** Given any page, then it uses the same header and navigation, page
  width, card style, heading sizes, spacing scale and colour palette as every
  other page, as the design system defines them.
- **AC-4** Given any primary or secondary button or button-styled link
  anywhere in the app, then all primary buttons share one base size and look,
  and so do all secondary buttons, including the navigation's "Register" and
  "Log out". Where a page deliberately changes one property, such as making
  a button full width, that change takes effect, and the button otherwise
  keeps the shared look (resolves Q-11).
- **AC-5** Given any page, then text uses a system font stack, and no font is
  downloaded from anywhere. Body text is at least 16px, with comfortable line
  spacing.

### Navigation
- **AC-6** Given an anonymous visitor or a signed-in user, then the navigation
  offers exactly the same items as before:
  - **Anonymous:** "Log in" and "Register".
  - **Signed in:** their username, "Dashboard", and "Log out" as a form
    submission.
  - **Both:** the site name links home.
- **AC-7** Given a user on a page that has a navigation link (dashboard,
  login, register), then that link is marked as the current page, both
  visually and for assistive technology.
- **AC-8** Given any page, when a keyboard user presses Tab once, then the
  first focused element is a "Skip to main content" link. Activating it moves
  focus to the page's main content. The link is visible while it has focus.
- **AC-9** Given a screen width as narrow as 320px, then every navigation
  item can still be seen and used. Nothing scrolls sideways, and no added
  JavaScript is needed (see OQ-3).

### Messages
- **AC-10** Given a confirmation message (for example after registering,
  logging out, creating a workspace or adding a member), then:
  - its text is **exactly** the same as today;
  - it is shown in the design system's style for its kind (success,
    information, warning or error);
  - its kind is shown by the visual design, a matching icon, and, where
    needed, an accessible indication of the kind for assistive technology,
    so the meaning never depends on colour alone;
  - it is announced to screen-reader users without moving their focus;
  - no dismiss button or other new interaction is added.

### Forms
These are the login, registration, create-workspace and add-member forms.
- **AC-11** Given any form, then every field has a visible label, and
  required fields are marked consistently. Any help text appears with its
  field and is linked to it for assistive technology. This includes the
  password rules on registration.
- **AC-12** Given a submitted form with errors, then each error appears next
  to its field. The field is visibly marked as invalid and is announced as
  invalid and linked to its error message for assistive technology. Errors
  that belong to no single field appear above the fields.
- **AC-13** Given any form, then each field has the right input type and
  autofill hint (username, email, new password, current password), and the
  submit button says what it does ("Log in", "Create account", "Create
  workspace", "Add member").

### Pages
- **AC-14** Given the login and registration pages, then each shows a single
  centred card. Each links clearly to the other ("Register" and "Log in").
- **AC-15** Given the dashboard, then it shows:
  - the greeting;
  - a clearly visible "Create workspace" action;
  - the user's workspaces as distinct, easy-to-scan items.

  When the user has no workspaces, the empty state contains its own message
  and its own "Create workspace" call to action.
- **AC-16** Given a workspace page, then it shows:
  - the workspace name prominently, with a way back to the dashboard;
  - the member count;
  - each member with an "Owner" or "Member" label, told apart by text and
    not only by colour;
  - for the owner only, a clearly separated "Add a member" section.
- **AC-17** Given the create-workspace page, then it shows the form in a card
  with a primary "Create workspace" button and a secondary "Cancel" that goes
  back to the dashboard.

### Accessibility
- **AC-18** Given any page, then:
  - the page declares its language;
  - it has a unique, descriptive browser title;
  - it has exactly one main heading;
  - its headings never skip a level;
  - it has a main content region and a labelled navigation region.
- **AC-19** Given any link, button or form field, then a clearly visible focus
  indicator appears when it is reached by keyboard.
- **AC-20** Given any text or interface element, then its colour contrast
  meets WCAG 2.2 AA: 4.5:1 for normal text, 3:1 for large text and for
  interface parts and focus indicators. The design system lists the colour
  pairs used, with their ratios.
- **AC-21** Given any clickable or tappable element, then its target is at
  least 24 by 24 CSS pixels, or the gap around it meets the WCAG 2.2 AA
  target-size exception.
- **AC-22** Given a user whose system asks for reduced motion, then no
  transition or animation plays for them.

### Responsive layout
- **AC-23** Given screen widths of 320px, 768px and 1280px, then on every
  page:
  - nothing scrolls sideways;
  - text stays readable without zooming;
  - forms fill the available width on small screens;
  - long workspace names and usernames wrap instead of overflowing.

### Behaviour and constraints preserved
- **AC-24** Given the finished step, then every authentication, workspace,
  access-control, validation and membership behaviour from steps 01 and 02 is
  unchanged. All existing tests pass. An existing test may be changed only
  under the rule in OQ-7.
- **AC-25** Given any page, then the only script loaded from another site is
  the existing styling script. No external stylesheets, fonts, icon libraries
  or new JavaScript are loaded. Any icons are drawn directly in the page
  (inline SVG). Decorative icons are hidden from assistive technology, and
  icons that carry meaning have a text alternative.
- **AC-26** Given any form, then it still carries the site's anti-forgery
  token, and logging out still requires a form submission. User-supplied text
  (workspace names, usernames, messages) is still displayed as plain text.

## Out of scope
- Any new product feature, page or URL, including projects and tasks
- Any change to authentication, workspace, membership or access-control
  behaviour, validation rules or message wording
- New backend functionality of any kind
- New dependencies, external font loading (Google Fonts or similar), and
  icon libraries
- Animations or interactions that need new JavaScript, such as dismissible
  messages, mobile menus that open and close, or client-side validation
- Dark mode (see OQ-1)
- Changing the base identity to an unrelated palette. Indigo and slate stay
  the foundation.
- Fixing the accepted step 02 findings S-3 and S-4 (product decisions for
  later specs)

## Decisions
These were open questions. The user accepted the proposed answers on
2026-10-05.

- **OQ-1 Dark mode.** It could follow the system setting with no JavaScript,
  but it doubles every colour pair to design, check for contrast and review.
  Decision: leave it out of this step. The design system may note how dark
  mode would map later.
- **OQ-2 Message kinds.** The app only produces success and information
  messages today. The design system defines all four kinds
  (success, information, warning, error), so later steps have them ready.
  This step only shows the two that exist. No dismiss button, because that
  would need JavaScript. → AC-10
- **OQ-3 Small-screen navigation.** No hamburger menu, because
  opening and closing it would need JavaScript. There are at most four items,
  and they stay visible and wrap or stack neatly at narrow widths. → AC-9
- **OQ-4 Skip link and current-page marker.** Add both. They are
  standard accessibility patterns and change no behaviour. → AC-7, AC-8
- **OQ-5 Required-field marking.** Every field on the current forms is
  required. Still mark required fields consistently (for example
  with an asterisk explained once per form), so the pattern is ready for
  forms that have optional fields. → AC-11
- **OQ-6 Design-system document.** It lives in the project
  alongside the code, as documentation. It is not a dependency, and it is
  updated only through approved steps. → AC-1
- **OQ-7 Tests that assert on markup.** A redesign can break tests that check
  page structure rather than behaviour. For example, one step 02 test helper
  (Q-9) reads member rows from the HTML. Decision:
  - such a test may be updated by `test-author`, but only to keep checking
    the **same behaviour**;
  - each changed test is listed in the build notes and checked at review;
  - no assertion about behaviour may be removed or weakened.

  New tests are added for this step's acceptance criteria wherever the
  result can be seen in the page's HTML. → AC-24

## Open questions
- (none)

No new dependencies are needed. Everything above can be built with what
CLAUDE.md already allows.
