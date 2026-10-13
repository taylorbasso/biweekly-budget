# Web Route Contract: Login Authentication

New routes are thin wrappers (Constitution Principle II): parse the form, call
`accounts.py` / `db.py`, render a template.

## Global behaviour

1. **Login by default.** Every budget route requires a signed-in account. Otherwise:
   `302 -> /login?next=<original path>` with no budget data in the response.
2. **CSRF.** Every `POST` must carry `csrf_token`, else `400` with no side effects. This
   includes all existing add/edit/delete/toggle forms.
3. **Caching.** Non-static responses carry `Cache-Control: no-store`.
4. **Cookie.** `HttpOnly`, `Secure` (production), `SameSite=Lax`; 12-hour lifetime
   refreshed on each request.
5. **Ownership.** Budget routes read and write only the signed-in account's rows. Another
   account's record id behaves like a nonexistent one: `404`.

Public endpoints (complete list): `auth.login`, `auth.register`, `auth.healthz`, `static`.

## `GET /login`

Signed in: `302 -> /`. Otherwise the sign-in form (email, password, hidden `next`,
`csrf_token`). `next` is honoured only if it is a relative path with a single leading `/`.

## `POST /login`

- **Success**: fresh session, `302 -> next` (validated) or `/`.
- **Failure** (unknown email or wrong password): `200`, same form, message "Invalid email
  or password." The email is retained; the password is never echoed.
- **Rate limited** (5 per 15 min per email, 20 per 15 min per source): `429`, "Too many
  attempts. Try again later." Password not checked.
- Passwords over 128 characters are treated as a normal failure without hashing.

## `POST /logout`

Requires `csrf_token`. Signs out, clears the session, `302 -> /login`. No `GET`.

## `GET /register` and `POST /register`

- `GET`: registration form (email, password, confirm, `csrf_token`); signed in -> `302 -> /`.
- `POST` success: account created, signed in, `302 -> /` (empty home page).
- `POST` errors (`200`, message, nothing stored): invalid email; password under 12 or over
  128 characters; confirmation mismatch; email already registered.
- Rate limited (5 per hour per source): `429`.

## `GET /healthz`

Public, no session or database access, `200` with body `ok`. For the load balancer.

## Existing routes

All routes in the budget blueprint (`/`, `/pay-schedule`, `/expenses*`, `/annual-cost`,
`/runway*`, `/credit-cards*`) are now protected, account-scoped, and CSRF-protected on
`POST`. Their inputs and computed outputs are unchanged for an account that owns the data.

## Operator command (not a web route)

```text
flask --app budget.wsgi claim-legacy --email <address>
```

Assigns all unowned (pre-feature) budget rows to the named existing account; errors if the
account is missing or already owns data; prints per-table counts.

## Configuration (environment)

| Variable | Meaning |
|----------|---------|
| `BUDGET_ENV` | `production` (default) or `development` |
| `BUDGET_SECRET_KEY` | session/CSRF signing key; required in production |
| `BUDGET_TRUST_PROXY` | `1` to trust one proxy hop (the ALB) for client IP and scheme |
| `BUDGET_DB_PATH` | unchanged |
