# Implementation Plan: Annual Expense Cost

**Branch**: `003-annual-expense-cost` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-annual-expense-cost/spec.md`

## Summary

Add a new read-only "Annual Cost" tab that lists every recurring expense with its
projected annual cost — computed as `amount × 12` (day-of-month), `amount × 52`
(day-of-week), or `amount × 26` (biweekly) — grouped by category (alphabetical, with an
"Uncategorized" fallback matching the existing Expenses tab), sorted by annual cost
descending within each group, with a per-category subtotal and a page-wide grand total.
This is a pure derived view over existing `RecurringExpense` records: no new
dependencies, no new persisted data, no new form. The multiplier table and the
grouping/sorting/totals logic live in `calculations.py` (a sibling to `CategoryBreakdown`
per Constitution Principle II); `routes.py` gains one thin `GET /annual-cost` view.

## Technical Context

**Language/Version**: Python 3.11+ (matches existing project)

**Primary Dependencies**: Flask, Jinja2 (both already in use). No new dependency.

**Storage**: N/A — no new tables or columns. Pure presentation layer over the existing
`RecurringExpense` records already loaded via `db.list_expenses`.

**Testing**: pytest — unit tests in `tests/unit/test_calculations.py` for the annual-cost
multiplier mapping, per-category sorting/tie-breaking, subtotals, and grand total
(including the zero-expense case), plus an integration assertion in
`tests/integration/test_routes.py` that `GET /annual-cost` renders successfully.

**Target Platform**: Same local Flask dev server bound to `127.0.0.1` only.

**Project Type**: Single project — extends the existing `src/budget/` package.

**Performance Goals**: N/A — single local user, same as features 001/002.

**Constraints**: No new runtime or dev dependency; read-only page (FR-010); annual cost
always computed from live data at request time, never cached or persisted (FR-009).

**Scale/Scope**: Same as 001/002 — single user, on the order of tens of expenses at
most; grouping/sorting computed fresh on every page load, negligible cost.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Simplicity First (YAGNI) | No new dependency, no new interface, no new persisted data; reuses the existing `RecurringExpense` model and the existing category-grouping convention | PASS |
| II. Library-Oriented Design | Multiplier table and `compute_annual_cost_breakdown` live in `calculations.py`, independent of Flask; `routes.py`'s `annual_cost()` view stays a thin wrapper (load expenses, call `calculations.py`, render template) | PASS |
| III. Type Safety & Static Checking | `AnnualCostItem`/`CategoryAnnualCost`/`AnnualCostBreakdown` are typed frozen dataclasses; the multiplier lookup is exhaustive over `RECURRENCE_TYPES` so mypy strict can verify it; mypy strict must pass | PASS |
| IV. Local-First Data Privacy | No new network calls, no new storage, no telemetry; still `127.0.0.1`-only | PASS |
| V. Correctness of Financial Calculations (NON-NEGOTIABLE) | Annual cost is a deterministic multiplication of an already-validated `amount` (integer cents), not a new cycle/date calculation, but boundary cases (multiplier-per-recurrence-type correctness, tie-breaking, zero-expense grand total, subtotal/grand-total exactness) get dedicated unit tests per SC-002 | PASS |

No violations — Complexity Tracking is empty.

*Re-checked after Phase 1 design (data-model.md, contracts/, quickstart.md): still PASS,
no new violations introduced by the concrete design.*

## Project Structure

### Documentation (this feature)

```text
specs/003-annual-expense-cost/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
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
    ├── calculations.py     # gains ANNUAL_COST_MULTIPLIERS, AnnualCostItem/CategoryAnnualCost/
    │                       # AnnualCostBreakdown dataclasses, compute_annual_cost_breakdown()
    ├── routes.py            # gains `annual_cost()` view: GET /annual-cost
    ├── templates/
    │   ├── layout.html      # gains "Annual Cost" nav link
    │   └── annual_cost.html # NEW — grouped table + subtotals + grand total, read-only
    └── static/
        └── style.css        # reuses existing table/heading styles; no new dependency

tests/
├── unit/
│   └── test_calculations.py   # extended — multiplier table, grouping/sorting/subtotals/
│                               # grand-total tests, including zero-expense case
└── integration/
    └── test_routes.py         # extended — GET /annual-cost renders successfully
```

**Structure Decision**: Single project, extending the existing `src/budget/` layout from
features 001/002. No new module — the annual-cost computation is added to
`calculations.py` per Constitution Principle II and Research Decision 2. One new route
and one new template file; `layout.html` and `routes.py` are edited in place.
`contracts/web-routes-delta.md` documents the new `GET /annual-cost` route since it's
genuinely new (unlike 002, which only changed an existing route's response).

## Complexity Tracking

*No entries — Constitution Check passed with no violations.*
