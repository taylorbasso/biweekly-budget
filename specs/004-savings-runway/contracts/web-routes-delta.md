# Web Routes Delta: Savings Runway

New routes added to `src/budget/routes.py` (the existing blueprint). All existing
routes are unchanged.

## `GET /runway`

Renders the Runway tab: every essential expense (read-only) with its monthly
equivalent, every account with its balance/penalty-tax% and edit/delete links, an "Add
account" link, and the computed runway result.

**Response 200**: `runway.html` template, given:
- `expenses: list[RecurringExpense]` (all expenses, each rendered with its current
  `essential` state)
- `accounts: list[Account]`
- `result: RunwayResult`

No query parameters; always reflects live DB state (FR-013).

## ~~`POST /runway/expenses/<int:expense_id>/toggle-essential`~~ (removed 2026-10-20)

Removed with the FR-003 amendment. The `essential` flag is now set only through the
existing expense forms (`POST /expenses`, `POST /expenses/<id>/edit`, checkbox field
`essential`). The route had since moved to `/expenses/<id>/toggle-essential`; both paths
are gone.

## `GET /runway/accounts/new`

Renders `account_form.html` for creating a new account (`account=None`, `action=
"/runway/accounts"`), mirroring `GET /expenses/new`.

## `POST /runway/accounts`

Creates a new account from form fields `name`, `balance` (dollars, parsed like existing
`_parse_dollars`), `penalty_tax_percent`.

- **400** + re-rendered form with `error` on `ValidationError`/`ValueError` (negative
  balance, empty name, out-of-range percent, unparsable amount) — mirrors
  `POST /expenses`.
- **302** redirect to `GET /runway` on success.

## `GET /runway/accounts/<int:account_id>/edit`

Renders `account_form.html` pre-filled with the existing account
(`action="/runway/accounts/<id>/edit"`), mirroring `GET /expenses/<id>/edit`.

- **404** if `account_id` doesn't exist.

## `POST /runway/accounts/<int:account_id>/edit`

Updates the account from the same form fields as create.

- **404** if `account_id` doesn't exist.
- **400** + re-rendered form with `error` on validation failure.
- **302** redirect to `GET /runway` on success.

## `POST /runway/accounts/<int:account_id>/delete`

Deletes the account.

- **404** if `account_id` doesn't exist.
- **302** redirect to `GET /runway` on success.

## Navigation

`layout.html` gains a `<a href="/runway">Runway</a>` link alongside the existing tabs.
