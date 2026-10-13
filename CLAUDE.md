# biweekly-budget

Personal budgeting tool: computes how much discretionary money is left in the current
biweekly pay cycle, plus a per-category spending breakdown for that cycle. Flask web app
backed by PostgreSQL (Aurora Serverless v2 when deployed), deployed publicly at https://budget.taylorbasso.dev; multiple accounts
with strictly separate data (see feature `006-login-authentication`).

## Status

Spec-driven development via Spec Kit. Constitution and the first feature's spec/plan/tasks
exist; application code under `src/` does not yet. Check `specs/001-pay-cycle-leftover/tasks.md`
for current progress before assuming any module exists.

## Governing rules

`.specify/memory/constitution.md` is authoritative and overrides default instincts here:

- **Simplicity first**: single Flask app + PostgreSQL. No ORM, no frontend build tooling, no
  additional interface, until a concrete need exists.
- **Hobby app, KISS**: this is not a production service. Use the standard, widely used
  Flask solution (Flask-Login, Flask-WTF, Flask-Limiter, Werkzeug password hashing) rather
  than building custom machinery, and don't invent requirements the feature doesn't need.
  Bumping container memory/size is fine if it avoids complexity.
- **Library-oriented design**: pay-cycle/leftover/category-breakdown logic lives in plain
  Python modules independent of Flask; routes are thin wrappers (parse input, call the
  module, render a template). No business logic in routes or templates.
- **Type safety**: type hints on all public functions and data models; `mypy` must pass
  clean before a change is done.
- **Data privacy**: PostgreSQL only (private, encrypted, credentials outside the repo), no telemetry, no outbound email, no data sent to third
  parties. Dev server binds to `127.0.0.1` by default; public deployment only behind
  HTTPS with login required on every page. Passwords only as salted slow one-way hashes.
- **Authentication & data isolation**: every route requires login unless explicitly
  exempted; every query is scoped to the signed-in account; CSRF protection on all forms;
  secure session cookies; rate-limited login/registration; and an automated test proving
  one account cannot read or change another's data on every route touching budget data.
- **Correctness of financial math (non-negotiable)**: any code touching cycle boundaries,
  expense-to-cycle matching, or leftover/breakdown totals needs automated tests covering
  boundary conditions (cycle start/end, day-of-month clamping, leap years, month
  rollovers). Money is handled as integer cents internally, never floats.

## Where things are

- `specs/006-login-authentication/` — spec, plan, tasks for sign-in, registration, and per-account data
- `specs/001-pay-cycle-leftover/spec.md` — feature spec, user stories, functional requirements
- `specs/001-pay-cycle-leftover/plan.md` — tech stack, architecture, Constitution Check
- `specs/001-pay-cycle-leftover/data-model.md` — entities (PaySchedule, RecurringExpense, computed Cycle/LeftoverResult/CategoryBreakdown)
- `specs/001-pay-cycle-leftover/contracts/web-routes.md` — route-by-route contract
- `specs/001-pay-cycle-leftover/tasks.md` — task breakdown by user story
- `specs/001-pay-cycle-leftover/quickstart.md` — worked example (Jul 31 → Aug 14 pay cycle) for manual validation

Planned source layout (see `plan.md` for the authoritative version):

```text
src/budget/
├── models.py         # PaySchedule, RecurringExpense dataclasses + validation
├── cycles.py         # pay-date projection, cycle boundary resolution
├── calculations.py   # expense-occurrence matching, leftover, category breakdown
├── db.py              # PostgreSQL schema + CRUD (no ORM)
├── app.py             # Flask app factory
├── routes.py          # thin Flask view functions
└── templates/         # Jinja2 templates
tests/
├── unit/              # cycles.py, calculations.py, models.py
└── integration/       # Flask test client + db round trips
```

## Commands

```bash
./scripts/check.sh      # pytest tests/ + mypy src/ — must both pass clean
./scripts/dev-server.sh {start|stop|restart|status}   # local dev server, binds 127.0.0.1 only
```

### Sign-in and accounts

Every page requires sign-in (Flask-Login); registration is public at `/register` and each
account has its own data. Config via environment variables:

- `BUDGET_ENV` — `production` (default) or `development` (`dev-server.sh` sets it: HTTP
  cookies, fixed dev secret key).
- `BUDGET_SECRET_KEY` — session/CSRF signing key; **required in production**, the app
  refuses to start without it.
- `BUDGET_TRUST_PROXY=1` — trust one proxy hop (the ALB) for client IP and HTTPS scheme.

Database connection uses libpq's standard `PG*` environment variables (`PGHOST`, `PGPORT`,
`PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGSSLMODE`). Locally: PostgreSQL via
`brew install postgresql@16 && brew services start postgresql@16`, then
`createdb budget_dev && createdb budget_test`. `dev-server.sh` uses `budget_dev`;
`check.sh` and the tests use `budget_test` (tests wipe it). The schema is `src/budget/schema.sql`,
applied at startup; change it with idempotent statements. Deployed: Aurora PostgreSQL
Serverless v2 defined in `~/code/basso-infra` (pauses when idle; first request after a pause
is slow).

New routes go in the `budget` blueprint (`routes.py`), which requires login by default;
every `db.py` function takes `user_id` and filters on it. Add an isolation test
(`tests/integration/test_isolation.py`) for any new kind of record.

Templates auto-reload on every request (`TEMPLATES_AUTO_RELOAD = True` is set in
`create_app()`), so template/Jinja edits show up on the next browser refresh with no
restart needed. Python module changes (routes.py, calculations.py, etc.) still require
restarting the dev server — `./scripts/dev-server.sh restart`.

### `scripts/dev-server.sh`

Wraps starting/stopping/restarting the Flask dev server so there's one approvable
command instead of ad hoc `ps`/`kill`/`flask run` invocations:

```bash
./scripts/dev-server.sh start     # start if not already running (127.0.0.1:5001)
./scripts/dev-server.sh stop      # stop if running
./scripts/dev-server.sh restart   # stop + start — use after any src/budget/*.py change
./scripts/dev-server.sh status    # report whether it's running and its PID
```

It finds the server by whatever's listening on port 5001 (override with
`BUDGET_DEV_PORT`), so it safely takes over a server started outside the script too.
Logs go to `.dev-server.log` (gitignored) in the repo root. Port 5001, not the Flask
default 5000: macOS AirPlay Receiver squats on 5000 whenever nothing else is bound to
it, so a stopped dev server silently gets replaced by AirPlay and returns a
confusing 403 instead of connection-refused.

## Working here

- Follow `specs/001-pay-cycle-leftover/tasks.md` task-by-task; each task lists its exact
  file path.
- New features start with `/speckit-specify`, not by writing code directly — the spec/
  plan/tasks pipeline is how this project accumulates features.
- Any change that touches interfaces, dependencies, or the CLI/Flask boundary should be
  checked against the constitution before proceeding.
- When testing a UI/route change in a browser, use the chrome-devtools MCP tools
  (navigate, snapshot, click, fill) against the running dev server — not `curl`. Close
  the page (`mcp__chrome-devtools__close_page`) once done testing — don't leave it open.
- Only one dev server should ever be running at a time, on port 5001. Use
  `./scripts/dev-server.sh {start|stop|restart|status}` for all of it rather than manual
  `ps`/`kill`/`flask run` — it finds whatever's already on the port (even if started
  outside the script) and takes it over rather than leaving a second instance running on
  a different port.
