---

description: "Task list for login-authentication implementation"
---

# Tasks: Login Authentication

**Input**: Design documents from `/specs/006-login-authentication/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/web-routes.md, quickstart.md (all present)

**Tests**: Included. Constitution Principle VI requires isolation tests for every kind of record, and the spec's success criteria (SC-002, SC-003, SC-008) are automated checks. All ~35 existing integration tests must be updated to sign in.

**Organization**: Grouped by user story from spec.md. US1, US2, US4, US5 are P1; US3 is P2. A Foundational phase comes first because the `user_id` plumbing through `db.py` touches every route and test, so it cannot be split per story. Phases below are ordered by priority: US1, US2, US4, US5, US3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- File paths are exact, per `plan.md`'s Project Structure

## Path Conventions

Single project, per `plan.md`: `src/budget/`, `tests/unit/`, `tests/integration/`. Infra tasks (marked) are in the separate `~/code/basso-infra` repo.

---

## Phase 1: Setup

- [X] T001 Add `flask-login`, `flask-wtf`, and `flask-limiter` to `dependencies` in `pyproject.toml`
- [X] T002 Run `.venv/bin/pip install -e '.[dev,deploy]'` and `./scripts/check.sh` to confirm the baseline is green before changes (depends on T001)
- [X] T003 [P] Update `scripts/dev-server.sh` to export `BUDGET_ENV=development` before starting the server (so the cookie is not Secure-only and the fixed dev secret key is used)

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Account model, password rules, schema/migration, user CRUD, and per-user scoping of every budget query. No story can work without these.

- [X] T004 [P] Add `User` to `src/budget/models.py`: frozen dataclass subclassing `flask_login.UserMixin` with `id: int` and `email: str` (never carries the password hash)
- [X] T005 [P] Create `src/budget/accounts.py` (no Flask imports): `normalize_email` (strip, lowercase), `validate_email` (single `@`, non-empty local and domain, <= 254 chars), `validate_password` (12-128 chars, no composition rules), `hash_password` / `verify_password` wrapping Werkzeug `generate_password_hash` / `check_password_hash`; raise the existing `ValidationError` with user-readable messages; `verify_password` returns `False` without hashing when the password exceeds 128 characters (data-model.md, research.md D1)
- [X] T006 [P] Unit tests in `tests/unit/test_accounts.py`: email normalization (case, surrounding spaces), invalid emails, password length boundaries (11 rejected, 12 and 128 accepted, 129 rejected), hash is not the password and differs for identical passwords (salt), `verify_password` true/false and false for oversized input
- [X] T007 In `src/budget/db.py`, add the `users` table to `SCHEMA` and change `connect` to run `PRAGMA foreign_keys = ON`; define the fresh-database shape of `pay_schedule` as `id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE, anchor_date, amount` and add `user_id INTEGER REFERENCES users(id) ON DELETE CASCADE` plus an index to `recurring_expense`, `account`, and `credit_account` (data-model.md)
- [X] T008 In `src/budget/db.py`, add `_migrate_add_user_ownership(conn)` and call it from `init_db`: add `user_id` to the three tables if missing, and if `pay_schedule` has no `user_id` column rebuild it (create new, copy the existing row with `user_id` NULL, drop old, rename), then create the indexes; idempotent like the existing `_migrate_*` functions (depends on T007)
- [X] T009 In `src/budget/db.py`, add `create_user(conn, email, password_hash) -> int` (translate `sqlite3.IntegrityError` on the unique email into `ValidationError("That email is already registered")`), `get_user(conn, user_id) -> User | None`, and `get_user_with_hash(conn, email) -> tuple[User, str] | None` (depends on T004, T007)
- [X] T010 In `src/budget/db.py`, add a required first-after-`conn` `user_id: int` parameter to every budget function and add `AND user_id = ?` / set `user_id` in `INSERT`: `get_pay_schedule`, `set_pay_schedule` (upsert on `user_id`), `list_expenses`, `get_expense`, `create_expense`, `update_expense`, `delete_expense`, `list_accounts`, `get_account`, `create_account`, `update_account`, `delete_account`, `list_credit_accounts`, `get_credit_account`, `create_credit_account`, `update_credit_account`, `delete_credit_account` (research.md D8; depends on T007, T008)
- [X] T011 Update `tests/conftest.py`: `app` fixture passes a test config (fixed `SECRET_KEY`, `TESTING=True`, `WTF_CSRF_ENABLED=False`, rate limits reset per test); add `make_user(app, email, password) -> int` helper that creates an account through `db`/`accounts`, a `login(client, email, password)` helper, and `logged_in_client` / `user_id` fixtures. `create_app` signature in T013 must accept a `config` mapping (depends on T005, T009)

**Checkpoint**: Schema, migration, password rules, and per-user queries exist; nothing is wired to routes yet.

---

## Phase 3: User Story 1 - Sign in to see my budget (Priority: P1) 🎯 MVP

**Goal**: Every budget page requires sign-in; a user with an account can sign in with email and password and reach the page they asked for.

**Independent Test**: With an account created through the test helper, anonymous requests to every budget route redirect to `/login`; signing in lands on the requested page; the existing route tests pass while signed in (quickstart.md steps 1, 2.1).

### Tests for User Story 1

- [X] T012 [P] [US1] Integration tests in `tests/integration/test_protection.py`: iterate `app.url_map.iter_rules()` for endpoints starting with `budget.`, fill `<int:...>` parameters with `1`, and assert an anonymous request (GET, or POST for POST-only rules) returns `302` to `/login?next=...` with no budget content; assert `/healthz` and `/login` are reachable anonymously
- [X] T013 [P] [US1] Integration tests in `tests/integration/test_auth.py` (login section): correct credentials redirect to `next` or `/`; a `next` of `https://evil.example`, `//evil.example`, or `javascript:` is ignored and goes to `/`; a signed-in user visiting `/login` is redirected to `/`; email matches case-insensitively with surrounding spaces; the session cookie has `HttpOnly` and `SameSite=Lax`; non-static responses carry `Cache-Control: no-store`

### Implementation for User Story 1

- [X] T014 [US1] In `src/budget/app.py`, extend `create_app(db_path, config=None)`: read `BUDGET_ENV` (default production), `BUDGET_SECRET_KEY` (required in production, fixed dev value in development, exit with a clear error if missing), `BUDGET_TRUST_PROXY` (wrap in Werkzeug `ProxyFix` with `x_for=1, x_proto=1, x_host=1` when `1`); set `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SECURE` (true unless development/testing), `SESSION_COOKIE_SAMESITE="Lax"`, `PERMANENT_SESSION_LIFETIME=12h`; initialise `LoginManager` (`login_view="auth.login"`), `CSRFProtect`, and the Limiter; register the auth blueprint; add an `after_request` setting `Cache-Control: no-store` on non-static responses (research.md D2-D7, D10)
- [X] T015 [US1] Create `src/budget/auth.py`: `auth` blueprint, `limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")`, the `LoginManager.user_loader` calling `db.get_user`, a `safe_next_url` helper (relative path, single leading `/`, no scheme or host), `GET`/`POST /login` (normalize email, look up with `get_user_with_hash`, `verify_password`, then `session.clear()`, `session.permanent = True`, `login_user`, redirect to the validated `next` or `/`; one generic message "Invalid email or password." on any failure, password never re-rendered), and `GET /healthz` returning `ok` (contracts/web-routes.md; depends on T005, T009, T014)
- [X] T016 [P] [US1] Create `src/budget/templates/login.html` extending `layout.html`: email and password fields, hidden `next`, `{{ csrf_token() }}` hidden input, error message area, link to `/register` (depends on T015)
- [X] T017 [US1] In `src/budget/routes.py`, add `@bp.before_request` returning `login_manager.unauthorized()` when `current_user.is_authenticated` is false, and update the home, pay-schedule, annual-cost, expenses list/new/create/edit/update/delete, and toggle-essential routes plus `_existing_categories` to pass `current_user.id` to every `db` call (depends on T010, T015)
- [X] T018 [US1] In `src/budget/routes.py`, update the runway and savings-account routes (`/runway`, `/runway/accounts/...` new, create, edit, update, delete) to pass `current_user.id` to every `db` call (depends on T017)
- [X] T019 [US1] In `src/budget/routes.py`, update the credit-card routes (`/credit-cards`, `/credit-cards/...` new, create, edit, update, delete) to pass `current_user.id` to every `db` call (depends on T018)
- [X] T020 [P] [US1] Add `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` to every `method="post"` form in `src/budget/templates/` (`grep -n 'method="post"' src/budget/templates/*.html` to find them: pay schedule, expense form, expenses list delete/toggle, runway, account form, credit cards, credit account form)
- [X] T021 [US1] Update `tests/integration/test_routes.py`: seed helpers (`_seed_pay_schedule`, `_seed_expense`, account and credit-card seeders) take and pass `user_id`; use `logged_in_client` and its `user_id` throughout; all existing assertions stay unchanged (depends on T011, T017-T019)
- [X] T022 [US1] Run `./scripts/check.sh`; fix failures until pytest and mypy are clean (if mypy reports missing stubs for `flask_wtf`, add a `[[tool.mypy.overrides]]` entry with `ignore_missing_imports = true` for that module only in `pyproject.toml`)

**Checkpoint**: Signed-in users can use the whole app exactly as before; anonymous users see nothing. This is the MVP, though accounts can only be created via the test helper until US4.

---

## Phase 4: User Story 2 - Failed sign-ins reveal nothing and are limited (Priority: P1)

**Goal**: Same message for unknown email and wrong password; attempts beyond the limit are refused before the password is checked.

**Independent Test**: Compare failure messages; exceed 5 attempts for one email and confirm the correct password is also refused (quickstart.md step 2.4).

### Tests for User Story 2

- [X] T023 [P] [US2] Integration tests in `tests/integration/test_auth.py` (failure section): unknown email and wrong password return identical response bodies/messages; the password is never present in the response; 6th attempt for one email returns `429` with "Too many attempts. Try again later." even with the correct password; the per-source limit (21st attempt from one address using different emails) returns `429`; limits are reset between tests via the fixture; an over-128-character password is a normal failure

### Implementation for User Story 2

- [X] T024 [US2] In `src/budget/auth.py`, add Flask-Limiter decorators to `POST /login`: `20 per 15 minutes` per source and `5 per 15 minutes` keyed by the normalized submitted email, and a `429` error handler that renders `login.html` with the generic message and status 429; log sign-in success, failure, and refusal at INFO/WARNING via `current_app.logger` with email and source but never the password (FR-016; depends on T015)

**Checkpoint**: US1 and US2 both work.

---

## Phase 5: User Story 4 - Register my own account (Priority: P1)

**Goal**: A visitor can register, sign in, and see only their own (initially empty) data; accounts cannot see or change each other's records.

**Independent Test**: Register two accounts, add different data to each, confirm neither sees or modifies the other's by id (quickstart.md steps 2.2, 2.5).

### Tests for User Story 4

- [X] T025 [P] [US4] Integration tests in `tests/integration/test_auth.py` (registration section): valid registration creates the account, signs in, and redirects to `/`; 11-character password, invalid email, mismatched confirmation each refused with a message and nothing stored; duplicate email (different case) refused; `POST /register` without CSRF token returns `400` (enable CSRF in that test's config); the 6th registration from one source in an hour returns `429`; a new account sees an empty home page and empty expenses/runway/credit-cards lists
- [X] T026 [P] [US4] Integration tests in `tests/integration/test_isolation.py`: with accounts A and B, A creates a pay schedule, an expense, a savings account, and a credit card; B's lists show none of them; B's `GET`/`POST` edit, delete, and toggle-essential of A's record ids each return `404` and leave A's data unchanged; A's data is intact afterward (Principle VI, SC-008)

### Implementation for User Story 4

- [X] T027 [US4] In `src/budget/auth.py`, add `GET`/`POST /register`: validate with `accounts.py`, require matching confirmation, `create_user`, then sign in as in `/login`; apply `5 per hour` per-source limit with the generic `429` handling; signed-in visitors are redirected to `/` (contracts/web-routes.md; depends on T015, T024)
- [X] T028 [P] [US4] Create `src/budget/templates/register.html` extending `layout.html`: email, password, confirm password, CSRF hidden input, the 12-character minimum shown, field-level error messages, link back to `/login` (depends on T027)

**Checkpoint**: Multi-account use works end to end.

---

## Phase 6: User Story 5 - Keep my existing data (Priority: P1)

**Goal**: Pre-existing data survives, is invisible to everyone, and moves to a named account only via the operator command.

**Independent Test**: Migrate a database containing old-style rows; register an unrelated account and confirm it sees nothing; run the claim command and confirm everything appears unchanged (quickstart.md step 2.6).

### Tests for User Story 5

- [X] T029 [P] [US5] Tests in `tests/integration/test_db_migration.py`: build a database with the pre-feature schema (singleton `pay_schedule` with `id = 1`, no `user_id` columns) and rows in all four tables; `init_db` preserves every row with `user_id` NULL; a second `init_db` is a no-op; `list_*`/`get_*` for any user id return nothing for those rows
- [X] T030 [P] [US5] Tests in `tests/integration/test_claim_legacy.py` using `app.test_cli_runner()`: `claim-legacy --email` assigns every NULL-owned row in all four tables to that account (values unchanged) and prints per-table counts; it errors for an unknown email, errors if the account already owns budget data (nothing changes), and does not touch rows owned by other accounts; an unrelated account signed in before the claim sees none of the legacy data

### Implementation for User Story 5

- [X] T031 [US5] In `src/budget/db.py`, add `claim_legacy_rows(conn, user_id) -> dict[str, int]`: in one transaction, raise `ValidationError` if the user already owns any row in the four tables, otherwise `UPDATE ... SET user_id = ? WHERE user_id IS NULL` on each and return the counts (data-model.md; depends on T008)
- [X] T032 [US5] In `src/budget/app.py`, register a Flask CLI command `claim-legacy --email` that normalizes the email, looks up the account (error if missing), calls `claim_legacy_rows`, and prints counts per table (depends on T031)

**Checkpoint**: Existing data can be safely attached to the owner's account.

---

## Phase 7: User Story 3 - Sign out and session expiry (Priority: P2)

**Goal**: Users can sign out; sessions end after 12 hours idle; Back after sign-out shows no cached data.

**Independent Test**: Sign in, sign out, request a budget page, check no-store headers (quickstart.md step 2.3).

### Tests for User Story 3

- [X] T033 [P] [US3] Integration tests in `tests/integration/test_auth.py` (sign-out section): `POST /logout` with a valid session signs out and redirects to `/login`, after which a budget page redirects to `/login`; `GET /logout` returns `405`; the logout form rejects a missing CSRF token (CSRF enabled in that test); `PERMANENT_SESSION_LIFETIME` is 12 hours and the session is permanent after sign-in

### Implementation for User Story 3

- [X] T034 [US3] In `src/budget/auth.py`, add `POST /logout`: `logout_user()`, `session.clear()`, redirect to `/login` (depends on T015)
- [X] T035 [US3] In `src/budget/templates/layout.html`, show the signed-in email and a sign-out `<form method="post" action="{{ url_for('auth.logout') }}">` with the CSRF hidden input when `current_user.is_authenticated` (depends on T034)

**Checkpoint**: All five user stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T036 Run `./scripts/check.sh` (pytest + mypy `--strict`) and fix anything outstanding
- [X] T037 Run the quickstart.md local walkthrough (section 2) in a browser with the chrome-devtools MCP tools against `./scripts/dev-server.sh restart`; close the page when done (CLAUDE.md rule); fix any discrepancy
- [X] T038 [P] Update `CLAUDE.md` (Commands: `BUDGET_ENV`, `BUDGET_SECRET_KEY`, `claim-legacy`; Where things are: spec 006) and `README.md` (sign-in, registration, env vars)
- [X] T039 [P] (basso-infra) In `~/code/basso-infra/basso-root/us-west-2/biweekly-budget/main.tf`: add `BUDGET_ENV=production` and `BUDGET_TRUST_PROXY=1` to the container environment, inject `BUDGET_SECRET_KEY` through the task definition `secrets` from an SSM SecureString ARN (parameter created beforehand with `aws ssm put-parameter --type SecureString`), grant the execution role `ssm:GetParameters` on that one parameter, and set the target group `health_check.path` to `/healthz`
- [ ] T040 Deploy with `.venv/bin/python deploy/deploy.py` after `terragrunt apply`; verify `curl -sI https://budget.taylorbasso.dev/` returns `302` to `/login` and `/healthz` returns `200` (quickstart.md section 3; depends on T036, T039)
- [ ] T041 GATE before opening access to others: choose durable storage for `/data` (EFS with overlap-free deployments, or the Aurora feature) in `basso-infra`; only then widen the ALB security group beyond the owner's IP and register from another network. Until then, registration must stay IP-restricted because the deployed SQLite file (including all accounts) is erased on each deploy

---

## Dependencies & Execution Order

- **Setup (T001-T003)** first. T003 is independent of T001/T002.
- **Foundational (T004-T011)** blocks all stories. Within it: T004, T005, T006 are parallel; T007 -> T008 -> T010 (all `db.py`, sequential); T009 needs T004 and T007; T011 needs T005, T009.
- **US1 (T012-T022)** needs Foundational. Tests T012/T013 can be written first (they fail until implementation). T014 -> T015 -> T016/T017; T017 -> T018 -> T019 (same file); T020 is independent; T021 needs T011 and T017-T019; T022 last.
- **US2 (T023-T024)**, **US4 (T025-T028)**, **US5 (T029-T032)** each need US1 complete and are independent of each other, except US4's T027 builds on US2's T024 limiter wiring.
- **US3 (T033-T035)** needs US1 only.
- **Polish (T036-T041)** after the stories; T039 can start any time after T014 defines the env var names; T041 gates opening access.

### Parallel opportunities

- Foundational: T004, T005, T006 together.
- US1 tests: T012 and T013 together; T016 and T020 alongside route work.
- After US1: US2, US5, US3 phases can be done in parallel by different people (different parts of `auth.py` merge cleanly if done sequentially, so for one person just proceed in phase order).
- Polish: T038 and T039 together.

## Implementation Strategy

1. **MVP**: Phases 1-3 (through T022). The app is fully protected and works for signed-in users. Accounts are only creatable via the test helper, so do not deploy publicly yet.
2. **Make it usable**: add US4 (registration) and US2 (rate limiting) next, then US5 (claim legacy data) so the owner's data can move to their account, then US3 (sign-out).
3. **Ship**: polish, infra changes (T039), deploy (T040) while the allow-list still restricts access to the owner's IP.
4. **Open access**: only after T041's durable-storage gate.

## Notes

- Constitution v3.1.0 applies: use the standard extensions; do not add server-side session tables, timing tricks, or audit tables.
- Every `db.py` signature change in T010 is a breaking change for callers; mypy will flag any call site missed in T017-T019 and T021.
- Money handling and cycle logic are not modified; existing calculation tests must keep passing untouched.
