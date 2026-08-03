# Data Model: Home Page Cycle Charts

No new persisted entities and no changes to existing tables (`PaySchedule`,
`RecurringExpense` — see `specs/001-pay-cycle-leftover/data-model.md`). This feature adds
one computed (not persisted) concept, produced on demand from the existing
`LeftoverResult` and `CategoryBreakdown` for a cycle.

## Computed (not persisted) concepts

### ChartSlice

One wedge of the pie chart (category or Leftover).

| Field | Type | Description |
|---|---|---|
| label | text | Category name, `"Uncategorized"`, or `"Leftover"` |
| amount | integer (cents) | The slice's dollar amount — a category total from `CategoryBreakdown.totals`, or the cycle's `leftover_amount` |
| percent | float | Share of the chart's total (0–100); see Research Decision 5 for the denominator rule |
| color | text | CSS color string, deterministically assigned (Research Decision 3) |
| path_d | text | SVG `<path>` `d` attribute drawing this slice's arc, or `None` when this is the sole remaining slice (see `is_full_circle`) |
| is_full_circle | bool | `True` when this slice is the only nonzero slice in the chart, in which case it MUST be rendered as a full `<circle>` rather than via `path_d` (Research Decision 4) |

### CycleChart

The full chart for one cycle — the output `charts.py` hands to the template.

| Field | Type | Description |
|---|---|---|
| slices | list[ChartSlice] | Nonzero slices only, category slices sorted by name then the Leftover slice last (when present) |
| overspent | bool | `True` when `total_expenses > pay_amount` for the cycle (FR-009) |
| overspent_amount | integer (cents) | `total_expenses - pay_amount` when `overspent` is `True`, else `0` |

## Derivation

```
CategoryBreakdown.totals + LeftoverResult.leftover_amount + LeftoverResult.pay_amount
        │
        ▼  charts.build_chart(...)
CycleChart (slices, overspent, overspent_amount)
```

Rules (see `research.md` for rationale):

1. Drop any category total that is exactly `0`.
2. If `leftover_amount > 0`, include a Leftover slice for that amount; if
   `leftover_amount <= 0`, omit the Leftover slice.
3. If `leftover_amount < 0` (i.e. `total_expenses > pay_amount`), set `overspent = True`
   and `overspent_amount = total_expenses - pay_amount`.
4. Percentage denominator: `pay_amount` when not overspent, `total_expenses` when
   overspent.
5. If zero slices remain (impossible in practice, since `pay_amount > 0` is enforced at
   input time per FR-012 of feature 001 — a `pay_amount > 0` cycle with `total_expenses
   == pay_amount` still has `leftover_amount == 0`, dropped, but any nonzero category
   total or a positive leftover keeps at least one slice), `charts.build_chart` returns
   an empty `slices` list and the template renders no chart (defensive only — not a
   reachable spec scenario given FR-012).
6. If exactly one slice remains, mark it `is_full_circle = True` and leave `path_d` as
   `None`.

## Invariants

- `sum(slice.amount for slice in slices where label != "Leftover") == CategoryBreakdown`'s
  nonzero total, i.e. `total_expenses` (minus any exactly-zero categories, which
  contribute 0 anyway).
- `sum(slice.percent for slice in slices)` is `100.0` (within floating-point rounding)
  whenever `slices` is nonempty.
- Slice order is deterministic for a given cycle's data (sorted by label, Leftover
  last) — required so the chart's color assignment (Research Decision 3) and any
  accompanying legend stay stable across repeated renders of the same cycle.
