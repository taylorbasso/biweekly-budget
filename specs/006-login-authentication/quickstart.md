# Quickstart: Validating Login Authentication

Run guide only. Behaviour: [spec.md](spec.md). Routes: [contracts/web-routes.md](contracts/web-routes.md).
Tables: [data-model.md](data-model.md).

## Prerequisites

`pip install -e '.[dev]'` in `.venv` (installs Flask-Login, Flask-WTF, Flask-Limiter) and a
local database with some existing data.

## 1. Automated gates

```bash
./scripts/check.sh        # pytest tests/ + mypy src/ — both clean
```

New suites: `test_accounts`, `test_auth`, `test_protection`, `test_isolation`; existing
tests now sign in first.

## 2. Local walkthrough (chrome-devtools MCP against the dev server)

```bash
./scripts/dev-server.sh restart     # BUDGET_ENV=development, 127.0.0.1:5001
```

1. Open `http://127.0.0.1:5001/` signed out -> redirected to `/login`, no data shown.
   Also try `/expenses`, `/runway`, `/credit-cards` directly.
2. Register `a@example.com` with an 11-character password -> refused; with 12+ -> account
   created, empty home page. Existing data is NOT shown.
3. Sign out, press Back -> sign-in page, no cached data.
4. Wrong password vs unknown email -> identical message. Try 6 times for one email ->
   "Too many attempts", even with the correct password.
5. Register `b@example.com`, add an expense; sign in as `a` and open `b`'s expense edit URL
   -> 404.
6. Claim the old data:
   ```bash
   flask --app budget.wsgi claim-legacy --email a@example.com
   ```
   Sign in as `a` -> all pre-existing data present and unchanged; `b` still sees only own.
7. `/login?next=https://evil.example` then sign in -> lands on `/`.

Close the browser page when done.

## 3. Deployment checks (after the prerequisites in plan.md)

1. In `basso-infra`: SSM secret, `BUDGET_SECRET_KEY`, `BUDGET_TRUST_PROXY=1`, `/healthz`
   health check; `terragrunt apply`; then `python deploy/deploy.py`.
2. `curl -sI https://budget.taylorbasso.dev/` -> `302` to `/login`; `/healthz` -> `200`.
3. Sign in over HTTPS and confirm the session cookie is `HttpOnly`, `Secure`, `SameSite=Lax`.
4. Only once storage is durable: open the security group and register from another network.

## Success criteria mapping

| Check | Criteria |
|-------|----------|
| Step 1 protection and isolation suites | SC-002, SC-008 |
| Step 2.4 | SC-003, SC-004 |
| Step 2.3 | SC-006 |
| Step 2.6 | SC-007 |
| Test that stored hashes and logs contain no plaintext | SC-005 |
| Step 3.2 | SC-009 |
