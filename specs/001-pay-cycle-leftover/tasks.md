---

description: "Task list for pay-cycle-leftover implementation"
---

# Tasks: Pay Cycle Leftover

**Input**: Design documents from `/specs/001-pay-cycle-leftover/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/web-routes.md, research.md, quickstart.md (all present)

**Tests**: Included where the constitution mandates them (Principle V, NON-NEGOTIABLE: automated tests for cycle-boundary and leftover-calculation logic). Not included for plain CRUD form handling (US2, US3), which the constitution does not single out.

**Organization**: Tasks are grouped by user story from spec.md, in priority order (US1 P1, then US2/US4 P2, then US3 P3). US4 depends on shared logic built in US1 despite sharing US2's priority tier — noted explicitly below.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths are exact, per `plan.md`'s Project Structure

## Path Conventions

Single project, per `plan.md`:
- `src/budget/` — core module + Flask app
- `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup

**Purpose**: Project initialization

- [ ] T001 Create project structure: `src/budget/__init__.py`, `src/budget/templates/`, `tests/unit/`, `tests/integration/` per `plan.md`
- [ ] T002 Create `pyproject.toml` declaring Flask as a runtime dependency and pytest + mypy as dev dependencies; make the package installable (`pip install -e .`)
- [ ] T003 [P] Configure mypy in `pyproject.toml` (`[tool.mypy]`) targeting `src/budget`
- [ ] T004 [P] Configure pytest in `pyproject.toml` (`[tool.pytest.ini_options]`) pointing at `tests/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Storage, models, and app scaffolding that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Implement SQLite schema creation for `pay_schedule` and `recurring_expense` tables (per `data-model.md`) in `src/budget/db.py`
- [ ] T006 [P] Implement `PaySchedule` and `RecurringExpense` dataclasses with type hints and validation (`amount > 0`; `recurrence_value` in range for its `recurrence_type`) in `src/budget/models.py`
- [ ] T007 Implement `db.py` CRUD functions — `get_pay_schedule`, `set_pay_schedule`, `list_expenses`, `get_expense`, `create_expense`, `update_expense`, `delete_expense` — in `src/budget/db.py` (depends on T005, T006)
- [ ] T008 Implement Flask app factory `create_app()` in `src/budget/app.py`; dev server MUST bind to `127.0.0.1` only (Constitution Principle IV)
- [ ] T009 [P] Create base Jinja2 layout template in `src/budget/templates/layout.html`
- [ ] T010 [P] Create shared pytest fixtures (temp SQLite db path, Flask test client) in `tests/conftest.py`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Check leftover spending money (Priority: P1) 🎯 MVP

**Goal**: Given a recorded pay schedule and recurring expenses, report the leftover amount and cycle date range for any reference date.

**Independent Test**: Seed a pay schedule and expenses directly via `db.py`, then call the leftover calculation (or `GET /`) and verify the dollar figure and cycle range match the worked example in `quickstart.md` (paid Jul 31, next pay Aug 14).

### Tests for User Story 1 (constitution-mandated — Principle V)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Unit tests for pay-date projection and cycle boundary resolution — forward/backward projection, reference date exactly on the anchor, reference date before the anchor — in `tests/unit/test_cycles.py`
- [ ] T012 [P] [US1] Unit tests for day-of-month clamping (31st in a 30-day month, 29th/30th/31st in February) and day-of-week occurrence counting (exactly 2 occurrences in any 14-day cycle) in `tests/unit/test_calculations.py`
- [ ] T013 [P] [US1] Unit tests for leftover-calculation boundary cases: an occurrence exactly on the cycle start date, exactly on the cycle end date, and exactly on the next pay date (must be excluded) in `tests/unit/test_calculations.py`

### Implementation for User Story 1

- [ ] T014 [US1] Implement pay-date projection and cycle boundary resolution (`resolve_cycle(pay_schedule, reference_date) -> Cycle`) in `src/budget/cycles.py`
- [ ] T015 [US1] Implement expense-occurrence generation for a cycle, including day-of-month clamping and day-of-week matching (`occurrences_in_cycle(expenses, cycle) -> list[ExpenseOccurrence]`) in `src/budget/calculations.py` (depends on T014)
- [ ] T016 [US1] Implement leftover calculation (`compute_leftover(pay_schedule, occurrences, cycle) -> LeftoverResult`) in `src/budget/calculations.py` (depends on T015)
- [ ] T017 [US1] Implement `GET /` route in `src/budget/routes.py`, rendering the cycle range, pay amount, total expenses, and leftover amount — or a "set up your pay schedule" prompt if none exists (depends on T016, T008)
- [ ] T018 [US1] Create the leftover view template in `src/budget/templates/leftover.html`

**Checkpoint**: User Story 1 is fully functional and testable independently — this is the MVP.

---

## Phase 4: User Story 2 - Record pay schedule (Priority: P2)

**Goal**: User can set and update the pay schedule (anchor date + amount).

**Independent Test**: Submit the pay-schedule form, then confirm `GET /pay-schedule` shows the stored values and `GET /` uses them.

### Implementation for User Story 2

- [ ] T019 [US2] Implement `GET /pay-schedule` and `POST /pay-schedule` routes in `src/budget/routes.py`, with validation (`amount > 0`, valid date) that re-renders the form with an inline error on failure rather than persisting bad input
- [ ] T020 [US2] Create the pay-schedule form/display template in `src/budget/templates/pay_schedule.html`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 4 - Category spending breakdown (Priority: P2)

**Goal**: Per-category expense totals for the current pay cycle.

**Independent Test**: With categorized recurring expenses recorded, `GET /breakdown` returns per-category totals (including "Uncategorized") that sum to the same total `GET /` reports for that cycle.

**Note**: Builds directly on the expense-occurrence generation from User Story 1 (T015) — implemented after US1 for that reason, even though it shares US2's priority tier.

### Tests for User Story 4 (constitution-mandated — Principle V / spec SC-002, SC-005)

- [ ] T021 [P] [US4] Unit tests for category grouping — expenses with no category fall into "Uncategorized"; per-category totals sum exactly to the total from `compute_leftover` for the same cycle — in `tests/unit/test_calculations.py`

### Implementation for User Story 4

- [ ] T022 [US4] Implement category breakdown (`compute_breakdown(occurrences) -> CategoryBreakdown`) in `src/budget/calculations.py` (depends on T015)
- [ ] T023 [US4] Implement `GET /breakdown` route in `src/budget/routes.py` (depends on T022, T008)
- [ ] T024 [US4] Create the breakdown view template in `src/budget/templates/breakdown.html`

**Checkpoint**: User Stories 1, 2, and 4 all work independently.

---

## Phase 6: User Story 3 - Record and manage recurring expenses (Priority: P3)

**Goal**: Full CRUD for recurring expenses (add, view, edit, remove), each with a name, amount, recurrence rule, and optional category.

**Independent Test**: Add an expense via the form, confirm it appears in `GET /expenses` and affects a subsequent leftover/breakdown calculation; edit and remove it and confirm those changes are reflected too.

### Implementation for User Story 3

- [ ] T025 [US3] Implement `GET /expenses` (list) route in `src/budget/routes.py` and its template in `src/budget/templates/expenses_list.html`
- [ ] T026 [US3] Implement `GET /expenses/new` and `POST /expenses` routes in `src/budget/routes.py`, with validation (`amount > 0`; `recurrence_type`/`recurrence_value` valid for that type) that re-renders the form with an inline error on failure
- [ ] T027 [P] [US3] Create the add/edit expense form template in `src/budget/templates/expense_form.html`
- [ ] T028 [US3] Implement `GET /expenses/<id>/edit` and `POST /expenses/<id>/edit` routes in `src/budget/routes.py` (404 on unknown id; reuses `expense_form.html`)
- [ ] T029 [US3] Implement `POST /expenses/<id>/delete` route in `src/budget/routes.py` (404 on unknown id)

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T030 [P] Run mypy across `src/budget` and resolve any type errors (Constitution Principle III gate)
- [ ] T031 [P] Add `README.md` with setup and `flask run` instructions
- [ ] T032 Walk through `quickstart.md` Scenarios 1–5 manually against the running app and confirm every figure matches

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational only — independent of US1
- **User Story 4 (Phase 5)**: Depends on Foundational **and** on T015 from US1 (reuses expense-occurrence generation)
- **User Story 3 (Phase 6)**: Depends on Foundational only — independent of US1/US2/US4
- **Polish (Phase 7)**: Depends on all user stories being complete

### Within Each User Story

- Tests (where included) MUST be written and FAIL before implementation
- `cycles.py` before `calculations.py` before `routes.py` before templates
- Story complete before moving to the next priority tier

### Parallel Opportunities

- All Setup `[P]` tasks (T003, T004) can run together once T001–T002 exist
- Foundational `[P]` tasks (T006, T009, T010) can run together once T005 (or, for T006, independently) exists
- US1's three test tasks (T011, T012, T013) can run together, in parallel with each other, before implementation begins
- Once Foundational is done, US2 (Phase 4) and US3 (Phase 6) can be worked in parallel with US1 (Phase 3) by different contributors — only US4 (Phase 5) must wait on US1's T015

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 test-writing tasks together (all fail until T014-T016 exist):
Task: "Unit tests for pay-date projection and cycle boundary resolution in tests/unit/test_cycles.py"
Task: "Unit tests for day-of-month clamping and day-of-week occurrence counting in tests/unit/test_calculations.py"
Task: "Unit tests for leftover-calculation boundary cases in tests/unit/test_calculations.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything)
3. Complete Phase 3: User Story 1 — write tests, watch them fail, then implement `cycles.py` → `calculations.py` → route → template
4. **STOP and VALIDATE**: run `pytest tests/unit/`, then manually check `GET /` against `quickstart.md` Scenario 3 (seed data directly into SQLite since US2/US3 forms don't exist yet)
5. This is a usable MVP: it answers "how much do I have left to spend" given hand-seeded data

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add User Story 1 → validate → MVP usable (with seeded data)
3. Add User Story 2 → validate → pay schedule now editable via the UI
4. Add User Story 4 → validate → category breakdown visible
5. Add User Story 3 → validate → expenses now fully manageable via the UI, no more manual seeding
6. Polish (mypy clean, README, full quickstart walkthrough)

### Parallel Team Strategy

With more than one contributor:

1. Complete Setup + Foundational together
2. Once Foundational is done:
   - Contributor A: User Story 1, then User Story 4 (depends on US1's T015)
   - Contributor B: User Story 2
   - Contributor C: User Story 3
3. Stories integrate independently at the routes layer (each owns its own route + template files)

---

## Notes

- `[P]` tasks touch different files with no unmet dependencies
- `[Story]` labels trace every task back to spec.md's user stories
- Money is handled as integer cents internally (per `data-model.md`) — do not introduce floats into `cycles.py`/`calculations.py`
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before moving on
