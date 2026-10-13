# Data Model: Aurora Postgres Migration

Entities and their meaning are unchanged; only physical types change. Authoritative DDL lives in
`src/budget/migrations/0001_initial.sql` (to be written during implementation).

## Tables

| Table | Columns (type) | Notes |
|---|---|---|
| `users` | `id` BIGINT identity PK; `email` TEXT UNIQUE NOT NULL; `password_hash` TEXT NOT NULL; `created_at` TIMESTAMPTZ NOT NULL | email stored normalized (existing rule) |
| `pay_schedule` | `id` identity PK; `user_id` BIGINT UNIQUE NOT NULL → `users(id)` ON DELETE CASCADE; `anchor_date` DATE NOT NULL; `amount` BIGINT NOT NULL | one per account |
| `recurring_expense` | `id`; `user_id` NOT NULL → users CASCADE; `name` TEXT NOT NULL; `amount` BIGINT NOT NULL; `recurrence_type` TEXT NOT NULL; `recurrence_value` INTEGER NOT NULL; `category` TEXT; `recurrence_anchor` DATE; `essential` BOOLEAN NOT NULL DEFAULT false | index on `user_id` |
| `account` | `id`; `user_id` NOT NULL → users CASCADE; `name` TEXT NOT NULL; `balance` BIGINT NOT NULL; `penalty_tax_percent` INTEGER NOT NULL DEFAULT 0 | index on `user_id` |
| `credit_account` | `id`; `user_id` NOT NULL → users CASCADE; `name`; `balance` BIGINT; `interest_rate` DOUBLE PRECISION DEFAULT 0; `minimum_payment` BIGINT; `actual_payment` BIGINT; `credit_limit` BIGINT (all NOT NULL, default 0) | index on `user_id` |
| `schema_migrations` | `version` TEXT PK; `applied_at` TIMESTAMPTZ NOT NULL DEFAULT now() | new; migration bookkeeping |

`user_id` is `NOT NULL` on all owned tables (FR-009): there is no legacy unowned data.
