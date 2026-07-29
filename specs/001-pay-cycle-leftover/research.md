# Research: Pay Cycle Leftover

All Technical Context items had a clear, constitution-consistent default; none required
open-ended research. This document records the decisions made and why.

## Language & runtime

- **Decision**: Python 3.11+.
- **Rationale**: Confirmed by the user; standard library includes everything needed for
  date math (`datetime`, `calendar`) and local storage (`sqlite3`).
- **Alternatives considered**: None — user-specified.

## Web framework

- **Decision**: Flask, with server-rendered Jinja2 templates (no separate frontend
  build, no JS framework).
- **Rationale**: Constitution Principle I (Simplicity First) favors the smallest
  dependency footprint that does the job. Flask needs minimal boilerplate for a handful
  of routes (`/pay-schedule`, `/expenses`, `/`  for leftover, `/breakdown`) and has no
  built-in machinery (auth system, admin site, app registry) that goes unused for a
  single-user local tool.
- **Alternatives considered**: Django — richer built-ins (ORM, migrations, admin site)
  but brings an auth system, multi-app project scaffolding, and admin security surface
  that this two-table, single-user tool doesn't need; rejected as unjustified complexity
  under Principle I. FastAPI — good for JSON APIs, but this feature needs server-rendered
  HTML pages, not an API, so its request/response-model machinery adds no value here.

## Data storage

- **Decision**: Standard library `sqlite3` module, direct SQL, no ORM.
- **Rationale**: Constitution explicitly calls for local SQLite storage. The data model
  is small (two tables, no complex relationships), so an ORM would add abstraction
  without solving a real problem — direct Principle I violation if introduced.
- **Alternatives considered**: SQLAlchemy — rejected as unnecessary weight for two
  tables and simple queries.

## Date / recurrence math

- **Decision**: Standard library `datetime` + `calendar.monthrange` for day-of-month
  clamping (last day of month), and `datetime.date.weekday()` for day-of-week matching.
- **Rationale**: Both are stdlib, well-understood, and sufficient — no external date
  library needed for straightforward calendar arithmetic.
- **Alternatives considered**: `python-dateutil` — provides recurrence rules (`rrule`)
  that could compute occurrences directly, but pulls in a dependency for a calculation
  that's a few lines of stdlib code (project a pay date every 14 days; clamp a
  day-of-month; find weekday occurrences in a 14-day window).

## Testing & static checking

- **Decision**: `pytest` for tests, `mypy` for static type checking.
- **Rationale**: Constitution Principle III mandates static type checking; Principle V
  mandates automated tests for cycle-boundary and financial-calculation logic. `pytest`
  is the de facto standard for Python test ergonomics (fixtures, parametrization —
  useful for the many boundary cases in the spec's Edge Cases section). `mypy` is the
  most widely adopted Python type checker.
- **Alternatives considered**: `unittest` (stdlib) — viable but more verbose for the
  parametrized boundary-condition tests this feature needs.

## Target platform / constraints

- **Decision**: Local web app, cross-platform (macOS/Linux/Windows wherever Python 3.11+
  runs), served by Flask's built-in dev server bound to `127.0.0.1` only, fully
  offline — no outbound network calls, no telemetry.
- **Rationale**: Constitution Principle IV (Local-First Data Privacy) now explicitly
  requires localhost-only binding; this is a single-user personal tool with no need for
  a production WSGI server or public exposure.

## Scale/scope

- **Decision**: Single user, single SQLite file, on the order of tens of recurring
  expenses and one pay schedule row. No concurrency, no multi-user access.
- **Rationale**: Matches the spec's Assumptions (single income source, single currency,
  no payment-status tracking) — there is no scale dimension beyond "one person's
  household budget."
