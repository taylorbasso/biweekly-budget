# biweekly-budget

Personal budgeting tool: computes how much discretionary money is left in the current
biweekly pay cycle, plus a per-category spending breakdown for that cycle. Single user,
local-only, Flask web app backed by SQLite.

## Status

Spec-driven development via Spec Kit. Constitution and the first feature's spec/plan/tasks
exist; application code under `src/` does not yet. Check `specs/001-pay-cycle-leftover/tasks.md`
for current progress before assuming any module exists.

## Governing rules

`.specify/memory/constitution.md` is authoritative and overrides default instincts here:

- **Simplicity first**: single Flask app + SQLite. No ORM, no frontend build tooling, no
  additional interface, until a concrete need exists.
- **Library-oriented design**: pay-cycle/leftover/category-breakdown logic lives in plain
  Python modules independent of Flask; routes are thin wrappers (parse input, call the
  module, render a template). No business logic in routes or templates.
- **Type safety**: type hints on all public functions and data models; `mypy` must pass
  clean before a change is done.
- **Local-first privacy**: SQLite only, no network calls, no telemetry, dev server bound
  to `127.0.0.1` only — never exposed on the network by default.
- **Correctness of financial math (non-negotiable)**: any code touching cycle boundaries,
  expense-to-cycle matching, or leftover/breakdown totals needs automated tests covering
  boundary conditions (cycle start/end, day-of-month clamping, leap years, month
  rollovers). Money is handled as integer cents internally, never floats.

## Where things are

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
├── db.py              # sqlite3 schema + CRUD (no ORM)
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

Templates auto-reload on every request (`TEMPLATES_AUTO_RELOAD = True` is set in
`create_app()`), so template/Jinja edits show up on the next browser refresh with no
restart needed. Python module changes (routes.py, calculations.py, etc.) still require
restarting the dev server — `./scripts/dev-server.sh restart`.

### `scripts/dev-server.sh`

Wraps starting/stopping/restarting the Flask dev server so there's one approvable
command instead of ad hoc `ps`/`kill`/`flask run` invocations:

```bash
./scripts/dev-server.sh start     # start if not already running (127.0.0.1:5000)
./scripts/dev-server.sh stop      # stop if running
./scripts/dev-server.sh restart   # stop + start — use after any src/budget/*.py change
./scripts/dev-server.sh status    # report whether it's running and its PID
```

It finds the server by whatever's listening on port 5000 (override with
`BUDGET_DEV_PORT`), so it safely takes over a server started outside the script too.
Logs go to `.dev-server.log` (gitignored) in the repo root.

## Working here

- Follow `specs/001-pay-cycle-leftover/tasks.md` task-by-task; each task lists its exact
  file path.
- New features start with `/speckit-specify`, not by writing code directly — the spec/
  plan/tasks pipeline is how this project accumulates features.
- Any change that touches interfaces, dependencies, or the CLI/Flask boundary should be
  checked against the constitution before proceeding.
- When testing a UI/route change in a browser, use the chrome-devtools MCP tools
  (navigate, snapshot, click, fill) against the running dev server — not `curl`.
- Only one dev server should ever be running at a time, on port 5000. Use
  `./scripts/dev-server.sh {start|stop|restart|status}` for all of it rather than manual
  `ps`/`kill`/`flask run` — it finds whatever's already on the port (even if started
  outside the script) and takes it over rather than leaving a second instance running on
  a different port.
