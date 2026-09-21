# Research: Annual Expense Cost

No `NEEDS CLARIFICATION` markers remain in Technical Context. This document records the
design decisions made while filling it in.

## Decision 1: Annualization multiplier mapping

**Decision**: A fixed lookup from `RecurringExpense.recurrence_type` to a nominal yearly
occurrence count: `day_of_month → 12`, `day_of_week → 52`, `biweekly → 26`. Annual cost
for an expense is `expense.amount * multiplier[expense.recurrence_type]`.

**Rationale**: Directly specified by the feature request and confirmed in the spec's
Assumptions — a simple, predictable nominal projection rather than an actual count of
occurrences in a specific calendar year (which would vary by leap year, which weekday
falls how many times in a given year, etc.). `RECURRENCE_TYPES` in `models.py` already
enumerates exactly these three values, so the mapping is exhaustive and can be checked by
mypy (no fallback/default branch needed).

**Alternatives considered**:
- *Actual occurrence count for a specific calendar year* (e.g., count real Fridays in
  2026, account for day-of-month clamping in short months): rejected — the spec
  explicitly calls for the fixed multipliers, and a year-dependent number would make the
  page's numbers shift depending on which year is "current," which is more confusing than
  useful for a "what does this cost me per year" question.

## Decision 2: Where the calculation lives

**Decision**: Add the multiplier table and a new computation function to the existing
`src/budget/calculations.py`, alongside `compute_breakdown`, rather than creating a new
module.

**Rationale**: Constitution Principle II requires business logic to live in a
Flask-independent module; `calculations.py` is already that module's home for computed,
non-persisted views over `RecurringExpense` data (`CategoryBreakdown` is the closest
existing precedent — same input type, same category-grouping shape). Annual cost is a
small sibling computation, not a new concern that justifies its own module (Principle I —
YAGNI).

**Alternatives considered**:
- *New `annual_cost.py` module*: rejected as unnecessary fragmentation for one function
  and one dataclass family that share `UNCATEGORIZED` and the same category-grouping
  shape already established in `calculations.py`.

## Decision 3: Grouping and ordering rules

**Decision**: Reuse the existing category convention — `expense.category or
UNCATEGORIZED` — for grouping. Categories are ordered alphabetically (matching
`routes._group_by_category`'s existing convention for the Expenses tab, so
"Uncategorized" sorts wherever it falls alphabetically rather than always first or last).
Within a category, expenses are sorted by annual cost descending, tie-broken by name
ascending for a deterministic, stable order (spec Edge Case: identical annual costs must
not reorder between loads).

**Rationale**: Directly required by FR-004/FR-005. Matching the existing Expenses tab's
category-ordering convention keeps the two "grouped by category" pages consistent for the
user, rather than introducing a second, different grouping rule.

**Alternatives considered**:
- *Order categories by their subtotal (largest first)*: considered, since it would
  reinforce the "biggest costs first" theme from FR-005. Rejected to keep category order
  consistent and predictable across the Expenses tab and this new tab — only the
  within-category order needs to foreground the largest costs (FR-005 only specifies
  ordering *within* a category).

## Decision 4: Route and navigation

**Decision**: One new read-only route, `GET /annual-cost`, added to `routes.py`, backed
by a new `annual_cost.html` template, with a new "Annual Cost" link added to the nav bar
in `layout.html` (after "Expenses"). No new POST endpoints, no new form.

**Rationale**: Matches FR-001 and FR-010 directly, and mirrors the existing pattern for
each of the three current tabs (one `GET` route per nav item, thin route body, dedicated
template).

**Alternatives considered**:
- *Add annual cost as a section on the existing Expenses page instead of a new tab*:
  rejected — the feature description and spec explicitly ask for a separate tab, and the
  Expenses page is about managing (create/edit/delete) expenses, while this page is a
  read-only analytical view; conflating the two would blur that page's purpose.
