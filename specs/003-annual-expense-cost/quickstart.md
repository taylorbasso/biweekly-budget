# Quickstart: Annual Expense Cost

Validates the feature end-to-end using the same example expenses from
`specs/001-pay-cycle-leftover/quickstart.md` Scenario 2.

## Prerequisites

- Feature 001 fully set up, with the three example expenses recorded:
  - `Rent` — $1200.00, day-of-month `1`, category `Housing`
  - `Investment transfer` — $100.00, day-of-week `Friday`, category `Investments`
  - `Streaming` — $15.00, day-of-month `31`, no category
- App running: `flask --app src.budget.app run`

## Scenario 1: View annual cost per expense (US1)

1. Open `http://127.0.0.1:5000/annual-cost`.
2. **Expected**: each expense shows its computed annual cost:
   - `Rent`: $1200.00 × 12 = **$14,400.00**
   - `Investment transfer`: $100.00 × 52 = **$5,200.00**
   - `Streaming`: $15.00 × 12 = **$180.00**

## Scenario 2: Grand total across all expenses (US2)

1. On the same page, check the grand total.
2. **Expected**: `$14,400.00 + $5,200.00 + $180.00 = $19,780.00`.

## Scenario 3: Empty state (US2 edge case)

1. Against a fresh database with no recurring expenses recorded, open
   `http://127.0.0.1:5000/annual-cost`.
2. **Expected**: an empty-state message is shown (no table), and the grand total reads
   `$0.00`.

## Scenario 4: Grouped by category, largest first (US3)

1. With the three example expenses in place, open `http://127.0.0.1:5000/annual-cost`.
2. **Expected**: three category groups in alphabetical order —
   - `Housing` — subtotal $14,400.00 — contains `Rent` ($14,400.00)
   - `Investments` — subtotal $5,200.00 — contains `Investment transfer` ($5,200.00)
   - `Uncategorized` — subtotal $180.00 — contains `Streaming` ($180.00)
3. Add a second `Housing` expense, e.g. `Renters insurance` — $10.00, day-of-month `5`
   (annual cost $120.00).
4. **Expected**: the `Housing` group now lists `Rent` ($14,400.00) before `Renters
   insurance` ($120.00) — highest annual cost first — and its subtotal becomes
   $14,520.00. Remove `Renters insurance` afterward to restore the baseline dataset.

## Scenario 5: Read-only page (FR-010)

1. On `http://127.0.0.1:5000/annual-cost`, confirm there are no edit/delete controls or
   forms for any listed expense.
2. **Expected**: managing expenses (add/edit/delete) is only available via
   `http://127.0.0.1:5000/expenses`, unchanged by this feature.

## Automated validation

```bash
mypy src/
pytest tests/
```

`tests/unit/test_calculations.py` gains coverage for the multiplier table, per-category
sorting/tie-breaking, subtotals, and grand total (including the zero-expense case).
`tests/integration/test_routes.py` gains a `GET /annual-cost` assertion. Both commands
MUST pass before the feature is considered complete (Constitution Principles III and V).
