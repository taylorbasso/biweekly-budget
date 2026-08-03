---

description: "Task list for home-page-charts implementation"
---

# Tasks: Home Page Cycle Charts

**Input**: Design documents from `/specs/002-home-page-charts/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/web-routes-delta.md, research.md, quickstart.md (all present)

**Tests**: Included for the slice-geometry module, per plan.md's Constitution Check (Principle V rationale: the chart must never visually misrepresent the underlying, already-tested leftover/breakdown totals) — boundary cases (zero-size slice omission, single full-circle slice, overspent percentage basis, percentages summing to 100%). One integration test file is added for route-level rendering, matching the "integration assertion" plan.md's Technical Context commits to. Not included for pure CSS/markup styling.

**Organization**: Tasks are grouped by user story from spec.md, in priority order (US1 P1, US2 P2, US3 P3). No Setup or Foundational phase is needed — this feature adds no new dependency, app scaffolding, or shared infra beyond what feature 001 already built; the one new module (`charts.py`) is scoped entirely to US1, mirroring how `cycles.py` was scoped to US1 in `specs/001-pay-cycle-leftover/tasks.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact, per `plan.md`'s Project Structure

## Path Conventions

Single project, per `plan.md`:
- `src/budget/` — core module + Flask app (existing, from feature 001)
- `tests/unit/`, `tests/integration/`

---

## Phase 1: User Story 1 - See spending breakdown at a glance (Priority: P1) 🎯 MVP

**Goal**: The home page shows a pie chart for the current cycle — one slice per expense category plus a leftover slice — built from the same totals already shown as text.

**Independent Test**: With a pay schedule and categorized recurring expenses recorded (the `quickstart.md` Scenario 1 dataset), loading `GET /` shows a pie chart whose slice amounts match `Housing` $1200, `Investments` $200, `Uncategorized` $15, `Leftover` $585, each inspectable via hover for its label and dollar amount.

### Tests for User Story 1 (constitution-committed — see plan.md Constitution Check, Principle V)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T001 [P] [US1] Unit tests for slice-geometry basics in `tests/unit/test_charts.py`: category totals + leftover produce one slice each, percentages sum to `100.0`, a zero-amount category is omitted entirely (data-model.md rule 1)
- [X] T002 [P] [US1] Unit tests for the single-slice edge case in `tests/unit/test_charts.py`: zero recorded expenses yields exactly one slice (`label="Leftover"`) with `is_full_circle=True` and `path_d=None` (research.md Decision 4)
- [X] T003 [P] [US1] Unit tests for deterministic color assignment in `tests/unit/test_charts.py`: same category set always yields the same colors across repeated calls; category slices are sorted by name; more than 8 categories wraps the palette (research.md Decision 3)

### Implementation for User Story 1

- [X] T004 [US1] Implement `ChartSlice` and `CycleChart` frozen dataclasses (per `data-model.md`) in `src/budget/charts.py`
- [X] T005 [US1] Implement `build_chart(pay_amount, totals, leftover_amount) -> CycleChart` in `src/budget/charts.py`: drop zero-amount categories, add/omit the Leftover slice, sort category slices by name, assign colors from a fixed 8-color palette (Leftover reserved separately), compute each slice's start/end angle and SVG arc `path_d` via `math.sin`/`math.cos`, and mark the sole remaining slice `is_full_circle=True` when only one slice remains (depends on T004)
- [X] T006 [US1] Wire `charts.build_chart` into the `leftover()` view in `src/budget/routes.py`: call `compute_breakdown` for the resolved cycle (already have `occurrences`), pass `result.pay_amount`, the breakdown totals, and `result.leftover_amount` into `build_chart`, and pass the resulting `CycleChart` to the template (depends on T005)
- [X] T007 [US1] Add the inline `<svg>` chart block to `src/budget/templates/leftover.html`: render one `<path>` (or `<circle>` when `is_full_circle`) per slice with a `<title>` child showing label and dollar amount, guarded by `pay_schedule is not none` and `chart.slices` being nonempty (depends on T006)
- [X] T008 [P] [US1] Add chart container and slice-color styling to `src/budget/static/style.css` (sizing, layout alongside the existing leftover text, dark-mode-aware container background)
- [X] T009 [US1] Integration test in `tests/integration/test_routes.py`: `GET /` with a seeded pay schedule and categorized expenses returns chart `<svg>`/`<path>` markup containing the expected slice count and labels (depends on T007)

**Checkpoint**: User Story 1 is fully functional and testable independently — this is the MVP.

---

## Phase 2: User Story 2 - Chart follows the selected cycle (Priority: P2)

**Goal**: Selecting a different cycle from the home page's existing cycle dropdown re-renders the chart for that cycle's data, with no stale values.

**Independent Test**: Load `GET /`, select a different cycle from the existing `cycle-select-form` dropdown, and confirm the resulting `GET /?date=...` response's chart slices match that cycle's category totals and leftover (not the previously displayed cycle's).

### Implementation for User Story 2

- [X] T010 [US2] Confirm (and adjust if needed) that `leftover()` in `src/budget/routes.py` builds the chart from the *resolved* cycle's `occurrences`/`result` (the one selected via `date`), not `current_cycle` (used only for populating the dropdown options) — the two must not be conflated (depends on T006)
- [X] T011 [P] [US2] Integration test in `tests/integration/test_routes.py`: requesting `GET /?date=<next-cycle-start>` returns chart markup reflecting that cycle's totals, distinct from the response for the default (current) cycle (depends on T010)

**Checkpoint**: User Stories 1 and 2 both work independently — the chart is never a second, disconnected source of truth from the rest of the page.

---

## Phase 3: User Story 3 - No data yet (Priority: P3)

**Goal**: A user with no pay schedule recorded sees the existing setup prompt, never a broken or empty chart.

**Independent Test**: With no pay schedule recorded, `GET /` renders the existing "set up your pay schedule" prompt and no chart markup at all.

### Implementation for User Story 3

- [X] T012 [US3] Confirm the `pay_schedule is None` early-return branch in `leftover()` (`src/budget/routes.py`) never calls `build_chart` and the template's chart block stays behind the existing `{% if pay_schedule is none %}` guard (depends on T007)
- [X] T013 [P] [US3] Integration test in `tests/integration/test_routes.py`: `GET /` with no pay schedule recorded contains the existing setup prompt and no `<svg>` chart markup (depends on T012)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T014 [P] Unit tests for the overspent edge case in `tests/unit/test_charts.py`: `total_expenses > pay_amount` yields `overspent=True`, no Leftover slice, `overspent_amount = total_expenses - pay_amount`, and category slice percentages sum to `100.0` against `total_expenses` rather than `pay_amount` (research.md Decision 5)
- [X] T015 Add overspent-amount text near the chart in `src/budget/templates/leftover.html`, shown when `chart.overspent` is true (FR-009)
- [X] T016 [P] Run mypy across `src/budget` and resolve any type errors, including the new `charts.py` (Constitution Principle III gate)
- [X] T017 Walk through `quickstart.md` Scenarios 1–5 manually against the running app and confirm every chart matches the expected slices and percentages

---

## Dependencies & Execution Order

### Phase Dependencies

- **User Story 1 (Phase 1)**: No dependencies on other phases in this feature — builds `charts.py` from scratch and wires it into the existing `GET /` route
- **User Story 2 (Phase 2)**: Depends on US1's T006 (the route must already call `build_chart` before its cycle-selection wiring can be confirmed/adjusted)
- **User Story 3 (Phase 3)**: Depends on US1's T007 (the template guard being confirmed requires the chart block to exist)
- **Polish (Phase 4)**: Depends on US1 being complete (T014 tests the same `charts.py` module built in Phase 1); T015 depends on T007

### Within Each User Story

- Tests MUST be written and FAIL before implementation (US1's T001–T003 before T004–T005)
- Dataclasses (T004) before `build_chart` (T005) before route wiring (T006) before template (T007) before styling (T008) before integration test (T009)

### Parallel Opportunities

- US1's three unit-test tasks (T001, T002, T003) can run together, in parallel with each other, before implementation begins
- T008 (CSS) can proceed in parallel with T009 (integration test) once T007 is done
- T011 and T013 (integration tests for US2/US3) can run in parallel with each other once their respective dependencies (T010, T012) are done
- T014 and T016 in Polish can run in parallel

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 test-writing tasks together (all fail until T004-T005 exist):
Task: "Unit tests for slice-geometry basics in tests/unit/test_charts.py"
Task: "Unit tests for the single-slice edge case in tests/unit/test_charts.py"
Task: "Unit tests for deterministic color assignment in tests/unit/test_charts.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: User Story 1 — write `tests/unit/test_charts.py` tests, watch them fail, then implement `charts.py` → wire into `routes.py` → template → CSS → integration test
2. **STOP and VALIDATE**: run `pytest tests/unit/test_charts.py tests/integration/test_routes.py`, then manually check `GET /` against `quickstart.md` Scenario 1
3. This is a usable MVP: the home page shows a correct pie chart for whatever cycle it currently defaults to

### Incremental Delivery

1. Add User Story 1 → validate → MVP usable (chart on the default/current cycle)
2. Add User Story 2 → validate → chart now stays correct when the user changes cycles
3. Add User Story 3 → validate → no-schedule state confirmed unbroken
4. Polish (overspent handling, mypy clean, full quickstart walkthrough)

### Parallel Team Strategy

With more than one contributor:

1. Contributor A: User Story 1 (the only phase with real implementation work)
2. Once US1's T006/T007 land, Contributor B can pick up US2 (T010–T011) while Contributor A continues to US3 (T012–T013) or Polish
3. All work lands in the same three files (`charts.py`, `routes.py`, `leftover.html`) plus tests, so coordinate on those rather than assuming full file-level independence across phases

---

## Notes

- `[P]` tasks touch different files (or independent test functions in the same new test file) with no unmet dependencies
- `[Story]` labels trace every task back to spec.md's user stories
- Money stays integer cents throughout `charts.py` — only convert to a display form (percent, SVG coordinates) at the edge, never back to float dollars
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before moving on
