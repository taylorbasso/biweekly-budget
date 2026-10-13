# Implementation Plan: Login Authentication

**Branch**: `006-login-authentication` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-login-authentication/spec.md`

## Summary

Put every page behind email-and-password sign-in, add public self-registration, and give
each account its own isolated budget data, using the standard Flask stack: **Flask-Login**
for sessions, **Werkzeug** scrypt for password hashes, **Flask-WTF** `CSRFProtect` for CSRF,
and **Flask-Limiter** for rate limiting. All budget tables gain a `user_id`, every database
function takes the signed-in user's id and filters on it, and pre-existing data stays
unowned until an operator command assigns it to a named account.

## Technical Context

**Language/Version**: Python 3.11 (matches `Dockerfile` and `pyproject.toml`)

**Primary Dependencies**: Flask >= 3.0 and gunicorn (existing); **new**: Flask-Login,
Flask-WTF, Flask-Limiter. Password hashing uses Werkzeug, already installed with Flask.

**Storage**: SQLite (unchanged). New `users` table; `user_id` column on `pay_schedule`,
`recurring_expense`, `account`, `credit_account`.

**Testing**: pytest (existing) and `mypy --strict` on `src/`. Flask-WTF may lack type
stubs; if mypy complains, add a single `ignore_missing_imports` override for that module.

**Target Platform**: Linux container on ECS Fargate (ARM64) behind an ALB that terminates
HTTPS; local dev at `http://127.0.0.1:5001`. The current 512 MB task is enough for
scrypt's default settings, so no container-size change is planned.

**Project Type**: web-service (single Flask app, server-rendered templates)

**Performance Goals**: sign-in in about a second; other pages unchanged.

**Constraints**: no outbound network calls; no new JavaScript or build tooling; rate-limit
counters live in memory (single gunicorn worker), so they reset on restart, which is fine
for a hobby app.

**Scale/Scope**: a handful of accounts; ~20 existing routes plus register, login, logout,
and a health check.

## Constitution Check

*Checked against constitution v3.1.0.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First / hobby app | PASS | Standard, widely used extensions instead of custom machinery; three small dependencies, all common in Flask apps; no custom session table, audit table, or throttle module. |
| II. Library-Oriented Design | PASS | Email/password validation and hashing live in plain `accounts.py` (no Flask imports); routes only parse, call, and render. |
| III. Type Safety | PASS | New public functions typed; `mypy --strict` must pass. |
| IV. Data Privacy | PASS | No outbound calls or email; hashed passwords only; dev server on 127.0.0.1; production HTTPS via the ALB with login on every page. |
| V. Financial Correctness | PASS | Cycle/leftover code untouched; existing tests must still pass with `user_id` plumbing. |
| VI. Authentication & Data Isolation | PASS | Login-by-default via one `before_request` on the budget blueprint; all queries scoped; CSRF, cookie flags, rate limits; isolation tests per kind of record. |
| Dev Workflow: tracked migrations preserve rows | PASS | Idempotent migration; legacy rows keep their data with `user_id` NULL. |

No violations; Complexity Tracking is empty. Post-design re-check: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/006-login-authentication/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/web-routes.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
src/budget/
├── accounts.py      # NEW: normalize/validate email, validate password, hash/verify via Werkzeug
├── auth.py          # NEW: auth blueprint (login, logout, register, healthz), LoginManager + user loader,
│                    #      Limiter, safe-redirect helper
├── models.py        # + User (Flask-Login UserMixin)
├── db.py            # + users table/CRUD; migration adding user_id; every budget function takes user_id
├── app.py           # create_app: config from env, init extensions, CSRFProtect, ProxyFix (optional),
│                    #      no-store header, claim-legacy CLI command
├── routes.py        # budget blueprint: before_request requires login; pass current_user.id to db calls
├── wsgi.py          # unchanged apart from reading env
└── templates/
    ├── login.html, register.html     # NEW
    ├── layout.html                   # + signed-in email and sign-out form
    └── *.html                        # each POST form gains the hidden csrf_token field

tests/
├── unit/test_accounts.py             # NEW: email/password rules, hash/verify
└── integration/
    ├── conftest additions            # app with fixed secret key, login helper, two-account fixture
    ├── test_auth.py                  # NEW: login/logout/register, generic error, redirects, rate limit, CSRF
    ├── test_protection.py            # NEW: every budget route redirects anonymous users to /login
    ├── test_isolation.py             # NEW: account B cannot read/change/delete account A's records
    └── test_routes.py                # UPDATED: sign in first
scripts/dev-server.sh                 # sets BUDGET_ENV=development
pyproject.toml                        # + flask-login, flask-wtf, flask-limiter
```

**Structure Decision**: extend the existing single-package layout. Two new modules and
one new blueprint; no new directories.

## Deployment Prerequisites (outside this repo, `basso-infra`)

1. **Durable storage.** The Fargate task has no persistent volume, so the SQLite file,
   including every account, is erased on each deploy or Spot replacement. Public
   registration must not be opened until storage is durable (an EFS mount at `/data`
   with deployments that never run two tasks at once, or the planned Aurora feature).
2. **Session secret.** Create an SSM SecureString parameter and inject it as
   `BUDGET_SECRET_KEY` through the task definition's `secrets`; grant the execution role
   `ssm:GetParameters` on it.
3. **Proxy trust.** Set `BUDGET_TRUST_PROXY=1` so the app sees the real client IP and
   HTTPS scheme from the ALB.
4. **Health check.** Point the target group at `/healthz` (cleanup; `/` would also pass).
5. **Last:** open the security group to others only after the above and a smoke test.

## Complexity Tracking

None. (The dependencies are the standard, common choices; see research.md.)
