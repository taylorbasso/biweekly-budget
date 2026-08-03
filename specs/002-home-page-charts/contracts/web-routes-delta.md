# Web Route Contract Delta: Home Page Cycle Charts

This feature adds no new routes. It changes the rendered response of one existing route
documented in `specs/001-pay-cycle-leftover/contracts/web-routes.md`.

## `GET /` (unchanged request contract, extended response)

- **Query params**: unchanged — `date` (optional, `YYYY-MM-DD`, defaults to today).
- **Response, when a pay schedule exists**: in addition to the existing leftover figures
  and expense list, the page now renders a pie chart (inline SVG) for the resolved
  cycle:
  - One slice per expense category with a nonzero total in the cycle (label =
    category name or `"Uncategorized"`), plus one Leftover slice when the cycle is not
    overspent (FR-001–FR-004, FR-006).
  - Each slice exposes its label and dollar amount on hover/inspection (FR-008), via an
    SVG `<title>` element on the slice — no JavaScript required.
  - When the cycle is overspent (`total_expenses > pay_amount`), no Leftover slice is
    drawn; the page instead displays the overspent amount as text near the chart
    (FR-009).
  - The chart reflects whichever cycle is currently selected via the existing
    `cycle-select-form` control on this page — changing the selection re-submits `GET /`
    with a new `date`, and the server re-renders the chart for that cycle's data
    (FR-006). No new client-side behavior is introduced; the existing
    `onchange="this.form.submit()"` mechanism already causes a full page reload.
- **Response, when no pay schedule exists**: unchanged — no chart is rendered, same
  "set up your pay schedule" prompt as before (FR-007).

## Non-changes

- `GET /breakdown`, `GET /pay-schedule`, `POST /pay-schedule`, `GET /expenses`, and all
  expense CRUD routes are unaffected by this feature.
- No new form fields, no new POST endpoints, no new persisted data.
