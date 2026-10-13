<!--
Sync Impact Report
Version change: 3.0.0 → 3.1.0 (same-day follow-up to the 3.0.0 amendment below)
Bump rationale: MINOR — Principle I gains a "hobby app, prefer standard libraries"
  rule, and Principle VI is simplified to match it (standard extensions instead of
  hand-built session/throttle machinery; no per-route registry test).
Earlier in this amendment cycle: 2.0.0 → 3.0.0 (MAJOR) — Principles I and IV previously
  prohibited public deployment and multi-user accounts; those prohibitions were removed
  (backward-incompatible redefinition), and a new Principle VI was added.
Modified principles:
  - I. Simplicity First (YAGNI) — removed the blanket deferral of "public-facing
    deployment" and "multi-user accounts" (the app is now deployed publicly at
    https://budget.taylorbasso.dev with multiple accounts and self-registration);
    baseline is still a single Flask app + SQLite; other speculative extensions remain
    deferred; the planned Aurora Postgres move is noted as requiring its own amendment
  - IV. Local-First Data Privacy — replaced "bind only to localhost / never deployed
    publicly" with: dev server binds to 127.0.0.1 by default; public deployment allowed
    only behind HTTPS with authentication on every page by default; no third-party data
    transfer (no telemetry, no outbound email); credentials only as salted slow one-way
    hashes
Added sections:
  - VI. Authentication & Data Isolation (new core principle)
  - Development Workflow: added rules for tracked migrations covering per-account
    ownership and for the baseline wording
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed (Constitution Check gate
    reads principles at plan time; still generic)
  - .specify/templates/spec-template.md ✅ no changes needed
  - .specify/templates/tasks-template.md ✅ no changes needed
  - CLAUDE.md ✅ updated — description and governing-rules bullets match v3.0.0
  - README.md ✅ updated — localhost note and governing-rules summary match v3.0.0
  - specs/006-login-authentication/spec.md ✅ already flags this amendment
Follow-up TODOs:
  - Moving storage from SQLite to Aurora Postgres will need its own amendment of
    Principles I and IV (storage baseline) before it is planned.
-->

<!-- Previous report (2.0.0, 2026-07-28): Version 1.0.0 → 2.0.0; Principle I redefined from
CLI to local Flask web app; Principle II generalized from CLI-first to library-oriented;
Principle IV gained an explicit localhost-only binding rule. -->


# Biweekly Budget Constitution
<!-- A personal budgeting tool that tells you how much free money you have left to spend
between one paycheck and the next. -->

## Core Principles

### I. Simplicity First (YAGNI)
The system MUST be built as a single web application (Flask) backed by a SQLite
database. The application MAY be deployed publicly and MAY serve multiple accounts, each
with strictly separate data, under the rules in Principles IV and VI. No additional
interface (native desktop GUI, mobile app) MAY be introduced until a concrete, stated
need exists. Moving storage off SQLite (for example to Aurora Postgres) requires its own
amendment of this principle and Principle IV before it is planned. Every feature MUST
serve the core goal — computing discretionary spending money between pay dates — before
speculative extensions (multi-currency, recurring-transaction templates, budget
forecasting, shared/household budgets, etc.) are considered. When in doubt, ship the
smaller thing.

This is a hobby application, not a production service. When a need is common, MUST
prefer the widely used, well-documented solution for Flask apps (for example Flask-Login,
Flask-WTF, Flask-Limiter, Werkzeug's password hashing) over a custom implementation, and
MUST NOT invent requirements beyond what the feature actually needs (for example
server-side session revocation tables, timing-equalization tricks, or custom audit
infrastructure). Standard behaviour of a well-known library is the definition of "good
enough" here; a bespoke mechanism needs a stated reason in the plan's Complexity Tracking.
Container size or memory MAY be increased to avoid complexity.

Rationale: this started as a personal project and the fastest path to a useful tool is a
small, focused core. Public deployment and per-account data are now real needs, so they
are governed by explicit rules instead of being forbidden; everything else stays
deferred until its need is concrete.

### II. Library-Oriented Design
Core budget logic (pay-cycle computation, expense-to-cycle matching, leftover-amount
calculation, category breakdown) MUST live in a Python module independent of the web
layer. Flask routes/views MUST be thin wrappers over that module: parse input, call the
core module, render output. Business logic MUST NOT be embedded directly in route
handlers or templates.

Rationale: keeping the calculation engine separate from the web layer means it stays
independently testable and could be reused behind a different interface later without
rewriting logic that has already been validated.

### III. Type Safety & Static Checking
All Python code MUST use type hints on public functions, method signatures, and data
models (income entries, expenses, budget categories, cycle results). A static type
checker MUST be run during development and MUST pass with no errors before a change is
considered complete.

Rationale: this tool exists to answer a money question the user will act on. Static
typing catches an entire class of mistakes (wrong types flowing into date/amount math)
before they can produce a wrong answer.

### IV. Local-First Data Privacy
Income, expenses, and category data MUST be stored in the application's own SQLite
database. No financial data MAY be transmitted to any third-party service or network
endpoint without explicit, separate user opt-in for that specific feature. There is no
default cloud sync, telemetry, outbound email, or external reporting. The development
server MUST bind to localhost (127.0.0.1) by default. A public deployment is permitted
only behind HTTPS and only when authentication is required on every page by default
(Principle VI). Credentials MUST be stored only as salted, deliberately slow, one-way
hashes — never in plaintext or reversible form, and never in logs or error output.

Rationale: this is personal financial data. The default posture is that it never leaves
the application's own storage unless a user specifically chooses to send it somewhere.
Public reachability is now allowed because the app is deployed that way, but a reachable
web server exposes every page to the internet, so encryption in transit, mandatory
authentication, and safe credential storage have to be stated rules, not assumptions.

### V. Correctness of Financial Calculations (NON-NEGOTIABLE)
Any code that determines pay-cycle boundaries, matches an expense's due date to a cycle,
or computes the leftover/discretionary amount MUST have automated tests covering boundary
conditions: the cycle's start date, the day immediately before the next paycheck,
month/year rollovers, and leap years. Every expense MUST be attributed to exactly one
cycle — never zero, never two — so cycles MUST partition time with no gaps and no
overlaps.

Rationale: this calculation is the entire value proposition of the tool. A silently wrong
answer here (double-counting a bill, or dropping one) is worse than the tool not existing,
because the user will make spending decisions based on it.

### VI. Authentication & Data Isolation
Every page and data-changing action MUST require a signed-in account by default; a route
is public only if it is explicitly exempted (sign-in, registration, and a minimal liveness
check that returns no user data). Every database read, write, and delete of budget data
MUST be scoped to the signed-in account; a request that names another account's record
MUST behave as if the record does not exist. All forms MUST be protected against
cross-site request forgery. Session cookies MUST be HttpOnly, Secure, and SameSite, and
sessions MUST start fresh at sign-in and be cleared at sign-out. Sign-in and registration
MUST be rate limited. Sign-in failures MUST show one generic message that does not say
whether the email exists. Automated tests MUST show that one account cannot read, change,
or delete another account's records by id, covering each kind of record (pay schedule,
expenses, savings accounts, credit cards).

Rationale: with public deployment and multiple accounts, a single missed filter or
unprotected route exposes someone's entire financial picture. Making protection the
default, and testing isolation for every kind of record, keeps a forgotten check from
becoming a data leak. Using the standard extensions for the mechanics keeps the code small.

## Core Domain Rules

- **Income event**: a paycheck with a date and an amount.
- **Expense**: a bill or budget-category item with a due date and an amount.
- **Cycle**: the span from one income event's date up to (but not including) the next
  income event's date. Example: paid Friday July 31 and next paid Friday August 14 → the
  cycle runs July 31 through August 13 inclusive; August 14 belongs to the *next* cycle.
- **Leftover (discretionary) amount** for a cycle = the cycle's paycheck amount minus the
  sum of all expenses whose due date falls within that cycle.
- Cycle boundaries and expense-to-cycle attribution are derived data, not user input —
  they MUST be computed from stored income and expense dates, never hardcoded or manually
  assigned.

## Development Workflow

- A static type checker MUST pass before a change is considered done (Principle III).
- Automated tests covering cycle-boundary and leftover-calculation logic MUST pass before
  a change touching that logic is considered done (Principle V).
- Database schema changes MUST be expressed as migrations tracked in the repository, not
  as ad-hoc manual edits to a developer's local database file.
- Templates MUST rely on Flask/Jinja2's default auto-escaping for any user-supplied text
  (expense names, categories) rendered in HTML; auto-escaping MUST NOT be disabled to
  work around a formatting problem.
- New interfaces, dependencies, or stored-data categories that go beyond the Flask +
  SQLite baseline MUST be justified against Principles I, IV, and VI before being added.
- Schema changes that add or change per-account ownership of data MUST be tracked
  migrations that preserve every existing row, and MUST NOT assign existing data to an
  account other than the one explicitly designated as its owner.
- A change is not done until the Principle VI isolation tests pass for every kind of
  record it adds or changes.

## Governance

This constitution supersedes any conflicting practice or prior informal convention for
this project. Amendments are made by editing this file directly, updating the Sync Impact
Report at its top, and bumping the version per the policy below.

**Versioning policy** (semantic versioning applied to governance):
- MAJOR: a principle is removed or redefined in a way that is backward-incompatible with
  prior guidance.
- MINOR: a new principle or section is added, or existing guidance is materially expanded.
- PATCH: wording, clarification, or typo fixes with no semantic change.

**Compliance review**: any change to core budget-calculation logic, storage, or the
web/library boundary should be checked against the Core Principles above before being
merged. Complexity that violates Principle I (Simplicity First) must be justified in the
relevant plan's Complexity Tracking section rather than added silently.

**Version**: 3.1.0 | **Ratified**: 2026-07-28 | **Last Amended**: 2026-10-12
