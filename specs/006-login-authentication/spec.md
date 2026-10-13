# Feature Specification: Login Authentication

**Feature Branch**: `006-login-authentication`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Add a login screen to the biweekly-budget Flask app. Users sign in with an email address and password. Follow security best practices for credential handling: passwords stored only as salted, slow adaptive hashes, secure session cookies (HttpOnly, Secure, SameSite), CSRF protection on forms, login rate limiting against brute force, generic error messages that don't reveal whether an email exists, and logout. All existing pages must require authentication. The app is deployed at https://budget.taylorbasso.dev behind an ALB and currently has no authentication; it still stores data in SQLite (a move to Aurora Postgres is a separate, later feature)."

**Scope note**: this is a hobby app (Constitution v3.1.0, Principle I). The feature uses
the standard, widely used Flask approach for each concern and deliberately omits
production-grade extras (server-side session revocation, timing-equalization, audit
tables, MFA, password reset).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign in to see my budget (Priority: P1)

A person with an account opens the budget site and lands on a sign-in page asking for an
email address and password. After valid credentials they reach the page they originally
wanted (or the home page) and can use every existing page as before.

**Why this priority**: the site is on the public internet and currently shows all
financial data to anyone who reaches it.

**Independent Test**: with an account in place, open any budget page in a fresh browser,
confirm a sign-in page appears instead of data, sign in, and confirm the requested page
loads.

**Acceptance Scenarios**:

1. **Given** a visitor who is not signed in, **When** they request any budget page or
   data-changing action, **Then** they are sent to the sign-in page and no financial data
   is included in the response.
2. **Given** the sign-in page, **When** a visitor submits a correct email and password,
   **Then** they are signed in and shown the page they originally requested (or home).
3. **Given** a signed-in user, **When** they visit the sign-in page, **Then** they are sent
   to the home page.
4. **Given** a sign-in link whose "return to" target points at another website, **When**
   the user signs in, **Then** they land on the home page, never on the external site.

---

### User Story 2 - Failed sign-ins reveal nothing and are limited (Priority: P1)

Someone guessing at emails or passwords gets the same generic failure message whether or
not the email exists, and cannot guess indefinitely: after too many attempts further
attempts are refused for a while.

**Why this priority**: on a public site, without this an attacker can learn which emails
have accounts and try unlimited passwords.

**Independent Test**: submit a wrong password for a real email and any password for an
unknown email and compare messages; then exceed the attempt limit and confirm further
attempts are refused until the limit window passes.

**Acceptance Scenarios**:

1. **Given** the sign-in page, **When** a visitor submits an unknown email or a wrong
   password, **Then** they see the same generic "invalid email or password" message.
2. **Given** repeated sign-in attempts beyond the limit (5 per 15 minutes for one email,
   or 20 per 15 minutes from one source), **When** another attempt is made, **Then** it is
   refused with a "too many attempts, try again later" message, even if the password is
   correct.
3. **Given** the limit window has passed, **When** the user signs in correctly, **Then**
   sign-in succeeds.

---

### User Story 3 - Sign out and session expiry (Priority: P2)

A signed-in user can sign out from any page. Afterwards the browser no longer shows data
(including via the Back button). Sessions also end on their own after a period of
inactivity.

**Why this priority**: matters on shared devices; the site is already protected without it.

**Independent Test**: sign in, sign out, request a budget page and press Back; separately
let a session sit idle past the limit and confirm the next request requires sign-in.

**Acceptance Scenarios**:

1. **Given** a signed-in user, **When** they sign out, **Then** they are shown the sign-in
   page and budget pages require sign-in again in that browser.
2. **Given** a session idle longer than 12 hours, **When** the user makes the next
   request, **Then** they are asked to sign in again.

---

### User Story 4 - Register my own account (Priority: P1)

A new person opens a registration page, enters an email address and password, and creates
an account. Weak passwords and already-registered emails are refused. A new account starts
empty and sees only its own data.

**Why this priority**: without registration nobody can sign in, and the goal is for several
people to each have their own budget.

**Independent Test**: register two accounts, add different data to each, and confirm
neither can see or change the other's data, including by editing a record id in the URL.

**Acceptance Scenarios**:

1. **Given** the registration page, **When** a visitor submits a valid email and a password
   of at least 12 characters, **Then** an account is created and they are signed in to an
   empty home page.
2. **Given** a too-short password or an invalid email, **When** submitted, **Then**
   registration is refused with the reason.
3. **Given** an existing account, **When** someone registers the same email (ignoring
   case), **Then** registration is refused.
4. **Given** two accounts, **When** one views, edits, or deletes data, **Then** only its own
   data is affected; another account's record id behaves as if it does not exist.

---

### User Story 5 - Keep my existing data (Priority: P1)

The owner's budget data that exists today must survive turning on sign-in and must go to
the owner's account, not to whoever registers first.

**Why this priority**: otherwise enabling sign-in loses the data or hands it to a stranger.

**Independent Test**: with existing data and registration open, register an unrelated
account and confirm it sees none of it; then run the owner claim step for the owner's
account and confirm all prior data appears there unchanged.

**Acceptance Scenarios**:

1. **Given** pre-existing data, **When** any account signs in before a claim, **Then** it
   sees none of the pre-existing data.
2. **Given** pre-existing data and an owner account, **When** the site operator runs the
   claim step naming that account, **Then** all of the data is attached to that account,
   unchanged.

---

### Edge Cases

- Email entered with different capitalization or surrounding spaces still matches.
- Very long passwords (hundreds of thousands of characters) are rejected quickly.
- A form submitted from another website is rejected.
- The session cookie is never sent over plain HTTP.
- The load balancer's health check has no credentials and must keep passing.
- Two people registering the same email at once: exactly one account is created.
- Browser Back after sign-out does not reveal previously displayed financial data.
- A sign-in error never echoes the submitted password.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST present a sign-in page asking for an email address and a
  password.
- **FR-002**: Every existing budget page and every action that adds, edits, deletes, or
  toggles data MUST require a signed-in account; unauthenticated requests MUST be
  redirected to the sign-in page without any financial data. New pages MUST require
  sign-in by default.
- **FR-003**: After sign-in the system MUST send the user to the page they originally
  requested only if it is on this site; otherwise to the home page.
- **FR-004**: Passwords MUST be stored only as salted, slow, one-way hashes and MUST NOT
  appear in plaintext in storage, logs, or error output.
- **FR-005**: Failed sign-ins MUST show one generic message that does not reveal whether
  the email has an account.
- **FR-006**: Sign-in and registration attempts MUST be rate limited: sign-in at 5
  attempts per 15 minutes per email and 20 per 15 minutes per source; registration at 5
  per hour per source. Refused attempts MUST NOT check the password.
- **FR-007**: Session cookies MUST be HttpOnly, Secure (HTTPS only), and SameSite, and a
  fresh session MUST start at sign-in.
- **FR-008**: Every form that changes data (sign-in, registration, sign-out, and all
  existing add/edit/delete/toggle forms) MUST be protected against cross-site request
  forgery.
- **FR-009**: Users MUST be able to sign out; sign-out MUST clear the session in that
  browser.
- **FR-010**: Sessions MUST end after 12 hours of inactivity.
- **FR-011**: Pages showing financial data MUST be marked non-cacheable so Back after
  sign-out does not reveal data.
- **FR-012**: Passwords MUST be 12-128 characters with no composition rules; emails MUST
  be case-insensitive, trimmed, and unique.
- **FR-013**: A minimal health-check page that returns no user data MUST be reachable
  without signing in.
- **FR-014**: The site MUST offer a public registration page, and each account MUST have
  entirely separate budget data (pay schedule, expenses, annual costs, savings accounts,
  credit cards). Every read, change, and delete MUST be limited to the signed-in
  account's own data; another account's record id MUST behave as not found. A new account
  starts empty.
- **FR-015**: Budget data that exists before this feature MUST NOT be visible to any
  account until the site operator explicitly assigns it to a named account with a claim
  command; registration alone MUST NOT grant access to it. Enabling sign-in MUST NOT
  alter or lose existing data.
- **FR-016**: Sign-in successes, failures, and refusals SHOULD be written to the
  application log without passwords.

### Key Entities *(include if feature involves data)*

- **User Account**: an email address (normalized, unique) and a password hash. Owns all of
  its budget data.
- **Budget Data (existing entities)**: pay schedule, recurring expenses, savings accounts,
  and credit card accounts each belong to exactly one User Account.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A returning user can sign in and reach their budget page in under 15 seconds
  with a password manager.
- **SC-002**: 100% of existing budget pages and data-changing actions return the sign-in
  page, with no financial data, when requested without being signed in.
- **SC-003**: Beyond the attempt limit, 100% of further sign-in attempts are refused until
  the window passes.
- **SC-004**: Unknown-email and wrong-password attempts show identical messages.
- **SC-005**: Inspection of storage and logs finds no plaintext passwords.
- **SC-006**: After sign-out, the browser cannot reach any budget page without signing in
  again, including via Back.
- **SC-007**: After enabling sign-in and running the claim step, 100% of pre-existing data
  is present and unchanged for the owner's account, and 0% is visible to any other account.
- **SC-008**: In an automated test with two accounts, neither can read or change the
  other's records of any kind by id.
- **SC-009**: The deployment's health check keeps passing with sign-in enabled.

## Assumptions

- The site runs behind a load balancer that terminates HTTPS, and the app can tell the
  original request was HTTPS so Secure cookies work.
- Moving storage from SQLite to Aurora Postgres is a separate, later feature; this feature
  works with SQLite and should not make that move harder.
- Out of scope: password reset by email (the app sends no email), changing a password from
  the site, multi-factor authentication, single sign-on, "remember me", account deletion,
  email verification, server-side session revocation (sign-out clears the browser's
  session; a copied cookie remains valid until it expires), and audit tables.
- Without email verification, registration reveals whether an email is already taken, and
  someone could register the owner's email first. This is accepted: they still cannot see
  the owner's data (FR-015). The owner can use any other email for the claim.
- Network access to the site is currently restricted to the owner's IP. Letting other
  people register means opening that restriction, which is a rollout step done last, after
  sign-in is verified and storage is durable (the deployed task's SQLite file is currently
  erased on each deploy, which would erase all accounts).
- Constitution v3.1.0 allows public deployment and multiple accounts under Principles IV
  and VI, and asks for standard libraries over custom machinery.
