---
step: 01
slug: user-authentication
status: done
created: 2026-10-01
approved: 2026-10-01
---

# 01 — User authentication

## Goal
People can create an account, sign in and sign out. Once signed in, they reach
a simple personal dashboard that anonymous visitors cannot see.

## Context / why now
Nothing exists yet. This is the first step, so it also sets up the application
these features run in. Every later feature (projects, tasks, members) needs to
know who the current user is and needs to keep anonymous visitors out, so
authentication has to come first. Getting the "who are you" and "you can't see
this" behaviour right now gives every later step a tested pattern to follow.

## User stories
- As a visitor, I want to register with a username, email and password, so
  that I have my own account.
- As a registered user, I want to log in and log out, so that only I can use
  my account on a shared computer.
- As a logged-in user, I want a dashboard as my starting point, so that I have
  a home page once I'm signed in.
- As a visitor who follows a link to a protected page, I want to be sent to
  login and then returned to that page, so that I don't lose my place.
- As any user, I want the navigation to show only actions that make sense for
  me right now, so that I'm never offered "Log in" while already logged in, or
  the reverse.

## Acceptance criteria

### Registration
- **AC-1** Given an anonymous visitor, when they open the registration page,
  then they see a form asking for username, email, password and password
  confirmation.
- **AC-2** Given valid details, when the visitor submits the registration form,
  then an account is created, they are logged in, they land on the dashboard,
  and they see a confirmation message.
- **AC-3** Given a username that is already taken, compared without regard to
  letter case (for example "alice" when "Alice" exists), when the visitor
  submits, then no account is created and the form shows an error on the
  username field.
- **AC-4** Given an email address that another account already uses, compared
  without regard to letter case, when the visitor submits, then no account is
  created and the form shows an error on the email field.
- **AC-5** Given a missing required field, an invalid email format, or password
  and confirmation that don't match, when the visitor submits, then no account
  is created and each problem is shown next to the relevant field.
- **AC-6** Given a weak password (too short, too common, all numbers, or too
  similar to the username or email), when the visitor submits, then no account
  is created and the form explains why the password was rejected.
- **AC-7** Given a submission that failed, when the form is shown again, then
  the username and email the visitor typed are kept, and both password fields
  are empty.

### Login
- **AC-8** Given an anonymous visitor, when they open the login page, then they
  see a form asking for username and password, and a link to the registration
  page.
- **AC-9** Given a registered username and its correct password, when the user
  logs in, then they are logged in and land on the dashboard. The username is
  matched without regard to letter case: an account registered as "Alice" can
  log in by typing "alice", "ALICE" or "Alice". The password is always
  case-sensitive. Logging in does not change the casing stored for the
  username; it stays as the user chose it when registering.
- **AC-10** Given a wrong password or an unknown username, when the user
  submits, then they stay logged out and see a single generic error. The error
  does not say which of the two was wrong, and the username they typed is kept.
- **AC-11** Given an account that has been deactivated, when its owner submits
  correct credentials, then they are not logged in.

### Logout
- **AC-12** Given a logged-in user, when they choose "Log out" from the
  navigation, then they are logged out, taken to the login page, and see a
  message confirming they logged out.
- **AC-13** Given a logged-in user, when a log-out request arrives as a simple
  link visit or page load instead of the logout action, then the user is
  **not** logged out. This stops another site from logging people out.

### Dashboard and protected pages
- **AC-14** Given a logged-in user, when they open the dashboard, then they see
  a page that greets them by username, using the casing they chose at
  registration no matter how they typed it at login.
- **AC-15** Given an anonymous visitor, when they request the dashboard (or any
  other protected page), then they are redirected to the login page, and that
  redirect remembers the page they asked for.
- **AC-16** Given a visitor who was redirected to login from a protected page,
  when they log in successfully, then they land on the page they originally
  asked for instead of the dashboard.
- **AC-17** Given a login request whose "return to" destination points to
  another website, when the user logs in successfully, then they land on the
  dashboard and not on the external site.
- **AC-18** Given a logged-in user, when they open the login or registration
  page, then they are redirected to the dashboard.
- **AC-19** Given anyone, when they open the site's root address, then a
  logged-in user lands on the dashboard and an anonymous visitor lands on the
  login page.

### Navigation
- **AC-20** Given an anonymous visitor on any page, then the navigation shows
  "Log in" and "Register" and shows neither "Dashboard" nor "Log out".
- **AC-21** Given a logged-in user on any page, then the navigation shows their
  username (with the casing they chose at registration), "Dashboard" and
  "Log out", and shows neither "Log in" nor "Register".

### Safety
- **AC-22** Given any registered account, then its password is never stored
  or displayed in readable form. Logging in with the original password works,
  and the stored value is not the password itself.
- **AC-23** Given a registration, login or logout form submitted from outside
  the site (without the site's anti-forgery token), then the request is
  rejected and has no effect.

## Out of scope
- User roles or permissions (admin vs. member, project owner, and so on)
- Profile viewing or editing, avatars, changing username or email
- Changing a password, password reset, "forgot password" emails
- Email verification, or sending any email at all
- Social login (Google, GitHub, …), two-factor authentication, "remember me"
- Limiting login attempts or locking accounts after failed attempts
- Account deletion and self-deactivation (AC-11 only covers accounts already
  deactivated by an administrator)
- Projects, tasks, teams, members, or any dashboard content beyond the greeting
- Visual design beyond a clean, readable layout that stays consistent across
  the pages

## Decisions
These were open questions. The user accepted the proposed answers on
2026-10-01.

- **OQ-1** Registration logs the new user straight in → AC-2.
- **OQ-2** Email addresses are unique across accounts, ignoring letter case.
  Future password reset by email relies on this → AC-4.
- **OQ-3** Users log in with their username only, not their email → AC-8, AC-9.
- **OQ-4** An anonymous visitor at the site root is sent to the login page. A
  public landing page can come in a later step → AC-19.
- **OQ-5** Usernames are unique ignoring letter case. Login matches the
  username ignoring letter case, and the casing chosen at registration is
  always the one displayed → AC-3, AC-9, AC-14, AC-21.

## Open questions
- (none)

No new dependencies are needed. Everything above can be built with what
CLAUDE.md already allows.
