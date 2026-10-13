# Data Model: Login Authentication

Money stays integer cents (unchanged). Timestamps are UTC ISO-8601 text.

## New table: `users`

| Column | Type | Rules |
|--------|------|-------|
| `id` | INTEGER PK AUTOINCREMENT | |
| `email` | TEXT NOT NULL UNIQUE | stored trimmed and lowercased |
| `password_hash` | TEXT NOT NULL | Werkzeug scrypt string (includes salt and parameters); never the password |
| `created_at` | TEXT NOT NULL | |

Validation (in `accounts.py`, not SQL): email has a single `@` with non-empty local and
domain parts and is at most 254 characters; password is 12-128 characters, any characters.
The UNIQUE constraint makes simultaneous registrations of one email safe: one wins.

## Changed tables (ownership)

| Table | Change |
|-------|--------|
| `pay_schedule` | rebuilt: `id` INTEGER PK AUTOINCREMENT, `user_id` INTEGER UNIQUE REFERENCES `users(id)` ON DELETE CASCADE, `anchor_date`, `amount`. Replaces the `id = 1` singleton; the existing row is copied with `user_id` NULL |
| `recurring_expense` | `+ user_id` INTEGER REFERENCES `users(id)` ON DELETE CASCADE, indexed |
| `account` | `+ user_id` (same) |
| `credit_account` | `+ user_id` (same) |

`user_id` is nullable only so pre-existing rows survive the migration. Application code
never inserts NULL: every create function takes a required `user_id`. Every select,
update, and delete filters `WHERE user_id = ?`, so NULL-owned rows are invisible to every
account until claimed.

## Migration (idempotent, in `db.init_db`)

Same pattern as the existing `_migrate_*` functions (inspect `PRAGMA table_info`, then
alter):

1. `CREATE TABLE IF NOT EXISTS users`.
2. Add `user_id` to `recurring_expense`, `account`, `credit_account` if missing.
3. If `pay_schedule` has no `user_id`: create the new table, copy the old row (if any) with
   `user_id` NULL, drop the old table, rename the new one.
4. Create the `user_id` indexes.

All existing rows are preserved (FR-015). `PRAGMA foreign_keys = ON` is set on every
connection in `db.connect`.

## Claiming legacy data (`claim-legacy` command)

In one transaction: find the account by email; abort if missing or if it already owns any
budget row; set `user_id` on every NULL-owned row in all four tables; print counts.

## Python models (`models.py`)

```text
User(UserMixin): id: int, email: str     # password hash stays inside db.py / accounts.py
```

Existing `PaySchedule`, `RecurringExpense`, `Account`, `CreditAccount` dataclasses are
unchanged; ownership is carried by the `user_id` argument to `db.py`.
