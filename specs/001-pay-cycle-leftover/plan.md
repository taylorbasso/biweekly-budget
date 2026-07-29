# Implementation Plan: Pay Cycle Leftover

**Branch**: `001-pay-cycle-leftover` | **Date**: 2026-07-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-pay-cycle-leftover/spec.md`

## Summary

Tell the user how much discretionary money they have left to spend in the current
biweekly pay cycle, and how that money breaks down by expense category. A single Flask
web app (server-rendered pages, local SQLite storage) lets the user record a pay
schedule (anchor date + amount, projected every 14 days) and recurring expenses (each
tied to a day-of-month or day-of-week, with an optional category), then view the
leftover amount and category breakdown for any pay cycle. Core cycle/leftover math lives
in a plain Python module independent of the Flask routes, per the constitution's
Library-Oriented Design principle.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Flask (web framework, server-rendered Jinja2 templates); no
ORM, no frontend build tooling

**Storage**: SQLite (local file), accessed via the standard library `sqlite3` module —
no ORM

**Testing**: pytest (unit tests for cycle/leftover/breakdown math and route-level
integration tests); mypy for static type checking

**Target Platform**: Local web app served by Flask's dev server bound to `127.0.0.1`
only, cross-platform (macOS/Linux/Windows wherever Python 3.11+ runs)

**Project Type**: Single project — Flask app + core library, single SQLite file

**Performance Goals**: N/A — single local user, page loads dominated by human reaction
time, not throughput

**Constraints**: Offline-capable, no outbound network calls, no telemetry, localhost-only
binding (Constitution Principle IV)

**Scale/Scope**: Single user, one pay schedule row, on the order of tens of recurring
expenses; no concurrency or multi-tenancy concerns

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Simplicity First (YAGNI) | Single Flask app + SQLite, no additional interface, no ORM, no frontend build tooling | PASS |
| II. Library-Oriented Design | Core module (`cycles`, `calculations`) holds all pay-cycle/leftover/breakdown logic; Flask routes are thin wrappers that call it and render templates | PASS |
| III. Type Safety & Static Checking | mypy required in dev workflow; type hints on all public functions and data models (see data-model.md) | PASS |
| IV. Local-First Data Privacy | SQLite local file only; dev server bound to `127.0.0.1`; no network calls, no telemetry | PASS |
| V. Correctness of Financial Calculations (NON-NEGOTIABLE) | pytest suite planned specifically for cycle-boundary, day-of-month clamping, and weekday-occurrence edge cases from spec.md's Edge Cases section | PASS |

No violations — Complexity Tracking is empty.

*Re-checked after Phase 1 design (data-model.md, contracts/, quickstart.md): still PASS,
no new violations introduced by the concrete design.*

## Project Structure

### Documentation (this feature)

```text
specs/001-pay-cycle-leftover/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── web-routes.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── budget/
    ├── __init__.py
    ├── models.py         # PaySchedule, RecurringExpense dataclasses + validation
    ├── cycles.py         # pay-date projection, cycle boundary resolution
    ├── calculations.py   # expense-occurrence matching, leftover, category breakdown
    ├── db.py              # sqlite3 schema + CRUD access (no ORM)
    ├── app.py             # Flask app factory, route registration
    ├── routes.py          # thin Flask view functions calling calculations.py/db.py
    └── templates/         # Jinja2 templates (pay schedule form, expense list/form,
                           # leftover view, category breakdown view)

tests/
├── unit/                 # cycles.py, calculations.py, models.py — boundary conditions
└── integration/          # Flask test client: route + db round trips
```

**Structure Decision**: Single project. `src/budget/` separates the interface-agnostic
core (`models.py`, `cycles.py`, `calculations.py`, `db.py`) from the Flask layer
(`app.py`, `routes.py`, `templates/`), per Constitution Principle II. No `contract/`
test directory — the interface contract for this project is the set of web routes
documented in `contracts/web-routes.md`, exercised by `tests/integration/`.

## Complexity Tracking

*No entries — Constitution Check passed with no violations.*
