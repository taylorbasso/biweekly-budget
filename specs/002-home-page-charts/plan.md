# Implementation Plan: Home Page Cycle Charts

**Branch**: `002-home-page-charts` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-home-page-charts/spec.md`

## Summary

Add a pie chart to the home page showing, for the currently selected pay cycle, one
slice per expense category plus one slice for leftover money — reusing the totals
already computed by `compute_leftover`/`compute_breakdown` (no new calculation, no new
persisted data). The chart is rendered as a server-generated inline SVG: a new
`charts.py` module turns cycle totals into slice geometry (angles, SVG arc paths,
deterministic colors), and `leftover.html` embeds the resulting SVG. This keeps the
constitution's "no frontend build tooling" and "no additional dependencies" constraints
intact — no JS charting library, no client-side computation.

## Technical Context

**Language/Version**: Python 3.11+ (matches existing project)

**Primary Dependencies**: Flask, Jinja2 (both already in use). No new dependency — chart
is a server-rendered inline SVG string built from stdlib `math` (trig for arc
endpoints), not a JS charting library.

**Storage**: N/A — no new tables or columns. The chart is a pure presentation layer over
existing `PaySchedule`/`RecurringExpense` data and the existing `LeftoverResult` /
`CategoryBreakdown` computations.

**Testing**: pytest — unit tests for the new slice-geometry function (percentages sum
correctly, zero-size slices omitted, overspent case omits the leftover slice, single
remaining slice renders a full circle) plus an integration assertion that `GET /`
still renders successfully with chart markup present when a pay schedule exists.

**Target Platform**: Same local Flask dev server bound to `127.0.0.1` only.

**Project Type**: Single project — extends the existing `src/budget/` package.

**Performance Goals**: N/A — single local user, same as feature 001.

**Constraints**: No new runtime or dev dependency; no frontend build tooling; chart
markup generated entirely server-side per request (Constitution Principle I).

**Scale/Scope**: Same as 001 — single user, on the order of tens of categories at most;
chart geometry computed on every page load, negligible cost.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Simplicity First (YAGNI) | No new dependency, no JS charting library, no frontend build tooling; chart is inline SVG generated server-side | PASS |
| II. Library-Oriented Design | New `charts.py` module holds all slice-geometry math, independent of Flask; `routes.py` stays a thin wrapper (call `charts.py`, pass result to template) | PASS |
| III. Type Safety & Static Checking | `charts.py` gets full type hints and a frozen dataclass for slice data; mypy strict must pass | PASS |
| IV. Local-First Data Privacy | No new network calls, no new storage, no telemetry; still `127.0.0.1`-only | PASS |
| V. Correctness of Financial Calculations (NON-NEGOTIABLE) | Chart slices are derived from already-tested `LeftoverResult`/`CategoryBreakdown` totals, not a new money calculation; slice-geometry itself gets boundary tests (zero categories, single slice, overspent, percentages summing to 100%) so the *visual* never silently misrepresents the underlying numbers | PASS |

No violations — Complexity Tracking is empty.

*Re-checked after Phase 1 design (data-model.md, contracts/, quickstart.md): still PASS,
no new violations introduced by the concrete design.*

## Project Structure

### Documentation (this feature)

```text
specs/002-home-page-charts/
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
    ├── charts.py          # NEW — cycle totals -> chart slices (angles, SVG path, color)
    ├── calculations.py    # unchanged — existing LeftoverResult/CategoryBreakdown source data
    ├── routes.py          # `leftover()` view gains a call to charts.py, passes slices to template
    ├── templates/
    │   └── leftover.html  # gains inline <svg> chart block + overspent text
    └── static/
        └── style.css       # gains chart container/legend styling

tests/
├── unit/
│   └── test_charts.py     # NEW — slice-geometry boundary tests
└── integration/            # existing route test(s) extended to assert chart markup present
```

**Structure Decision**: Single project, extending the existing `src/budget/` layout from
feature 001. One new module (`charts.py`) added alongside `calculations.py` per
Constitution Principle II; no new route, no new template file — `leftover.html` and
`routes.py` are edited in place. No `contracts/` route additions since `GET /` already
exists; `contracts/web-routes-delta.md` documents how its response changes.

## Complexity Tracking

*No entries — Constitution Check passed with no violations.*
