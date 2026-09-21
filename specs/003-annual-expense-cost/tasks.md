---

description: "Task list for annual-expense-cost implementation"
---

# Tasks: Annual Expense Cost

**Input**: Design documents from `/specs/003-annual-expense-cost/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/web-routes-delta.md, research.md, quickstart.md (all present)

**Tests**: Included, per plan.md's Constitution Check (Principle V rationale: the page must never misrepresent the exact grand total / subtotal derived from already-validated expense amounts) — multiplier correctness per recurrence type, grouping/sort-order/tie-breaking, subtotal and grand-total exactness, and the zero-expense case. One integration test file is extended for route-level rendering, matching the "integration assertion" plan.md's Technical Context commits to.

**Organization**: Tasks are grouped by user story from spec.md, in priority order (US1 P1, US2 P2, US3 P3). No Setup or Foundational phase is needed — this feature adds no new dependency, app scaffolding, or shared infra; the one new module addition (`calculations.py` additions) is built in full during US1, mirroring how `charts.py` was built in full during US1 of `specs/002-home-page-charts/tasks.md`. Later phases add story-specific tests and confirm the already-built behavior against each story's acceptance criteria, rather than re-implementing from scratch.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact, per `plan.md`'s Project Structure

## Path Conventions

Single project, per `plan.md`:
- `src/budget/` — core module + Flask app (existing, from feature 001)
- `tests/unit/`, `tests/integration/`

---

## Phase 1: User Story 1 - View annual cost per expense (Priority: P1) 🎯 MVP

**Goal**: A new `/annual-cost` page shows every recurring expense with its computed annual cost (amount × 12/52/26 depending on recurrence type).

**Independent Test**: With the quickstart.md dataset recorded (`Rent` $1200/day-of-month-1/Housing, `Investment transfer` $100/day-of-week-Friday/Investments, `Streaming` $15/day-of-month-31/none), loading `GET /annual-cost` shows `Rent` at $14,400.00, `Investment transfer` at $5,200.00, and `Streaming` at $180.00.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T001 [P] [US1] Unit tests for the annual-cost multiplier in `tests/unit/test_calculations.py`: a day-of-month expense's annual cost = amount × 12, a day-of-week expense's = amount × 52, and a biweekly expense's = amount × 26 (research.md Decision 1, data-model.md multiplier table)

### Implementation for User Story 1

- [X] T002 [US1] Add `ANNUAL_COST_MULTIPLIERS` mapping and `AnnualCostItem`/`CategoryAnnualCost`/`AnnualCostBreakdown` frozen dataclasses to `src/budget/calculations.py` (per data-model.md)
- [X] T003 [US1] Implement `compute_annual_cost_breakdown(expenses: list[RecurringExpense]) -> AnnualCostBreakdown` in `src/budget/calculations.py`: compute each expense's annual cost via `ANNUAL_COST_MULTIPLIERS`, group by `expense.category or UNCATEGORIZED`, order categories alphabetically, sort items within each category by annual cost descending then name ascending, and compute each category's subtotal and the page's grand total (data-model.md Derivation rules 1-6; depends on T002)
- [X] T004 [US1] Add `annual_cost()` view (`GET /annual-cost`) to `src/budget/routes.py`: load expenses via `db.list_expenses`, call `compute_annual_cost_breakdown`, render `annual_cost.html` (depends on T003)
- [X] T005 [US1] Create `src/budget/templates/annual_cost.html`: a grouped table per category showing each expense's name and annual cost, a category subtotal, and a page grand total, with an empty-state message when there are no expenses (depends on T004)
- [X] T006 [P] [US1] Add an "Annual Cost" nav link to `src/budget/templates/layout.html`, positioned after the existing "Expenses" link
- [X] T007 [US1] Integration test in `tests/integration/test_routes.py`: `GET /annual-cost` with the quickstart dataset (`Rent`, `Investment transfer`, `Streaming`) returns 200 and the response body contains each expense's name with its computed annual cost ($14,400.00 / $5,200.00 / $180.00) (depends on T005, T006)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently — this is the MVP.

---

## Phase 2: User Story 2 - See total annual recurring spend (Priority: P2)

**Goal**: The page shows a single grand total across all recurring expenses, and an empty state (with a $0.00 total) when none are recorded.

**Independent Test**: With the quickstart.md dataset, the page's grand total reads $19,780.00 ($14,400.00 + $5,200.00 + $180.00). Against a database with no recurring expenses, the page shows an empty-state message and a $0.00 grand total.

### Tests for User Story 2

- [X] T008 [P] [US2] Unit tests for the grand total in `tests/unit/test_calculations.py`: `grand_total` equals the exact sum of every item's `annual_cost` across all categories for the quickstart dataset (19780_00 cents); an empty expense list yields `categories == []` and `grand_total == 0` (data-model.md Invariants; FR-007, FR-008)

### Implementation for User Story 2

- [X] T009 [US2] Confirm `annual_cost.html` renders `AnnualCostBreakdown.grand_total` and, when `categories` is empty, shows the empty-state message instead of an empty table (depends on T005; confirms FR-007/FR-008, already satisfied by the US1 implementation, against this story's acceptance criteria)
- [X] T010 [P] [US2] Integration test in `tests/integration/test_routes.py`: `GET /annual-cost` against a database with no recurring expenses shows the empty-state message and a $0.00 grand total (depends on T009)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently.

---

## Phase 3: User Story 3 - Compare costs by category, largest first (Priority: P3)

**Goal**: Expenses are grouped by category (with an "Uncategorized" fallback) and, within each category, ordered by annual cost descending so the largest costs stand out, with a subtotal per category.

**Independent Test**: With the quickstart.md dataset plus a second `Housing` expense (`Renters insurance`, annual cost $120.00), the `Housing` group lists `Rent` ($14,400.00) before `Renters insurance` ($120.00), and its subtotal reads $14,520.00.

### Tests for User Story 3

- [X] T011 [P] [US3] Unit tests for category grouping and sort order in `tests/unit/test_calculations.py`: expenses are grouped under their category (or `"Uncategorized"`), categories are ordered alphabetically, and within a category, items are ordered by `annual_cost` descending with ties broken by `name` ascending (data-model.md Derivation rules 2-4; FR-004, FR-005)
- [X] T012 [P] [US3] Unit tests for category subtotal correctness in `tests/unit/test_calculations.py`: each `CategoryAnnualCost.subtotal` equals the exact sum of its items' `annual_cost` (data-model.md Invariants; FR-006)

### Implementation for User Story 3

- [X] T013 [US3] Confirm `annual_cost.html` renders each category's subtotal next to its heading and lists items in the exact order produced by `compute_annual_cost_breakdown`, with no client-side re-sorting (depends on T005; confirms FR-004–FR-006, already satisfied by the US1 implementation, against this story's acceptance criteria)

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T014 [P] Confirm `annual_cost.html` contains no edit/delete controls or `<form>` elements anywhere on the page (FR-010 — read-only page)
- [X] T015 [P] Run `mypy src/` and resolve any type errors, including the new `calculations.py` additions (Constitution Principle III gate)
- [X] T016 Walk through `quickstart.md` Scenarios 1–5 manually against the running app and confirm every figure matches

---

## Dependencies & Execution Order

### Phase Dependencies

- **User Story 1 (Phase 1)**: No dependencies on other phases in this feature — builds the `calculations.py` additions from scratch and wires them into a new route/template
- **User Story 2 (Phase 2)**: Depends on US1's T005 (the template's grand-total/empty-state rendering must already exist before its acceptance criteria can be confirmed/tested)
- **User Story 3 (Phase 3)**: Depends on US1's T005 (the template's grouped rendering must already exist before its acceptance criteria can be confirmed/tested)
- **Polish (Phase 4)**: Depends on US1 being complete (T014 checks the same template built in Phase 1); T015 depends on T002/T003

### Within Each User Story

- Tests MUST be written and FAIL before implementation (US1's T001 before T002–T003)
- Dataclasses (T002) before `compute_annual_cost_breakdown` (T003) before route wiring (T004) before template (T005) before nav link (T006) before integration test (T007)

### Parallel Opportunities

- T006 (nav link) can proceed in parallel with T005 (template) since they're different files, though both must land before T007's integration test
- T008 (US2 unit tests) and T011/T012 (US3 unit tests) can all run in parallel with each other once T003 exists — they exercise the same already-built function from different angles
- T010 (US2 integration test) and T014/T015 (Polish) can run in parallel once their respective dependencies are done

---

## Parallel Example: User Story 1

```bash
# T001 (multiplier tests) can be written and run first; T006 (nav link) can proceed
# in parallel with T005 (template) once T004 (route) exists:
Task: "Unit tests for the annual-cost multiplier in tests/unit/test_calculations.py"
Task: "Add an 'Annual Cost' nav link to src/budget/templates/layout.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: User Story 1 — write `tests/unit/test_calculations.py` multiplier tests, watch them fail, then implement the `calculations.py` additions → route → template → nav link → integration test
2. **STOP and VALIDATE**: run `pytest tests/unit/test_calculations.py tests/integration/test_routes.py`, then manually check `GET /annual-cost` against `quickstart.md` Scenario 1
3. This is a usable MVP: the page shows correct per-expense annual costs, even before the grand total or category grouping are specifically validated

### Incremental Delivery

1. Add User Story 1 → validate → MVP usable (per-expense annual costs visible)
2. Add User Story 2 → validate → grand total and empty state specifically confirmed and tested
3. Add User Story 3 → validate → grouping/sort-order/subtotal specifically confirmed and tested
4. Polish (read-only confirmation, mypy clean, full quickstart walkthrough)

### Parallel Team Strategy

With more than one contributor:

1. Contributor A: User Story 1 (the only phase with real implementation work)
2. Once US1's T005 lands, Contributor B can pick up US2 (T008–T010) while Contributor A continues to US3 (T011–T013) or Polish
3. All work lands in the same few files (`calculations.py`, `routes.py`, `annual_cost.html`, `layout.html`) plus tests, so coordinate on those rather than assuming full file-level independence across phases

---

## Notes

- `[P]` tasks touch different files (or independent test functions in the same test file) with no unmet dependencies
- `[Story]` labels trace every task back to spec.md's user stories
- Money stays integer cents throughout `calculations.py` — only format as dollars in the template, never convert to float for the underlying calculation (Constitution: money handled as integer cents internally, never floats)
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before moving on
