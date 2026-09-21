---

description: "Task list for credit-card-tracking implementation"
---

# Tasks: Credit Cards Tracking

**Input**: Design documents from `/specs/005-credit-card-tracking/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/web-routes-delta.md, research.md, quickstart.md (all present)

**Tests**: Included, per plan.md's Constitution Check (money math needs dedicated coverage even though this isn't a cycle-boundary calculation) — `CreditAccount` validation, `payoff_months`/`effective_payment`/`compute_credit_cards` correctness including every edge case in research.md Decision 1, and route-level integration tests for the full CRUD lifecycle and each payoff-time display state.

**Organization**: Tasks are grouped by user story from spec.md. US1 and US2 are both Priority P1 (tied); US3 and US4 are both P2. A Foundational phase precedes them because this feature introduces a genuinely new persisted entity (`CreditAccount`), a schema change, and core payoff math that US1's table rendering depends on directly (FR-003 requires the payoff-time column from the first render) — that shared groundwork is built once rather than duplicated per story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths are exact, per `plan.md`'s Project Structure

## Path Conventions

Single project, per `plan.md`:
- `src/budget/` — core module + Flask app (existing, from feature 001)
- `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup

No setup tasks — this feature adds no new dependency or app scaffolding; it extends the existing `src/budget/` package in place.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Persisted data model, storage, and core payoff math shared by all four user stories — none of their acceptance criteria can be verified without this.

- [X] T001 [P] Add `CreditAccount` frozen dataclass to `src/budget/models.py`: `id: int | None`, `name: str`, `balance: int`, `interest_rate: float`, `minimum_payment: int`, `actual_payment: int`, with `__post_init__` validation rejecting empty/whitespace-only name and negative `balance`/`interest_rate`/`minimum_payment`/`actual_payment` (data-model.md)
- [X] T002 [P] Add `credit_account` table to `SCHEMA` in `src/budget/db.py` per data-model.md's SQL (columns: `id`, `name`, `balance`, `interest_rate REAL NOT NULL DEFAULT 0`, `minimum_payment INTEGER NOT NULL DEFAULT 0`, `actual_payment INTEGER NOT NULL DEFAULT 0`)
- [X] T003 In `src/budget/db.py`, add `_row_to_credit_account`, `list_credit_accounts`, `get_credit_account`, `create_credit_account`, `update_credit_account`, `delete_credit_account`, mirroring the existing `Account` CRUD functions exactly (depends on T001, T002)
- [X] T004 [P] Add `payoff_months(balance: int, interest_rate: float, payment: int) -> int | None` and `effective_payment(account: CreditAccount) -> int` to `src/budget/calculations.py` per research.md Decision 1/Decision 2, using stdlib `math.log`/`math.ceil` (depends on T001)
- [X] T005 Add `CreditAccountRow` frozen dataclass (`account: CreditAccount`, `payoff_months: int | None`), `CreditCardsTotals` frozen dataclass (`balance: int`, `minimum_payment: int`, `actual_payment: int`), and `compute_credit_cards(accounts: list[CreditAccount]) -> tuple[list[CreditAccountRow], CreditCardsTotals]` to `src/budget/calculations.py` (depends on T001, T004)
- [X] T006 [P] Add a `payoff` Jinja filter to `src/budget/app.py` (registered alongside the existing `usd` filter) formatting `int | None` months as `"Paid off"` (0), `"Never at this rate"` (`None`), or `"{n} months"` (positive int) per FR-011 (depends on T004)

**Checkpoint**: Schema migrated, `CreditAccount` CRUD available, payoff math implemented and unit-testable — ready for route/template work in every user story.

---

## Phase 3: User Story 1 - View all balances at a glance (Priority: P1)

**Goal**: The user opens a new "Credit Cards" tab and sees every entry in a table (name, balance, minimum payment, actual payment, payoff time) with a Totals row summing balance/minimum payment/actual payment independently.

**Independent Test**: Seed a few `CreditAccount` rows directly in the DB, load `/credit-cards`, confirm the table renders each entry correctly and the Totals row shows correct independent sums (quickstart.md Scenario A).

### Tests for User Story 1

- [X] T007 [P] [US1] Unit tests in `tests/unit/test_calculations.py`: `compute_credit_cards` sums `balance`/`minimum_payment`/`actual_payment` independently across multiple accounts (matching quickstart.md Scenario A's figures) and returns an empty rows list with all-zero totals for an empty accounts list
- [X] T008 [US1] Integration test in `tests/integration/test_routes.py`: `GET /credit-cards` with no entries shows an empty state (no Totals row, or an all-zero one) and a link to add an entry; with entries seeded, shows one row per entry plus a Totals row with correct sums

### Implementation for User Story 1

- [X] T009 [US1] Add `credit_cards()` view (`GET /credit-cards`) to `src/budget/routes.py`: load accounts via `db.list_credit_accounts`, call `compute_credit_cards`, render new `credit_cards.html` (depends on T003, T005)
- [X] T010 [US1] Create `src/budget/templates/credit_cards.html`: table with columns Name/Balance/Interest Rate/Minimum Payment/Actual Payment/Payoff Time (using the `payoff` filter), a Totals row summing balance/minimum payment/actual payment with a blank payoff-time cell, and an empty-state message with an "Add" link when there are no entries (depends on T009, T006)
- [X] T011 [P] [US1] Add a "Credit Cards" nav link to `src/budget/templates/layout.html`, positioned after the existing "Runway" link

**Checkpoint**: User Story 1 is fully functional and testable independently — the table and Totals row render correctly from seeded data.

---

## Phase 4: User Story 2 - Add and edit entries (Priority: P1)

**Goal**: The user can add a new credit card/loan via a form (name, balance, interest rate, minimum payment, actual payment) and later edit any of its fields.

**Independent Test**: Use the add form to create an entry, confirm it appears in the table; edit one of its fields and confirm the change (and recalculated payoff time) is reflected (quickstart.md Scenarios A-B).

### Tests for User Story 2

- [X] T012 [P] [US2] Unit tests in `tests/unit/test_models.py`: `CreditAccount` raises `ValidationError` for an empty/whitespace name, a negative `balance`, a negative `interest_rate`, a negative `minimum_payment`, and a negative `actual_payment`
- [X] T013 [US2] Integration test in `tests/integration/test_routes.py`: `POST /credit-cards` with valid form data creates a new entry that appears in the table and Totals row; with a negative balance or non-numeric amount, returns 400 and re-renders the form with an error, creating nothing
- [X] T014 [US2] Integration test in `tests/integration/test_routes.py`: `GET /credit-cards/<id>/edit` pre-fills the form with the entry's current values (404 for an unknown id); `POST` with updated balance/actual payment updates the DB row and the payoff time shown on `/credit-cards` changes accordingly

### Implementation for User Story 2

- [X] T015 [US2] Add `_credit_account_from_form(credit_account_id)` helper (mirroring `_account_from_form`, using the existing `_parse_dollars` helper for money fields and parsing `interest_rate` as a plain float) plus `credit_account_new()` (`GET /credit-cards/new`) and `credit_account_create()` (`POST /credit-cards`) views to `src/budget/routes.py`; 400 + re-render with `error` on `ValidationError`/`ValueError` (depends on T003)
- [X] T016 [US2] Create `src/budget/templates/credit_account_form.html`, mirroring `account_form.html`'s structure and error display, with fields for name, balance (dollars), interest rate (percent), minimum payment (dollars), and actual payment (dollars, optional) (depends on T015)
- [X] T017 [US2] Add `credit_account_edit()` (`GET /credit-cards/<id>/edit`) and `credit_account_update()` (`POST /credit-cards/<id>/edit`) views to `src/budget/routes.py`, reusing `credit_account_form.html` in edit mode; 404 if the entry doesn't exist; 400 + re-render with `error` on validation failure (depends on T015, T016)
- [X] T018 [US2] Extend `credit_cards.html`: add an "Add credit card/loan" link and an "Edit" action per row, mirroring `runway.html`'s account-table actions column (depends on T010, T015, T016, T017)

**Checkpoint**: User Stories 1 and 2 both work independently — entries can be created and edited, and the table/Totals stay correct.

---

## Phase 5: User Story 3 - Delete an entry (Priority: P2)

**Goal**: The user can remove a credit card/loan entry, with a confirmation step to prevent accidental deletion.

**Independent Test**: Delete an existing entry and confirm it no longer appears in the table and is excluded from the Totals row; confirm a dismissed confirmation dialog leaves it in place (quickstart.md Scenario F).

### Tests for User Story 3

- [X] T019 [P] [US3] Integration test in `tests/integration/test_routes.py`: `POST /credit-cards/<id>/delete` removes the entry and the Totals row on `/credit-cards` updates to exclude it; 404 for an unknown id

### Implementation for User Story 3

- [X] T020 [US3] Add `credit_account_delete()` (`POST /credit-cards/<id>/delete`) view to `src/budget/routes.py`; 404 if the entry doesn't exist, otherwise `db.delete_credit_account` and redirect to `GET /credit-cards` (depends on T003)
- [X] T021 [US3] Extend `credit_cards.html`: add a "Remove" button per row inside a `<form method="post">` targeting the delete route, with `onclick="return confirm('Delete this entry?')"` per research.md's delete-confirmation decision (depends on T010, T020)

**Checkpoint**: All entry lifecycle operations (add/edit/delete) work; the table and Totals stay accurate through every mutation.

---

## Phase 6: User Story 4 - See estimated payoff time (Priority: P2)

**Goal**: Each entry's payoff-time column reflects a correct amortization estimate, including the "already paid off," "never at this rate," and zero-interest edge cases.

**Independent Test**: Create entries covering each case (normal payoff, zero balance, zero/insufficient payment, zero interest rate) and confirm the displayed payoff time matches a hand-calculated result for each (quickstart.md Scenarios A, C, D).

### Tests for User Story 4

- [X] T022 [P] [US4] Unit tests in `tests/unit/test_calculations.py` for `payoff_months`: `balance <= 0` → `0`; `payment <= 0` → `None`; `interest_rate == 0` → `math.ceil(balance / payment)`; `payment` at or below the monthly interest accrued on `balance` → `None`; a normal case (e.g. quickstart.md's Visa: $2,000 balance, 20% APR, $100 payment → 25 months) matches the hand-calculated amortization result within one period
- [X] T023 [P] [US4] Unit tests in `tests/unit/test_calculations.py` for `effective_payment`: returns `actual_payment` when it's `> 0`; falls back to `minimum_payment` when `actual_payment == 0`
- [X] T024 [P] [US4] Integration test in `tests/integration/test_routes.py`: seed three entries — one with a normal payoff, one paid off (`balance = 0`), one that will never pay off (`minimum_payment = actual_payment = 0`) — and confirm `GET /credit-cards` renders `"N months"`, `"Paid off"`, and `"Never at this rate"` respectively (quickstart.md Scenarios C-D)

### Implementation for User Story 4

- [X] T025 [US4] Verify `credit_cards.html`'s payoff-time cell uses the `payoff` filter from T006 consistently for every row (no ad-hoc formatting), and that the Totals row's payoff cell is left blank rather than attempting to aggregate it (FR-004) (depends on T010, T006)

**Checkpoint**: All four user stories are independently functional — full CRUD lifecycle plus correct payoff-time estimation across every edge case.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T026 [P] Confirm invalid credit-account input (negative balance/rate/payments, non-numeric text, empty name) shows an inline error on `credit_account_form.html` rather than a 500 (SC-005, edge cases in spec.md)
- [X] T027 [P] Run `mypy src/` and resolve any type errors, including the new `CreditAccount`/`CreditAccountRow`/`CreditCardsTotals` dataclasses and `payoff_months`'s `int | None` return type (Constitution Principle III gate)
- [X] T028 Walk through `quickstart.md` Scenarios A-F manually against the running app and confirm every figure and display string matches
- [X] T029 Run `./scripts/check.sh` and confirm pytest + mypy both pass clean

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies within this feature; blocks every user story
- **User Story 1 (Phase 3)**: Depends on Foundational T003/T005/T006 (CRUD + payoff math + display filter)
- **User Story 2 (Phase 4)**: Depends on Foundational T003 (CRUD) and US1's T009/T010 (the `credit_cards()` view/template must exist to extend)
- **User Story 3 (Phase 5)**: Depends on Foundational T003 and US1's T010 (template to extend with a delete button)
- **User Story 4 (Phase 6)**: Depends on Foundational T004/T005/T006 (payoff math already built) and US1's T010 (template already renders the payoff column) — this phase is primarily verification/edge-case testing of work done earlier, not new plumbing
- **Polish (Phase 7)**: Depends on all user stories being complete

### Within Each Phase

- Foundational: model (T001) and schema (T002) in parallel → db CRUD (T003) → payoff math (T004) → aggregate math (T005); display filter (T006) depends only on T004
- US1: tests (T007, T008 — write first, confirm failing) → route (T009) → template (T010); nav link (T011) is independent
- US2: tests (T012-T014) → form helper + create routes (T015) → form template (T016) → edit routes (T017) → template wiring (T018)
- US3: test (T019) → delete route (T020) → template button (T021)
- US4: tests (T022-T024) can be written immediately after Foundational lands (T004-T006), independent of US2/US3; verification task (T025) just double-checks the template from US1

### Parallel Opportunities

- T001 and T002 (different files) can be done together; T004 depends only on T001, not T002
- T007 (unit test) can be written in parallel with T008 (integration test) — different files
- T011 (nav link) can proceed in parallel with T010 once T009 exists
- T012 is independent of T013/T014 (different files) and can be written as soon as T001 lands
- T019 can be written as soon as T003/T010 exist, in parallel with US2 work
- T022, T023, T024 are all independent test additions and can be written in parallel as soon as Foundational (T004-T006) lands — they don't wait on US2 or US3
- T026 and T027 (Polish) can run in parallel

---

## Parallel Example: Foundational

```bash
# T001 and T002 touch different files with no interdependency:
Task: "Add CreditAccount dataclass to src/budget/models.py"
Task: "Add credit_account table to SCHEMA in src/budget/db.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 — both P1)

1. Complete Phase 2: Foundational — schema, model, CRUD, and payoff math, all unit-tested
2. Complete Phase 3: User Story 1 — table and Totals row render correctly from seeded data
3. Complete Phase 4: User Story 2 — entries can be added and edited through the UI
4. **STOP and VALIDATE**: run `pytest tests/unit/test_calculations.py tests/unit/test_models.py tests/integration/test_routes.py`, then manually check `/credit-cards` against `quickstart.md` Scenarios A-B
5. This is a usable MVP: a user can add cards/loans and see correct balances, totals, and payoff estimates

### Incremental Delivery

1. Foundational → US1 → US2 → validate → MVP usable (both P1 stories delivered together, per spec.md's tied priority)
2. Add User Story 3 (delete) → validate → full CRUD lifecycle
3. Add User Story 4 (payoff-time edge-case verification) → validate → all display states correct
4. Polish (validation error handling, mypy clean, full quickstart walkthrough, `./scripts/check.sh` clean)

### Parallel Team Strategy

With more than one contributor:

1. Contributor A: Foundational (model/schema/db), then US1
2. Once Foundational's T003/T005/T006 land, Contributor B can start US4's tests (T022-T024) against the planned function signatures while Contributor A finishes US1
3. Both US2 and US3 converge on `credit_cards.html` and `routes.py`, so coordinate on those files rather than assuming full independence
4. US3 (delete) only starts once US1's T010 (template) exists to extend with a delete button

---

## Notes

- `[P]` tasks touch different files (or independent test functions in the same test file) with no unmet dependencies
- `[Story]` labels trace every task back to spec.md's user stories
- Money (`balance`, `minimum_payment`, `actual_payment`) stays integer cents throughout; `interest_rate` is the one new non-money field, a plain `float` percentage (research.md, data-model.md)
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before moving on
