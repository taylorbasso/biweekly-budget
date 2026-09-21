# Phase 0 Research: Savings Runway

## Decision 1: Monthly-equivalent burn rate reuses `annual_cost()` ÷ 12

**Decision**: Add `monthly_equivalent(expense) = Fraction(annual_cost(expense), 12)` in
`calculations.py`, calling the existing `annual_cost()` function from the Annual Cost
feature rather than writing a new day-counting conversion.

**Rationale**: The user explicitly requested this reuse so the Annual Cost tab and the
Runway tab never disagree about what an expense "really" costs per unit time — both
derive from the same multiplier table (`ANNUAL_COST_MULTIPLIERS`). It also avoids a
second, subtly different definition of "a month" (e.g. 30 days vs. calendar month vs.
annual/12) living in two places.

**Alternatives considered**: A calendar-accurate monthly projection (actual occurrence
count per real month) was rejected — it would require picking a reference month,
produce a different number depending on when you look, and the spec/user already
settled on annual/12 for consistency with the existing feature.

## Decision 2: Use `fractions.Fraction` for burn rate and spendable total, not float or integer cents

**Decision**: `monthly_equivalent`, `essential_monthly_burn`, `account_spendable`, and
`total_spendable` all return `Fraction` values (still denominated in cents). The final
runway-in-months value is converted to `float` only at the last step, for display
rounded to two decimals.

**Rationale**: `annual_cost() / 12` is not a whole number of cents for `day_of_week`
(×52) or `biweekly` (×26) expenses (e.g. amount × 52 ÷ 12 = amount × 13/3). The
constitution requires integer-cents money with no floats for the app's core ledger
math (leftover/breakdown), but a monthly *rate* derived for this one display isn't a
stored ledger value — it's an intermediate used once to compute a ratio. Using `Fraction`
(stdlib, no new dependency) keeps every intermediate exact — no float rounding drift
accumulates across summing several expenses/accounts — and only the final human-facing
number is rounded, exactly once.

**Alternatives considered**:
- Plain `float` throughout — rejected: accumulates rounding error across sums before the
  one place where imprecision is actually acceptable (the final displayed months value).
- Force monthly-equivalent to integer cents (round early) — rejected: rounding each
  expense's monthly-equivalent before summing would make the total burn rate depend on
  rounding order/direction rather than being the true derived value, which is avoidable
  here at zero cost by just not rounding until the end.

## Decision 3: `essential` flag as a migrated boolean column, following the existing pattern

**Decision**: Add `essential INTEGER NOT NULL DEFAULT 0` to `recurring_expense`, applied
via the same `_migrate_add_*` pattern already used for `recurrence_anchor` in `db.py`
(`PRAGMA table_info` check + `ALTER TABLE ... ADD COLUMN ... DEFAULT 0`).

**Rationale**: SQLite booleans are conventionally stored as `INTEGER` 0/1; the project
already has a working, tested migration pattern for adding a column to this exact table.
Reusing it means no new migration mechanism is introduced (Simplicity First).

**Alternatives considered**: A separate `expense_flags` table — rejected as needless
indirection for a single boolean attribute of an existing entity.

## Decision 4: New `Account` entity gets full CRUD mirroring `RecurringExpense`

**Decision**: `Account` (id, name, balance, penalty_tax_percent) gets its own table and
the same create/read/update/delete shape as `RecurringExpense` in `db.py`, with routes
and a form template mirroring `expense_form.html`.

**Rationale**: The user wants to add, edit, and remove an arbitrary number of named
accounts — this is genuinely a new persisted entity, not a derived value, so it needs
the same CRUD shape already established and tested for expenses. Mirroring an existing,
working pattern is lower-risk than inventing a new one.

**Alternatives considered**: A single fixed-shape row (e.g. `savings_amount`,
`k401_amount`, `k401_haircut_pct` columns) — rejected per the user's explicit request
for an arbitrary number of named accounts, not a fixed set of fields.

## Decision 5: Essential toggle persists via a background `fetch()` POST, no full-page reload

**Decision**: Each expense row's "Essential" checkbox lives in its own small `<form>`
posting to `POST /runway/expenses/<id>/toggle-essential`. A small vanilla-JS file
(`static/runway.js`, mirroring the existing `expense_form.js` pattern — no framework, no
build step) listens for the checkbox's `change` event, fires `fetch(...)` against the
form's action, and then re-fetches `/runway` in the background to refresh just the
`#runway-result` element's contents.

**Rationale**: The first version of this used `onchange="this.form.submit()"`, a full
synchronous form submit that reloads the page. With a long expense list, that reset the
user's scroll position to the top on every checkbox click — reported directly during
manual browser validation. Doing the POST via `fetch()` avoids navigating at all, so the
checkbox's own state (already flipped by the browser) never needs to be re-rendered and
scroll position is untouched; only the runway result text is patched in afterward so the
displayed months figure still updates live.

**Alternatives considered**:
- A single "Save all" button submitting every checkbox at once — rejected because the
  spec requires each toggle to persist immediately (acceptance scenarios 1–2 of User
  Story 1), not batched.
- Full-page `this.form.submit()` (the original decision) — rejected after manual
  testing surfaced the scroll-reset UX problem above.
