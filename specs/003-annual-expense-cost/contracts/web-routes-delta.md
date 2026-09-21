# Web Route Contract Delta: Annual Expense Cost

This feature adds one new route and one new nav link. It does not change the request or
response contract of any existing route documented in
`specs/001-pay-cycle-leftover/contracts/web-routes.md` or
`specs/002-home-page-charts/contracts/web-routes-delta.md`.

## `GET /annual-cost` (new)

- **Query params**: none.
- **Response**: renders a page listing every `RecurringExpense`, grouped by category
  (`Uncategorized` fallback), each with its computed annual cost (FR-001–FR-004):
  - Categories are ordered alphabetically; within a category, expenses are ordered by
    annual cost descending, ties broken by name ascending (FR-005).
  - Each category group shows a subtotal (FR-006).
  - The page shows a grand total across all expenses (FR-007).
  - The page is read-only — no create/edit/delete controls or forms are present
    (FR-010); editing remains on `GET /expenses` and its existing routes.
- **Response, when no recurring expenses exist**: an empty-state message is shown instead
  of an empty table, and the grand total is displayed as `$0.00` (FR-008).
- **Errors**: none expected — this route has no user-supplied input to validate.

## Navigation

- `layout.html`'s nav bar gains a new `<a href="/annual-cost">Annual Cost</a>` link,
  positioned after the existing "Expenses" link.

## Non-changes

- `GET /`, `GET /pay-schedule`, `POST /pay-schedule`, `GET /expenses`, and all expense
  CRUD routes (`POST /expenses`, `GET`/`POST /expenses/<id>/edit`,
  `POST /expenses/<id>/delete`) are unaffected by this feature.
- No new form fields, no new POST endpoints, no new persisted data or schema changes.
