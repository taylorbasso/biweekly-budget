# Data Model: Pay Cycle Leftover

## Persisted entities

### PaySchedule

Single-row table — one income source (per spec Assumptions).

| Field | Type | Constraints |
|---|---|---|
| id | integer PK | Always `1`; enforced singleton (insert-or-replace, never a second row) |
| anchor_date | date | Required |
| amount | integer (cents) | Required, `> 0` (FR-012) |

Amounts are stored as integer cents to avoid floating-point rounding error in money math.

### RecurringExpense

| Field | Type | Constraints |
|---|---|---|
| id | integer PK | Auto-increment |
| name | text | Required, non-empty |
| amount | integer (cents) | Required, `> 0` (FR-012) |
| recurrence_type | text enum | One of `day_of_month`, `day_of_week` (FR-004) |
| recurrence_value | integer | `day_of_month`: 1–31. `day_of_week`: 0–6 (Monday=0 .. Sunday=6, matching `datetime.date.weekday()`) |
| category | text, nullable | Optional (FR-004); `NULL`/empty displays as "Uncategorized" (FR-016) |

Validation:
- `recurrence_type = day_of_month` → `recurrence_value` must be in `1..31`.
- `recurrence_type = day_of_week` → `recurrence_value` must be in `0..6`.

## Computed (not persisted) concepts

These are produced on demand by the service layer from `PaySchedule` +
`RecurringExpense` rows; they have no table.

### Cycle

Derived from `PaySchedule` for a given reference date (FR-007, FR-008).

| Field | Type | Description |
|---|---|---|
| start_date | date | Most recent projected pay date on or before the reference date |
| end_date | date | Day immediately before `next_pay_date` |
| next_pay_date | date | `start_date + 14 days` |

Pay dates are projected as `anchor_date + 14*n days` for any integer `n` (positive or
negative), per FR-002 — the schedule is a fixed-interval arithmetic sequence, not a
stored log.

### ExpenseOccurrence

A concrete due-date instance of a `RecurringExpense` within a specific `Cycle`
(FR-006, FR-009).

| Field | Type | Description |
|---|---|---|
| expense_id | integer | FK to `RecurringExpense.id` |
| name | text | Copied from the expense |
| due_date | date | Concrete date within the cycle; for `day_of_month`, clamped to the last day of the month when the nominal day doesn't exist (FR-006) |
| amount | integer (cents) | Copied from the expense |
| category | text or "Uncategorized" | Copied from the expense, defaulted per FR-016 |

A given `RecurringExpense` contributes zero or more `ExpenseOccurrence`s to a single
cycle (a `day_of_week` rule on a 14-day cycle always yields exactly 2; a `day_of_month`
rule yields 0 or 1, since a 14-day window cannot span two occurrences of the same
calendar day-of-month). Every occurrence belongs to exactly one cycle (FR-013).

### LeftoverResult

Output of a leftover request (FR-011).

| Field | Type | Description |
|---|---|---|
| cycle | Cycle | The resolved cycle |
| pay_amount | integer (cents) | From `PaySchedule.amount` |
| occurrences | list[ExpenseOccurrence] | All occurrences due in the cycle |
| total_expenses | integer (cents) | Sum of `occurrences[].amount` |
| leftover_amount | integer (cents) | `pay_amount - total_expenses` |

### CategoryBreakdown

Output of a breakdown request (FR-014, FR-015).

| Field | Type | Description |
|---|---|---|
| cycle | Cycle | The resolved cycle |
| totals | list[(category: text, amount: integer cents)] | One entry per distinct category (including "Uncategorized") present in the cycle's occurrences |

Invariant: `sum(totals[].amount) == LeftoverResult.total_expenses` for the same cycle
(spec US4 Acceptance Scenario 2).

## Relationships

```
PaySchedule (1 row)  ──generates──>  Cycle (computed, per reference date)
RecurringExpense (N rows)  ──generates──>  ExpenseOccurrence (computed, per cycle)
Cycle + ExpenseOccurrence[]  ──aggregates into──>  LeftoverResult
Cycle + ExpenseOccurrence[]  ──groups into──>  CategoryBreakdown
```

## State transitions

None — `PaySchedule` and `RecurringExpense` are plain CRUD records with no status/workflow
field. `Cycle`, `ExpenseOccurrence`, `LeftoverResult`, and `CategoryBreakdown` are
stateless, recomputed on every request.
