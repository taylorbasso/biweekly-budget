# Web Route Contract: Pay Cycle Leftover

The Flask app is the only interface for this feature (Constitution Principle II). All
routes are thin wrappers over the core module described in `data-model.md`: parse the
request, call `cycles.py` / `calculations.py` / `db.py`, render a template. No business
logic lives in `routes.py` or in templates.

Money amounts are entered and displayed in decimal dollars (e.g., `1500.00`) at the web
boundary; internally they are stored/computed as integer cents (see `data-model.md`).
Dates are entered and displayed as `YYYY-MM-DD`.

## `GET /`

The leftover view — the primary screen (spec US1).

- **Query params**: `date` (optional, `YYYY-MM-DD`, defaults to today — FR-007)
- **Response**: renders the resolved cycle's start date, end date, next pay date, pay
  amount, total expenses, and leftover amount.
- **No pay schedule recorded**: renders a prompt directing the user to `/pay-schedule`
  instead of a leftover figure.

## `GET /breakdown`

Category spending breakdown (spec US4).

- **Query params**: `date` (optional, `YYYY-MM-DD`, defaults to today — FR-014)
- **Response**: renders the same cycle `GET /` would resolve for that date, followed by
  one row per category with its total, including "Uncategorized" when applicable
  (FR-016). Displayed totals sum to the same total-expenses figure as `GET /` for that
  cycle (spec US4 AC2).
- **No pay schedule recorded**: same prompt as `GET /`.

## `GET /pay-schedule`

Shows the current pay schedule (or an empty form if none exists) with a form to set it.

## `POST /pay-schedule`

Create or replace the single pay schedule (spec US2).

- **Form fields**: `anchor_date` (`YYYY-MM-DD`), `amount` (decimal dollars)
- **Success**: redirects to `GET /pay-schedule` showing the stored values.
- **Errors**: `amount <= 0` or invalid date → re-renders the form with an inline
  validation message; the invalid submission is not persisted (FR-012).

## `GET /expenses`

Lists all recurring expenses (id, name, amount, recurrence rule, category) with links to
edit/remove each, and a link to the add form (spec US3). Empty list renders "no expenses
recorded" rather than an error.

## `GET /expenses/new`

Renders the add-expense form.

## `POST /expenses`

Create a recurring expense.

- **Form fields**: `name`, `amount` (decimal dollars), `recurrence_type`
  (`day_of_month` | `day_of_week`), `recurrence_value`, `category` (optional)
- **Success**: redirects to `GET /expenses`.
- **Errors**: `amount <= 0`, missing/invalid `recurrence_type`, `recurrence_value` out of
  range for the chosen type → re-renders the form with an inline validation message; not
  persisted (FR-012).

## `GET /expenses/<id>/edit`

Renders the edit form pre-filled with the expense's current values.

- **Unknown `id`**: 404.

## `POST /expenses/<id>/edit`

Update a recurring expense. Same fields and validation as `POST /expenses`.

- **Success**: redirects to `GET /expenses`.
- **Unknown `id`**: 404.

## `POST /expenses/<id>/delete`

Remove a recurring expense (spec US3 AC3).

- **Success**: redirects to `GET /expenses`.
- **Unknown `id`**: 404.

## Shared conventions

- All state-changing actions use `POST` (no `PUT`/`DELETE` — plain HTML forms only, no
  JS-driven requests, per Simplicity First).
- Validation errors re-render the originating form with a 400-range status and an inline
  message; they never silently drop the bad input or crash the process.
- The app binds to `127.0.0.1` only (Constitution Principle IV) — no route or
  configuration option exposes it on a network-accessible interface.
