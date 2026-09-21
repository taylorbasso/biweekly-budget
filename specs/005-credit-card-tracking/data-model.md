# Data Model: Credit Cards Tracking

## CreditAccount (new entity)

Represents a single tracked credit card or loan. Frozen dataclass in `models.py`,
following the exact shape of the existing `Account` and `RecurringExpense` entities.

| Field             | Type        | Notes |
|-------------------|-------------|-------|
| `id`              | `int \| None` | `None` for an unsaved instance; assigned by SQLite `AUTOINCREMENT` on insert |
| `name`            | `str`       | Required, non-empty after `.strip()` |
| `balance`         | `int`       | Integer cents. Must be `>= 0` |
| `interest_rate`   | `float`     | Annual percentage rate, e.g. `24.99` means 24.99% APR. Must be `>= 0` |
| `minimum_payment` | `int`       | Integer cents. Must be `>= 0` |
| `actual_payment`  | `int`       | Integer cents. Must be `>= 0`. `0` means "not set" — payoff calc falls back to `minimum_payment` (research.md Decision 2) |

**Validation** (raises `ValidationError`, same exception class already used by
`PaySchedule`/`RecurringExpense`/`Account`):
- `name` must not be empty/whitespace-only.
- `balance`, `minimum_payment`, `actual_payment` must each be `>= 0`.
- `interest_rate` must be `>= 0`.

No relationship to `PaySchedule`, `RecurringExpense`, or `Account` — a fully independent
entity/table, per the spec's Assumptions (standalone ledger, no cycle integration).

## Computed values (not persisted)

### `payoff_months(balance: int, interest_rate: float, payment: int) -> int | None`

Pure function in `calculations.py`. Returns:
- `0` if `balance <= 0` (already paid off)
- `None` if the balance will never reach zero at this payment (payment is `0`, or doesn't
  exceed the interest accruing each month)
- otherwise, the number of whole months (rounded up) to reach a zero balance, per
  research.md Decision 1.

### `effective_payment(account: CreditAccount) -> int`

Pure function in `calculations.py`. Returns `account.actual_payment` if `> 0`, else
`account.minimum_payment` (research.md Decision 2).

### `CreditAccountRow` (frozen dataclass, `calculations.py`)

| Field           | Type          | Notes |
|-----------------|---------------|-------|
| `account`       | `CreditAccount` | The underlying entry |
| `payoff_months` | `int \| None`   | Result of `payoff_months(...)` using `effective_payment(account)` |

### `CreditCardsTotals` (frozen dataclass, `calculations.py`)

| Field             | Type  | Notes |
|-------------------|-------|-------|
| `balance`         | `int` | Sum of `balance` across all accounts |
| `minimum_payment` | `int` | Sum of `minimum_payment` across all accounts |
| `actual_payment`  | `int` | Sum of `actual_payment` across all accounts |

No `payoff_months` field — the spec explicitly excludes payoff time from the Totals row
(FR-004) since summing a time-to-payoff across independent accounts is not a meaningful
number.

### `compute_credit_cards(accounts: list[CreditAccount]) -> tuple[list[CreditAccountRow], CreditCardsTotals]`

Pure function in `calculations.py` assembling the above for the page: one row per
account (in the order given — `db.list_credit_accounts` returns them ordered by `id`) plus
the totals.

## SQLite schema addition (`db.py`)

```sql
CREATE TABLE IF NOT EXISTS credit_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    interest_rate REAL NOT NULL DEFAULT 0,
    minimum_payment INTEGER NOT NULL DEFAULT 0,
    actual_payment INTEGER NOT NULL DEFAULT 0
);
```

Added to the `SCHEMA` string alongside the existing tables — no migration function needed
since this is a brand-new table (`CREATE TABLE IF NOT EXISTS` is itself idempotent for a
fresh table, matching how the `account` table was added in feature 004).

New CRUD functions in `db.py`, mirroring `list_accounts`/`get_account`/`create_account`/
`update_account`/`delete_account` exactly: `list_credit_accounts`, `get_credit_account`,
`create_credit_account`, `update_credit_account`, `delete_credit_account`.
