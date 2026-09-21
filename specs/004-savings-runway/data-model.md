# Phase 1 Data Model: Savings Runway

## `RecurringExpense` (extended)

Existing dataclass in `src/budget/models.py` gains one field:

| Field | Type | Notes |
|---|---|---|
| `essential` | `bool` | New. Defaults to `False`. No validation beyond being a bool — any expense can be marked essential or not, independent of category/recurrence. |

Persisted as `essential INTEGER NOT NULL DEFAULT 0` on the existing `recurring_expense`
table, added via a migration in `db.py` matching the existing `recurrence_anchor`
migration pattern.

## `Account` (new)

New frozen dataclass in `src/budget/models.py`:

| Field | Type | Notes |
|---|---|---|
| `id` | `int \| None` | `None` before insert, like `RecurringExpense.id`. |
| `name` | `str` | Required, non-empty after stripping whitespace. |
| `balance` | `int` | Integer cents. Must be `>= 0`. |
| `penalty_tax_percent` | `int` | Whole percent, `0..100` inclusive. Defaults to `0`. Represents the blended portion of this account's balance lost to early-withdrawal penalty and/or tax before it's usable. |

**Validation** (`__post_init__`, mirroring `RecurringExpense`/`PaySchedule`):
- `name.strip()` must be non-empty → `ValidationError`.
- `balance < 0` → `ValidationError`.
- `penalty_tax_percent` not in `0..100` → `ValidationError`.

Persisted in a new `account` table:

```sql
CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    penalty_tax_percent INTEGER NOT NULL DEFAULT 0
);
```

`db.py` gains `list_accounts`, `get_account`, `create_account`, `update_account`,
`delete_account`, mirroring the existing expense CRUD functions.

## Computed: `RunwayResult` (not persisted)

New frozen dataclass in `src/budget/calculations.py`:

| Field | Type | Notes |
|---|---|---|
| `monthly_essential_burn` | `Fraction` | Sum of `monthly_equivalent(e)` for every expense with `essential = True`. `Fraction(0)` when none are marked essential. |
| `total_spendable` | `Fraction` | Sum of each account's balance after its own `penalty_tax_percent` haircut. `Fraction(0)` when there are no accounts. |
| `months` | `float \| None` | `total_spendable / monthly_essential_burn` as a `float`, or `None` when `monthly_essential_burn == 0` (avoids divide-by-zero; template renders the "no essential expenses selected" message instead of a number). |

Supporting functions in `calculations.py`:

- `monthly_equivalent(expense: RecurringExpense) -> Fraction` — `Fraction(annual_cost(expense), 12)`.
- `essential_monthly_burn(expenses: list[RecurringExpense]) -> Fraction`
- `account_spendable(account: Account) -> Fraction` — `Fraction(account.balance * (100 - account.penalty_tax_percent), 100)`.
- `total_spendable(accounts: list[Account]) -> Fraction`
- `compute_runway(expenses: list[RecurringExpense], accounts: list[Account]) -> RunwayResult`

## Relationships

- `Account` has no foreign-key relationship to `RecurringExpense` — they're independent
  lists combined only at computation time by `compute_runway`.
- `RunwayResult` is derived fresh on every request from current `recurring_expense` and
  `account` rows; nothing about the runway itself is stored (FR-013).
