# Web Routes Delta: Credit Cards Tracking

All routes are new (this feature introduces the `/credit-cards` tab). Mirrors the shape of
the existing `Account` CRUD routes (`/runway/accounts/...`) documented in
`specs/001-pay-cycle-leftover/contracts/web-routes.md`.

## `GET /credit-cards`

Renders the Credit Cards page: a table of all `CreditAccount` entries (name, balance,
interest rate, minimum payment, actual payment, computed payoff time) plus a Totals row
(balance, minimum payment, actual payment summed; payoff-time cell blank/dash).

**Response**: 200, `credit_cards.html`.

## `GET /credit-cards/new`

Renders the add-entry form (empty).

**Response**: 200, `credit_account_form.html` with `account=None`.

## `POST /credit-cards`

Creates a new `CreditAccount` from form fields `name`, `balance` (dollars, converted to
cents), `interest_rate` (percent, e.g. `24.99`), `minimum_payment` (dollars),
`actual_payment` (dollars, optional — blank treated as `0`).

- **Success**: redirect to `GET /credit-cards`.
- **Validation failure** (negative amounts, non-numeric input, empty name): 400, re-render
  `credit_account_form.html` with `error` set, no row created.

## `GET /credit-cards/<int:credit_account_id>/edit`

Renders the edit form pre-filled with the existing entry's values.

- **Not found**: 404.
- **Response**: 200, `credit_account_form.html` with `account` set.

## `POST /credit-cards/<int:credit_account_id>/edit`

Updates the entry from the same form fields as create.

- **Not found**: 404.
- **Success**: redirect to `GET /credit-cards`.
- **Validation failure**: 400, re-render form with `error` set, no change persisted.

## `POST /credit-cards/<int:credit_account_id>/delete`

Deletes the entry. Confirmed client-side via a JS `confirm()` dialog on the delete
button (FR-007) before the form submits — no server-side confirmation step.

- **Not found**: 404.
- **Success**: redirect to `GET /credit-cards`.

## Navigation

`layout.html` gains a `Credit Cards` link in the nav bar, alongside `Leftover`,
`Pay Schedule`, `Expenses`, `Annual Cost`, `Runway`.
