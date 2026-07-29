# Biweekly Budget

A personal budgeting tool that answers one question: **how much money do I have left to
spend before my next paycheck?**

Given a biweekly pay schedule and a set of recurring expenses (rent on the 1st, an
investment transfer every Friday, etc.), it computes the discretionary amount left in
the current pay cycle, and a per-category breakdown of that cycle's spending.

## Status

This project is being built with [Spec Kit](https://github.com/github/spec-kit)'s
spec-driven workflow. As of now:

- ✅ Constitution ratified (`.specify/memory/constitution.md`, v2.0.0)
- ✅ Feature spec, plan, and tasks generated for the core feature
  (`specs/001-pay-cycle-leftover/`)
- ✅ Implemented: pay schedule, recurring expenses (CRUD), leftover calculation, and
  category breakdown all working end-to-end; `pytest` and `mypy` both pass clean

See `specs/001-pay-cycle-leftover/tasks.md` for the current task breakdown.

## How it works

- **Pay schedule**: one anchor pay date + amount. Future and past pay dates are
  projected every 14 days from that anchor — you don't log every paycheck individually.
- **Recurring expenses**: each has a name, a dollar amount, a recurrence rule (a
  day-of-month like "the 1st", or a day-of-week like "every Friday"), and an optional
  category.
- **Cycle**: the span from one pay date up to (but not including) the next. Every
  expense occurrence in that window gets subtracted from that cycle's paycheck to give
  the leftover amount.

Full behavior, edge cases, and a worked example live in
`specs/001-pay-cycle-leftover/spec.md` and `specs/001-pay-cycle-leftover/quickstart.md`.

## Tech stack

- Python 3.11+
- [Flask](https://flask.palletsprojects.com/) — server-rendered pages, no separate
  frontend build
- SQLite via the standard library `sqlite3` module — no ORM
- `pytest` for tests, `mypy` for static type checking

See `specs/001-pay-cycle-leftover/research.md` for why these were chosen over the
alternatives considered (Django, FastAPI, an ORM, `python-dateutil`).

## Running it (once implemented)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
flask --app src.budget.app run
```

The app binds to `127.0.0.1` only by design — see Constitution Principle IV — and is
never exposed on the network by default.

Run tests and type checks with:

```bash
pytest tests/
mypy src/
```

## Project structure

```text
.specify/            # Spec Kit config, constitution, templates
specs/                # Feature specs, plans, and tasks (one directory per feature)
src/budget/           # Application code (once implemented)
tests/                # Unit + integration tests (once implemented)
```

## Governing principles

Development is governed by `.specify/memory/constitution.md`: simplicity first (no
premature interfaces or dependencies), a clean split between core budget logic and the
Flask layer, mandatory type checking, local-first data privacy (SQLite only, localhost
only, no telemetry), and non-negotiable test coverage for the pay-cycle and
leftover-calculation math.
