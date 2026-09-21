---

description: "Task list for savings-runway implementation"
---

# Tasks: Savings Runway

**Input**: Design documents from `/specs/004-savings-runway/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/web-routes-delta.md, research.md, quickstart.md (all present)

**Tests**: Included, per plan.md's Constitution Check (money math needs dedicated coverage even though this isn't a cycle-boundary calculation) — `essential` persistence, `Account` validation, `monthly_equivalent`/`essential_monthly_burn`/`account_spendable`/`total_spendable`/`compute_runway` correctness including the zero-burn and zero-account edge cases, and route-level integration tests for the toggle and full account CRUD.

**Organization**: Tasks are grouped by user story from spec.md. US1 and US2 are both Priority P1 (tied) and are ordered as listed in spec.md; US3 is P2. A Foundational phase precedes them because, unlike feature 003, this feature introduces a genuinely new persisted entity (`Account`) and a schema change (`recurring_expense.essential`) that both US1 and US2 depend on — that shared groundwork is built once rather than duplicated per story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
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

**Purpose**: Persisted data model and core calculation math shared by both US1 (essential flag) and US2 (accounts + runway). Neither story's acceptance criteria can be verified without this.

- [X] T001 [P] Add `essential: bool = False` field to `RecurringExpense` in `src/budget/models.py` (data-model.md)
- [X] T002 [P] Add new frozen `Account` dataclass to `src/budget/models.py`: `id: int | None`, `name: str`, `balance: int`, `penalty_tax_percent: int = 0`, with `__post_init__` validation rejecting empty/whitespace-only name, negative balance, and `penalty_tax_percent` outside `0..100` (data-model.md)
- [X] T003 Add `account` table to `SCHEMA` and a `_migrate_add_essential` migration (mirroring the existing `_migrate_add_recurrence_anchor` pattern) for `recurring_expense.essential INTEGER NOT NULL DEFAULT 0` in `src/budget/db.py` (depends on T001, T002)
- [X] T004 In `src/budget/db.py`: update `_row_to_expense`, `list_expenses`'s/`get_expense`'s SELECT, `create_expense`, and `update_expense` to read/write `essential`; add `list_accounts`, `get_account`, `create_account`, `update_account`, `delete_account` mirroring the existing expense CRUD functions (depends on T003)
- [X] T005 [P] Add `monthly_equivalent(expense: RecurringExpense) -> Fraction` and `essential_monthly_burn(expenses: list[RecurringExpense]) -> Fraction` to `src/budget/calculations.py`, using `fractions.Fraction` per research.md Decision 2 (depends on T001)
- [X] T006 [P] Add `account_spendable(account: Account) -> Fraction`, `total_spendable(accounts: list[Account]) -> Fraction`, `RunwayResult` frozen dataclass (`monthly_essential_burn`, `total_spendable`, `months: float | None`), and `compute_runway(expenses, accounts) -> RunwayResult` (months is `None` when burn is zero, else `float(total_spendable / monthly_essential_burn)`) to `src/budget/calculations.py` (depends on T002, T005)

**Checkpoint**: Schema migrated, `Account` CRUD available, runway math implemented and unit-testable — ready for route/template work in US1 and US2.

---

## Phase 3: User Story 1 - Mark expenses as essential (Priority: P1)

**Goal**: The user can toggle an "Essential" checkbox per recurring expense on a new Runway tab, and it persists immediately.

**Independent Test**: Check the "Essential" box for an expense, reload `/runway`, confirm it's still checked; uncheck it, reload, confirm it's unchecked.

### Tests for User Story 1

- [X] T007 [P] [US1] Unit test in `tests/unit/test_models.py`: `RecurringExpense` defaults `essential` to `False`; can be constructed with `essential=True`
- [X] T008 [US1] Integration test in `tests/integration/test_routes.py`: seed an expense, `POST /runway/expenses/<id>/toggle-essential`, confirm the DB row's `essential` flips and the response redirects to `/runway`; confirm 404 for an unknown expense id

### Implementation for User Story 1

- [X] T009 [US1] Add `runway()` view (`GET /runway`) to `src/budget/routes.py`: load expenses via `db.list_expenses`, render new `runway.html` (depends on T004)
- [X] T010 [US1] Create `src/budget/templates/runway.html`: table of every expense with name, amount, and an "Essential" checkbox, each in its own `<form method="post">` targeting `/runway/expenses/<id>/toggle-essential` with `onchange="this.form.submit()"` (research.md Decision 5); empty-state message when there are no expenses (depends on T009)
- [X] T011 [US1] Add `toggle_essential(expense_id)` view (`POST /runway/expenses/<id>/toggle-essential`) to `src/budget/routes.py`: 404 if the expense doesn't exist, otherwise flip `essential` and persist via `db.update_expense`, then redirect to `GET /runway` (depends on T004, T009)
- [X] T012 [P] [US1] Add a "Runway" nav link to `src/budget/templates/layout.html`, positioned after the existing "Annual Cost" link

**Checkpoint**: User Story 1 is fully functional and testable independently — expenses can be marked essential and it sticks across reloads.

---

## Phase 4: User Story 2 - Enter account balances and see runway in months (Priority: P1)

**Goal**: The user can add named accounts with balances (and an optional per-account penalty/tax %), and the Runway tab shows total spendable money divided by monthly essential burn, in months.

**Independent Test**: With a known essential monthly burn and one or more accounts of known balances/haircuts, the displayed runway equals total spendable ÷ monthly burn (quickstart.md Scenarios A–D).

### Tests for User Story 2

- [X] T013 [P] [US2] Unit tests in `tests/unit/test_calculations.py`: `monthly_equivalent` equals `Fraction(annual_cost(expense), 12)` for `day_of_month`, `day_of_week`, and `biweekly` expenses; `essential_monthly_burn` sums only expenses with `essential=True` and is `Fraction(0)` when none are essential
- [X] T014 [P] [US2] Unit tests in `tests/unit/test_calculations.py`: `account_spendable` returns the full balance at 0% and the correctly reduced amount at a nonzero percent (e.g. $10,000 at 30% → $7,000); `total_spendable` sums across multiple accounts and is `Fraction(0)` with no accounts
- [X] T015 [P] [US2] Unit tests in `tests/unit/test_calculations.py`: `compute_runway` reproduces spec.md's worked examples (single $7,060/0% account against $2,000/month burn → 3.53 months; a $2,000/0% + $10,000/30% pair against $2,000/month burn → 4.5 months); `months is None` when burn is zero (FR-011); `months == 0.0` when spendable is zero and burn is nonzero (FR-012)
- [X] T016 [P] [US2] Unit tests in `tests/unit/test_models.py`: `Account` raises `ValidationError` for a negative balance, for `penalty_tax_percent` outside `0..100`, and for an empty/whitespace name

### Implementation for User Story 2

- [X] T017 [US2] Extend `runway()` in `src/budget/routes.py` to also load accounts via `db.list_accounts` and call `compute_runway(expenses, accounts)`, passing `accounts` and `result` to the template (depends on T006, T009)
- [X] T018 [US2] Extend `runway.html`: list each account (name, balance, penalty/tax %), an "Add account" link, and the computed runway — `"{months:.2f} months"` when `result.months is not None`, otherwise a "No essential expenses selected" message (FR-010, FR-011) (depends on T017)
- [X] T019 [US2] Add `account_new()` (`GET /runway/accounts/new`) and `account_create()` (`POST /runway/accounts`) views to `src/budget/routes.py`: parse `name`/`balance` (dollars, via the existing `_parse_dollars` helper)/`penalty_tax_percent` from form data, construct and validate an `Account`, `db.create_account`, redirect to `/runway`; 400 + re-render with `error` on `ValidationError`/`ValueError` (depends on T004)
- [X] T020 [US2] Create `src/budget/templates/account_form.html` for creating an account, mirroring `expense_form.html`'s structure and error display (depends on T019)
- [X] T021 [US2] Integration test in `tests/integration/test_routes.py`: seed an essential expense burning $2,000/month, create a single account ($7,060, 0%), confirm `GET /runway` shows "3.53 months"; add a second account ($10,000, 30%), confirm it shows "4.5 months" (quickstart.md Scenarios A–B) (depends on T018, T020)
- [X] T022 [P] [US2] Integration test in `tests/integration/test_routes.py`: with no essential expenses marked, `GET /runway` shows the no-essential-expenses message instead of a number; with an essential expense but zero accounts, it shows "0.00 months" (quickstart.md Scenarios C–D) (depends on T018)

**Checkpoint**: User Stories 1 and 2 both work independently — accounts can be created and the runway number is correct, including both edge cases.

---

## Phase 5: User Story 3 - Manage multiple accounts (Priority: P2)

**Goal**: The user can edit and remove existing accounts, not just create new ones.

**Independent Test**: Add several accounts, edit one's balance/percentage and confirm the runway recalculates, delete one and confirm it no longer contributes.

### Tests for User Story 3

- [X] T023 [P] [US3] Integration test in `tests/integration/test_routes.py`: `GET /runway/accounts/<id>/edit` pre-fills the form with the account's current values; `POST` with updated balance/percentage updates the DB row and the runway on `/runway` reflects the new value; 404 for an unknown account id
- [X] T024 [P] [US3] Integration test in `tests/integration/test_routes.py`: `POST /runway/accounts/<id>/delete` removes the account and its contribution from the displayed spendable total/runway; 404 for an unknown account id

### Implementation for User Story 3

- [X] T025 [US3] Add `account_edit()` (`GET /runway/accounts/<id>/edit`) and `account_update()` (`POST /runway/accounts/<id>/edit`) views to `src/budget/routes.py`, reusing `account_form.html` in edit mode; 404 if the account doesn't exist; 400 + re-render with `error` on validation failure (depends on T020)
- [X] T026 [US3] Add `account_delete()` (`POST /runway/accounts/<id>/delete`) view to `src/budget/routes.py`; 404 if the account doesn't exist, otherwise `db.delete_account` and redirect to `/runway` (depends on T004)
- [X] T027 [US3] Extend `runway.html`: add "Edit"/"Remove" controls per account row, mirroring `expenses_list.html`'s expense-actions column (depends on T018, T025, T026)

**Checkpoint**: All three user stories are independently functional — full account lifecycle plus essential-marking and runway math.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T028 [P] Confirm invalid account input (negative balance, out-of-range percentage, empty name) shows an inline error on `account_form.html` rather than a 500 (edge cases in spec.md)
- [X] T029 [P] Run `mypy src/` and resolve any type errors, including the `Fraction`-typed `calculations.py` additions and the new `Account`/`RunwayResult` dataclasses (Constitution Principle III gate)
- [X] T030 Walk through `quickstart.md` Scenarios A–D manually against the running app and confirm every figure matches
- [X] T031 Run `./scripts/check.sh` and confirm pytest + mypy both pass clean

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies within this feature; blocks every user story
- **User Story 1 (Phase 3)**: Depends on Foundational T004 (essential column + expense CRUD)
- **User Story 2 (Phase 4)**: Depends on Foundational T004/T006 (account CRUD + `compute_runway`) and US1's T009 (the `runway()` view/template must exist to extend)
- **User Story 3 (Phase 5)**: Depends on US2's T019/T020 (account creation route + form template to mirror/extend)
- **Polish (Phase 6)**: Depends on all user stories being complete

### Within Each Phase

- Foundational: models (T001, T002) before schema (T003) before db CRUD (T004); `calculations.py` additions (T005, T006) depend on the model fields but not on db.py
- US1: tests (T007, T008 — write first, confirm failing) → route (T009) → template (T010) → toggle route (T011); nav link (T012) is independent
- US2: tests (T013–T016) → route extension (T017) → template extension (T018) → account create route (T019) → form template (T020) → integration tests (T021, T022)
- US3: tests (T023, T024) can be written against the planned routes before T025/T026 exist, then implementation (T025, T026) → template update (T027)

### Parallel Opportunities

- T001 and T002 (different concerns within the same file, but non-overlapping edits) can be done together; T005/T006 can proceed once T001/T002 land
- T007 (unit test) can be written in parallel with T008 (integration test) — different files
- T012 (nav link) can proceed in parallel with T010/T011 once T009 exists
- T013, T014, T015, T016 are all independent test additions and can be written in parallel once Phase 2 lands
- T023 and T024 can be written in parallel; T028 and T029 (Polish) can run in parallel

---

## Parallel Example: Foundational + User Story 1

```bash
# T001 and T002 touch the same file but different dataclasses — fine to do back-to-back;
# T012 (nav link) can proceed in parallel with T010 (template) once T009 (route) exists:
Task: "Add essential field to RecurringExpense in src/budget/models.py"
Task: "Add Runway nav link to src/budget/templates/layout.html"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 — both P1)

1. Complete Phase 2: Foundational — schema, models, and runway math, all unit-tested
2. Complete Phase 3: User Story 1 — essential checkbox toggles and persists
3. Complete Phase 4: User Story 2 — accounts can be created and the runway number is correct, including zero-burn/zero-account edge cases
4. **STOP and VALIDATE**: run `pytest tests/unit/test_calculations.py tests/unit/test_models.py tests/integration/test_routes.py`, then manually check `/runway` against `quickstart.md` Scenarios A–D
5. This is a usable MVP: a user can mark essentials, add at least one account, and see a correct runway figure

### Incremental Delivery

1. Foundational → US1 → US2 → validate → MVP usable (both P1 stories delivered together, per spec.md's tied priority)
2. Add User Story 3 → validate → full account edit/delete lifecycle
3. Polish (validation error handling, mypy clean, full quickstart walkthrough, `./scripts/check.sh` clean)

### Parallel Team Strategy

With more than one contributor:

1. Contributor A: Foundational (schema/models/calculations), then US1
2. Once Foundational's T004/T006 land, Contributor B can start US2's tests (T013–T016) against the planned function signatures while Contributor A finishes US1
3. Both stories converge on `runway.html` and `routes.py`, so coordinate on those files rather than assuming full independence
4. US3 (edit/delete) only starts once US2's account-creation route/template (T019/T020) exist to mirror

---

## Notes

- `[P]` tasks touch different files (or independent test functions in the same test file) with no unmet dependencies
- `[Story]` labels trace every task back to spec.md's user stories
- Money stays integer cents at rest in `models.py`/`db.py`; `calculations.py` uses `fractions.Fraction` only as an exact intermediate for the derived monthly-burn/runway math, converting to `float` once, at the final `months` value (research.md Decision 2)
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before moving on
