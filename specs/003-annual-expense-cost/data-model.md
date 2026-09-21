# Data Model: Annual Expense Cost

No new persisted entities and no changes to existing tables (`PaySchedule`,
`RecurringExpense` — see `specs/001-pay-cycle-leftover/data-model.md`). This feature adds
computed (not persisted) concepts, produced on demand from the existing
`RecurringExpense` records.

## Computed (not persisted) concepts

### Annualization multiplier

A fixed mapping from `RecurringExpense.recurrence_type` to a nominal yearly occurrence
count, used to derive annual cost (Research Decision 1):

| recurrence_type | multiplier |
|---|---|
| `day_of_month` | 12 |
| `day_of_week` | 52 |
| `biweekly` | 26 |

### AnnualCostItem

One recurring expense's row on the Annual Cost page.

| Field | Type | Description |
|---|---|---|
| expense_id | int \| None | The source `RecurringExpense.id` |
| name | text | The expense's name |
| annual_cost | integer (cents) | `expense.amount * multiplier[expense.recurrence_type]` |

### CategoryAnnualCost

One category grouping on the Annual Cost page.

| Field | Type | Description |
|---|---|---|
| category | text | Category name, or `"Uncategorized"` (`UNCATEGORIZED`) when the expense has none |
| items | list[AnnualCostItem] | This category's expenses, sorted by `annual_cost` descending, ties broken by `name` ascending (FR-005) |
| subtotal | integer (cents) | Sum of `annual_cost` across `items` (FR-006) |

### AnnualCostBreakdown

The full page's data — what `calculations.py` hands to the route/template.

| Field | Type | Description |
|---|---|---|
| categories | list[CategoryAnnualCost] | Ordered alphabetically by `category` (Research Decision 3), matching the existing Expenses tab's convention |
| grand_total | integer (cents) | Sum of every `CategoryAnnualCost.subtotal` (FR-007), equivalently the sum of every expense's `annual_cost` |

## Derivation

```
list[RecurringExpense]
        │
        ▼  calculations.compute_annual_cost_breakdown(...)
AnnualCostBreakdown (categories -> CategoryAnnualCost -> AnnualCostItem, grand_total)
```

Rules (see `research.md` for rationale):

1. For each expense, compute `annual_cost = expense.amount * multiplier[expense.recurrence_type]`.
2. Group expenses by `expense.category or UNCATEGORIZED`.
3. Within each category group, sort items by `annual_cost` descending, then `name`
   ascending (stable tie-break, spec Edge Case).
4. Order category groups alphabetically by category name.
5. Compute each category's `subtotal` as the sum of its items' `annual_cost`.
6. Compute `grand_total` as the sum of all category subtotals.
7. When there are no `RecurringExpense` records at all, `categories` is an empty list and
   `grand_total` is `0` (FR-008).

## Invariants

- `grand_total == sum(item.annual_cost for category in categories for item in category.items)`
  exactly, with no rounding — all values are integer cents (FR-002, SC-002).
- `category.subtotal == sum(item.annual_cost for item in category.items)` exactly, for
  every category.
- Every `RecurringExpense` returned by `db.list_expenses` appears in exactly one
  `AnnualCostItem` — this is a pure grouping/derivation over existing data, so no expense
  is dropped or duplicated.
- Computation reads current expense data at request time; no annual-cost value is stored
  or cached (FR-009).
