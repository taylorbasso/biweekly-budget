# Implementation Plan: Savings Runway

**Branch**: `004-savings-runway` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-savings-runway/spec.md`

## Summary

Add a new "Runway" tab where the user marks recurring expenses "essential" (persisted,
toggled immediately from the tab) and manages an arbitrary number of named accounts
(persisted, each with a balance and its own optional penalty/tax %). The page computes
and displays how many months the total spendable balance (each account's balance after
its own haircut) would cover the combined monthly-equivalent cost of essential expenses
only. Monthly-equivalent cost reuses the existing `annual_cost()` function (÷12) added
for the Annual Cost feature. All new business math lives in `calculations.py`; two new
CRUD-style route groups (`essential` toggle, `Account` CRUD) stay thin wrappers over
`db.py`.

## Technical Context

**Language/Version**: Python 3.11+ (matches existing project)

**Primary Dependencies**: Flask, Jinja2 (already in use), stdlib `fractions.Fraction`
for exact intermediate math. No new third-party dependency.

**Storage**: SQLite, via the existing `db.py` (no ORM). One new column
(`recurring_expense.essential`) added via migration, one new table (`account`).

**Testing**: pytest — unit tests in `tests/unit/test_calculations.py` for
`monthly_equivalent`, `essential_monthly_burn`, `account_spendable`, `total_spendable`,
and `compute_runway` (including the zero-burn and zero-account edge cases and
per-account haircut correctness); unit tests in `tests/unit/test_models.py` (or
alongside existing model tests) for `Account` validation; integration tests in
`tests/integration/test_routes.py` for `GET /runway`, the essential-toggle route, and
account CRUD routes.

**Target Platform**: Same local Flask dev server bound to `127.0.0.1` only.

**Project Type**: Single project — extends the existing `src/budget/` package.

**Performance Goals**: N/A — single local user, same scale as features 001–003.

**Constraints**: No new runtime dependency; essential-toggle and account CRUD persist
immediately (no batch save); runway always computed from live data at request time,
never cached (FR-013); money stays integer cents at rest, `Fraction` only as an
intermediate for the derived monthly-burn/runway math (see `research.md` Decision 2).

**Scale/Scope**: Same as prior features — single user, tens of expenses and a handful
of accounts at most; computed fresh on every page load, negligible cost.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Simplicity First (YAGNI) | No new dependency (stdlib `fractions` only), no new interface, no frontend build tooling — essential-toggle uses a plain auto-submitting form like the existing delete buttons | PASS |
| II. Library-Oriented Design | `monthly_equivalent`, `essential_monthly_burn`, `account_spendable`, `total_spendable`, `compute_runway` all live in `calculations.py`, independent of Flask; new routes (`runway`, `toggle_essential`, account CRUD) stay thin — parse input, call `db.py`/`calculations.py`, render template | PASS |
| III. Type Safety & Static Checking | `Account` and `RunwayResult` are typed frozen dataclasses; `Fraction` and `float \| None` are explicit types; mypy strict must pass | PASS |
| IV. Local-First Data Privacy | No new network calls, no telemetry; still SQLite + `127.0.0.1`-only | PASS |
| V. Correctness of Financial Calculations (NON-NEGOTIABLE) | Not a cycle-boundary/leftover calculation, so not strictly gated by this principle's literal scope — but it's still money math, so dedicated unit tests cover the zero-essential-expense divide-by-zero case, zero-account case, and per-account haircut precision (Decision 2 in research.md) regardless | PASS |

No violations — Complexity Tracking is empty.

*Re-checked after Phase 1 design (data-model.md, contracts/, quickstart.md): still PASS,
no new violations introduced by the concrete design.*

## Project Structure

### Documentation (this feature)

```text
specs/004-savings-runway/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── web-routes-delta.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── budget/
    ├── models.py           # RecurringExpense gains `essential: bool = False`;
    │                       # new Account frozen dataclass + validation
    ├── db.py                # SCHEMA gains `account` table; new migration for
    │                       # recurring_expense.essential; new list/get/create/
    │                       # update/delete_account functions; expense CRUD gains
    │                       # essential in insert/update/select
    ├── calculations.py      # gains monthly_equivalent(), essential_monthly_burn(),
    │                       # account_spendable(), total_spendable(), RunwayResult,
    │                       # compute_runway() — uses fractions.Fraction internally
    ├── routes.py            # gains: runway() GET /runway; toggle_essential() POST;
    │                       # account_new/account_create/account_edit/account_update/
    │                       # account_delete (mirrors expense CRUD routes)
    ├── templates/
    │   ├── layout.html      # gains "Runway" nav link
    │   ├── runway.html      # NEW — expense list w/ essential checkboxes, account
    │   │                    # list w/ edit/delete, computed runway result
    │   └── account_form.html # NEW — create/edit account form, mirrors expense_form.html
    └── static/
        └── style.css        # reuses existing table/form styles; no new dependency

tests/
├── unit/
│   ├── test_calculations.py   # extended — monthly_equivalent, essential_monthly_burn,
│   │                          # account_spendable, total_spendable, compute_runway
│   │                          # (zero-burn, zero-account, multi-account haircut cases)
│   └── test_models.py         # extended (or created if not yet present) — Account
│                              # validation (negative balance, out-of-range percent,
│                              # empty name)
└── integration/
    └── test_routes.py         # extended — GET /runway renders; toggle-essential
                               # persists and redirects; account create/edit/delete
                               # round-trip through the DB
```

**Structure Decision**: Single project, extending the existing `src/budget/` layout from
features 001–003. No new module — runway math is added to `calculations.py` per
Constitution Principle II, following the same placement as the Annual Cost feature's
`compute_annual_cost_breakdown`. One new template (`runway.html`) plus one new reusable
form template (`account_form.html`) mirroring `expense_form.html`; `layout.html`,
`models.py`, `db.py`, `routes.py`, and `test_calculations.py`/`test_routes.py` are edited
in place. `contracts/web-routes-delta.md` documents all new routes since none of them
exist today (unlike 002, which only changed an existing route's response).

## Complexity Tracking

*No entries — Constitution Check passed with no violations.*
