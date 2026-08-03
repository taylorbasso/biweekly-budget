# Quickstart: Home Page Cycle Charts

Validates the chart end-to-end, building on the same data used in
`specs/001-pay-cycle-leftover/quickstart.md` (paid Friday July 31, next paid Friday
August 14).

## Prerequisites

- Feature 001 fully set up: pay schedule recorded, and the three example expenses from
  001's Scenario 2 (`Rent` $1200/Housing, `Investment transfer` $100/Investments,
  `Streaming` $15/uncategorized) present.
- App running: `flask --app src.budget.app run`

## Scenario 1: Chart on the primary cycle (US1)

1. Open `http://127.0.0.1:5000/?date=2026-08-01`.
2. **Expected**: same figures as 001's Scenario 3 (total expenses $1415.00, leftover
   $585.00), plus a pie chart with 3 slices:
   - `Housing` — $1200.00 (~60% of the $2000 pay amount)
   - `Investments` — $200.00 (~10%)
   - `Uncategorized` — $15.00 (~0.75%)
   - `Leftover` — $585.00 (~29.25%)
3. Hovering/inspecting each slice shows its label and dollar amount (FR-008).

## Scenario 2: Chart follows the cycle selector (US2)

1. On the same page, use the existing cycle dropdown to select the next cycle
   (`2026-08-14`–`2026-08-27`).
2. **Expected**: the page reloads (`GET /?date=2026-08-14`) and the chart updates to
   that cycle's category totals and leftover — no stale slices from the previous cycle.

## Scenario 3: No expenses in the cycle (Edge Case)

1. Pick a reference date whose cycle has zero expense occurrences (e.g., far enough in
   the future that none of the sample recurring expenses land in it, if applicable, or a
   database with a pay schedule but no expenses recorded at all).
2. **Expected**: chart renders a single full-circle "Leftover" slice for the entire pay
   amount (Research Decision 4 — full circle, not a degenerate arc).

## Scenario 4: Overspent cycle (FR-009)

1. Temporarily add a large enough expense that a cycle's total expenses exceed the pay
   amount (e.g., a one-off day-of-month expense larger than $2000).
2. Open `/` for that cycle.
3. **Expected**: chart shows only category slices (summing to 100% of *expenses*, not
   pay amount — Research Decision 5), no Leftover slice, and the page displays the
   overspent amount as text near the chart.
4. Remove the temporary expense afterward to restore the baseline dataset.

## Scenario 5: No pay schedule recorded (US3)

1. Against a fresh database with no pay schedule set, open `/`.
2. **Expected**: existing "set up your pay schedule" prompt renders, no chart markup
   present.

## Automated validation

```bash
mypy src/
pytest tests/
```

`tests/unit/test_charts.py` covers the slice-geometry boundary cases exercised manually
above (zero-size slice omission, single full-circle slice, overspent percentage basis,
percentages summing to 100%). Both commands MUST pass before the feature is considered
complete (Constitution Principles III and V).
