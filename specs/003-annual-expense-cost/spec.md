# Feature Specification: Annual Expense Cost

**Feature Branch**: `003-annual-expense-cost`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Add an \"Annual Cost\" tab/page to the app that lists every recurring expense along with its computed annual cost, plus a grand total. Annual cost is derived from the expense's existing recurrence (day_of_month => amount * 12, day_of_week => amount * 52, biweekly => amount * 26) — no new user input needed, this is a pure display/derived-calculation feature reusing the existing RecurringExpense data. Should follow the same nav-tab pattern as the existing Leftover/Pay Schedule/Expenses tabs, and probably group by category similar to the expenses list, sorted by annual cost descending, with a grand total at the bottom."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View annual cost per expense (Priority: P1)

As the user, I want to open a dedicated page that shows what each of my recurring
expenses costs me over a full year, so I can understand the real yearly weight of a
bill instead of just its per-occurrence amount.

**Why this priority**: This is the core value of the feature — without it there is
nothing to show. Every other capability in this feature builds on this list existing.

**Independent Test**: Can be fully tested by adding a few recurring expenses with
different recurrence types (day-of-month, day-of-week, biweekly), opening the new tab,
and confirming each expense shows a name and an annual cost consistent with its amount
and recurrence.

**Acceptance Scenarios**:

1. **Given** a monthly (day-of-month) expense of $50, **When** the user opens the
   Annual Cost tab, **Then** that expense shows an annual cost of $600 (50 × 12).
2. **Given** a weekly (day-of-week) expense of $20, **When** the user opens the Annual
   Cost tab, **Then** that expense shows an annual cost of $1,040 (20 × 52).
3. **Given** a biweekly expense of $75, **When** the user opens the Annual Cost tab,
   **Then** that expense shows an annual cost of $1,950 (75 × 26).

---

### User Story 2 - See total annual recurring spend (Priority: P2)

As the user, I want to see a single grand total across all recurring expenses, so I can
know at a glance the total yearly cost of everything I've committed to.

**Why this priority**: The per-expense list alone is useful, but the single number
summarizing overall yearly commitment is the headline answer most users are looking
for when they open this page.

**Independent Test**: Can be fully tested by adding several expenses and confirming the
displayed grand total equals the sum of every individual expense's annual cost.

**Acceptance Scenarios**:

1. **Given** three recurring expenses with annual costs of $600, $1,040, and $1,950,
   **When** the user opens the Annual Cost tab, **Then** the page displays a grand
   total of $3,590.
2. **Given** no recurring expenses exist, **When** the user opens the Annual Cost tab,
   **Then** the page shows an empty state and a grand total of $0.

---

### User Story 3 - Compare costs by category, largest first (Priority: P3)

As the user, I want expenses grouped by category and sorted so the biggest annual costs
stand out, so I can quickly spot which categories or individual bills dominate my yearly
spending.

**Why this priority**: Grouping and ranking add analytical value on top of the raw list,
but the feature is already useful without them — this is a refinement, not the MVP.

**Independent Test**: Can be fully tested by adding expenses across multiple categories
with varying amounts and confirming expenses are grouped under their category and
ordered from highest to lowest annual cost within each group.

**Acceptance Scenarios**:

1. **Given** expenses in "Housing" and "Subscriptions" categories, **When** the user
   opens the Annual Cost tab, **Then** expenses are displayed grouped under their
   respective category headings.
2. **Given** a category containing expenses with annual costs of $200, $1,200, and
   $600, **When** the user opens the Annual Cost tab, **Then** that category's
   expenses are listed in the order $1,200, $600, $200.
3. **Given** an expense with no category assigned, **When** the user opens the Annual
   Cost tab, **Then** that expense appears under an "Uncategorized" grouping, matching
   the existing Expenses tab's convention.

### Edge Cases

- What happens when there are no recurring expenses at all? The page MUST show an
  empty-state message (consistent with the existing Expenses tab) rather than an empty
  or broken table, and a grand total of $0.
- What happens when two expenses in the same category have the identical annual cost?
  Order between them MUST be stable and deterministic (e.g., secondary sort by name) so
  the page doesn't reorder on every load.
- What happens when an expense's amount, category, or recurrence is edited on the
  existing Expenses tab? The Annual Cost tab MUST reflect the current stored data on
  next page load — it does not cache or duplicate expense data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a new page reachable from the main navigation,
  labeled "Annual Cost," alongside the existing Leftover, Pay Schedule, and Expenses
  tabs.
- **FR-002**: System MUST compute each recurring expense's annual cost from its stored
  amount and recurrence type: day-of-month recurrence = amount × 12; day-of-week
  recurrence = amount × 52; biweekly recurrence = amount × 26.
- **FR-003**: System MUST display, for every recurring expense, its name and its
  computed annual cost.
- **FR-004**: System MUST group displayed expenses by category, using "Uncategorized"
  for any expense without an assigned category, consistent with the existing Expenses
  tab's grouping convention.
- **FR-005**: Within each category group, System MUST sort expenses by annual cost in
  descending order, breaking ties by expense name for a stable, deterministic order.
- **FR-006**: System MUST display a subtotal of annual cost for each category group.
- **FR-007**: System MUST display a grand total of annual cost summed across all
  recurring expenses.
- **FR-008**: When no recurring expenses exist, System MUST display an empty-state
  message instead of an empty list, and a grand total of $0.
- **FR-009**: System MUST always compute annual cost from current, live expense data at
  request time — it MUST NOT store or cache a separately-maintained annual-cost value.
- **FR-010**: This page is read-only; it MUST NOT provide expense creation, editing, or
  deletion controls (those remain on the existing Expenses tab).

### Key Entities

- No new persisted entity is introduced. This feature adds a derived **Annual Cost**
  value (annual cost = per-occurrence amount × the fixed yearly-occurrence count implied
  by the existing RecurringExpense's recurrence type), computed at request time from the
  existing RecurringExpense records, plus a page-level grand total and per-category
  subtotals derived the same way.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can see the annual cost of every recurring expense they've entered
  within a single page view, with no additional navigation or calculation required.
- **SC-002**: The displayed grand total always equals the exact sum of every individual
  displayed annual cost, with no rounding discrepancy.
- **SC-003**: A user can identify their single largest annual recurring cost within 5
  seconds of opening the page, without needing to manually compare numbers, due to
  descending sort order.
- **SC-004**: Editing an expense's amount, category, or recurrence on the existing
  Expenses tab is reflected on the Annual Cost tab the next time it is opened, with no
  manual refresh step or stale data.

## Assumptions

- Annual cost is a nominal, fixed-multiplier projection (×12 for day-of-month, ×52 for
  day-of-week, ×26 for biweekly) rather than an actual count of calendar occurrences; it
  does not adjust for leap years, day-of-month clamping in short months, or the exact
  number of Fridays (etc.) in a given real year. This matches the multipliers specified
  by the user and keeps the calculation simple and predictable.
- No new user input, form, or data entity is required — this feature only adds a
  read-only view and a computed value derived from existing RecurringExpense records.
- Category grouping and the "Uncategorized" fallback reuse the same convention already
  established on the existing Expenses tab.
- Money continues to be handled as integer cents internally and formatted as dollars for
  display, consistent with the rest of the application.
