# Research: Login Authentication

Design decisions for the points the spec left to planning. Guiding rule (Constitution
v3.1.0, Principle I): use the standard, widely used Flask solution; don't invent
requirements.

## D1. Password hashing

- **Decision**: Werkzeug's `generate_password_hash` / `check_password_hash` with the
  library defaults (scrypt, per-hash random salt, constant-time comparison). Wrapped in
  `accounts.py` so a different method is a one-file change.
- **Rationale**: already installed with Flask; the most common choice in Flask apps;
  satisfies "salted, slow, one-way".
- **Alternatives**: `argon2-cffi` (also common, one more dependency); bcrypt (72-byte
  limit). Neither adds value for a hobby app.

## D2. Sessions and login state

- **Decision**: Flask-Login with Flask's signed cookie session. Cookie flags:
  `HttpOnly`, `Secure` (production), `SameSite=Lax`. `session.permanent = True` with
  `PERMANENT_SESSION_LIFETIME = 12 hours`; Flask re-issues the cookie on each request, so
  this acts as a 12-hour idle timeout. `session.clear()` runs just before `login_user` so
  sign-in starts a fresh session. Sign-out calls `logout_user()` and clears the session.
- **Rationale**: the standard pattern. A copied cookie stays valid until it expires; the
  spec accepts that for a hobby app (no server-side revocation table).
- **Alternatives**: server-side session table (more code and a table to maintain).

## D3. Login required by default

- **Decision**: all budget routes live in the existing blueprint; add one
  `@bp.before_request` that calls `login_manager.unauthorized()` when
  `current_user.is_authenticated` is false. Auth routes live in a separate blueprint and
  are therefore public. `LoginManager.login_view = "auth.login"` makes the redirect carry
  `?next=`.
- **Rationale**: one hook covers every current and future budget route; no per-route
  decorators to forget.

## D4. CSRF

- **Decision**: Flask-WTF `CSRFProtect(app)` globally. Templates add
  `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` to each POST form.
  No WTForms form classes are needed.
- **Rationale**: the standard approach; central enforcement covers all existing forms.

## D5. Rate limiting

- **Decision**: Flask-Limiter with in-memory storage and `get_remote_address` as the
  default key. `POST /login`: `20 per 15 minutes` per source plus `5 per 15 minutes` per
  submitted email (second limit with an email key function). `POST /register`:
  `5 per hour` per source. Exceeding returns HTTP 429 with a generic message, before the
  password is checked.
- **Rationale**: standard extension; counters in memory are fine for one worker and reset
  on restart.
- **Known limits**: counts all attempts, not just failures; an attacker can burn a
  victim's 5 attempts per 15 minutes. Accepted for a hobby app.

## D6. Client IP and scheme behind the ALB

- **Decision**: when `BUDGET_TRUST_PROXY=1`, wrap the WSGI app in Werkzeug `ProxyFix`
  (`x_for=1, x_proto=1, x_host=1`). Off by default so a local client can't spoof headers.
- **Rationale**: without it every request appears to come from the ALB (rate limits would
  apply to everyone at once) and Flask thinks requests are plain HTTP (Secure cookies).

## D7. Secret key

- **Decision**: `BUDGET_SECRET_KEY` env var. In `BUDGET_ENV=development` a fixed dev
  value is used; otherwise the app refuses to start if it is missing. Tests set their own.
- **Rationale**: simple and fails loudly instead of running with a guessable key.

## D8. Data isolation

- **Decision**: add `user_id` to the four budget tables; every `db.py` function takes a
  required `user_id` and includes it in the `WHERE` (including update and delete). The
  singleton `pay_schedule` row becomes one row per user. Foreign keys are enabled per
  connection. Routes already `abort(404)` when a lookup returns `None`.
- **Rationale**: a required argument means a missed filter is a type error, not a leak.

## D9. Existing data and claiming

- **Decision**: the migration leaves existing rows with `user_id` NULL, which no query
  returns. `flask --app budget.wsgi claim-legacy --email <address>` assigns all NULL rows
  to that existing account in one transaction, refusing if the account already owns data.
- **Rationale**: registration alone can never reveal legacy data (FR-015), with almost no
  code.

## D10. Small response hardening

- **Decision**: one `after_request` sets `Cache-Control: no-store` on non-static
  responses (FR-011). The `next` parameter is accepted only when it is a relative path
  with a single leading `/` and no host.
- **Rationale**: both are one-liners that close concrete spec items.

## D11. Production storage durability

- **Finding**: the deployed task has no persistent volume, so accounts disappear on each
  deploy. Not a code issue, but it gates rollout (see plan.md Deployment Prerequisites).
- **Recommendation**: mount EFS at `/data` with overlap-free deployments, or do the Aurora
  feature first, before inviting anyone else.

## Dropped as over-engineering

Server-side session table and revocation, sign-in timing equalization, an auth-event
audit table with lockout windows, a route-registry meta-test, `__Host-` cookie prefix,
HSTS and extra security headers, a password blocklist, and per-account lockout counters.
