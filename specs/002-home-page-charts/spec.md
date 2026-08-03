# Feature Specification: Home Page Cycle Charts

**Feature Branch**: `002-home-page-charts`

**Created**: 2026-07-29

**Status**: Draft

**Input**: User description: "I want to add some graphs to the home page. Maybe a pie graph of total expenses next period grouped by category (also having a slice for 'leftover' money)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See spending breakdown at a glance (Priority: P1)

As the user, I want to see a pie chart on the home page showing how my pay for the cycle splits across expense categories and leftover money, so I can understand my spending mix visually without reading a list of numbers.

**Why this priority**: This is the entire feature — without the chart rendering correctly for the primary case, there is nothing to ship.

**Independent Test**: With a pay schedule and at least one categorized recurring expense recorded, loading the home page shows a pie chart with one slice per category (sized by that category's total in the cycle) plus one slice for leftover money, and the slice values sum to the cycle's pay amount.

**Acceptance Scenarios**:

1. **Given** a pay schedule and recurring expenses in two categories ("Housing", "Subscriptions") with occurrences in the current cycle, **When** the user loads the home page, **Then** the pie chart shows a slice for "Housing", a slice for "Subscriptions", and a slice for "Leftover", each sized proportionally to its dollar amount.
2. **Given** a recurring expense with no category assigned, **When** the chart is rendered, **Then** its amount is included in an "Uncategorized" slice rather than being dropped.
3. **Given** the cycle has zero recorded expenses, **When** the chart is rendered, **Then** it shows a single "Leftover" slice equal to the full pay amount.

---

### User Story 2 - Chart follows the selected cycle (Priority: P2)

As the user, I want the chart to update to match whichever pay cycle I've selected on the home page, so the visual always matches the numbers already shown there.

**Why this priority**: The home page already lets the user pick a different cycle from a dropdown; the chart must stay consistent with that existing view rather than becoming a second source of truth.

**Independent Test**: Selecting a different cycle from the existing cycle selector re-renders the chart with that cycle's category totals and leftover amount.

**Acceptance Scenarios**:

1. **Given** the home page is showing the current cycle's chart, **When** the user selects a different upcoming cycle from the existing cycle dropdown, **Then** the chart updates to reflect that cycle's category totals and leftover amount.

---

### User Story 3 - No data yet (Priority: P3)

As a first-time user with no pay schedule recorded, I want the home page to not show a broken or empty chart, so the page still makes sense before I've set anything up.

**Why this priority**: Edge-case polish; the page already handles this state today for the existing leftover text, the chart just needs to not break it.

**Independent Test**: Loading the home page with no pay schedule recorded shows the existing "set up your pay schedule" prompt and no chart.

**Acceptance Scenarios**:

1. **Given** no pay schedule has been recorded, **When** the user loads the home page, **Then** no chart is rendered and the existing setup prompt is shown unchanged.

### Edge Cases

- A category's total is $0 for the selected cycle: that category is omitted from the chart entirely (no zero-size slice).
- Every expense falls into a single category: the chart shows exactly two slices (that category and Leftover).
- The pay schedule exists but no expenses are recorded at all: chart shows a single "Leftover" slice for the full pay amount (User Story 1, Scenario 3).
- The selected cycle's expenses exceed its pay amount (negative leftover): no leftover slice is drawn; only category slices are shown, and the overspent amount is called out as text near the chart.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The home page MUST display a pie chart of the selected cycle's spending whenever a pay schedule is recorded.
- **FR-002**: The chart MUST show one slice per expense category with a nonzero total in the selected cycle, sized proportionally to that category's total amount.
- **FR-003**: Expense occurrences with no category assigned MUST be grouped into a single "Uncategorized" slice, consistent with how the existing category breakdown groups them.
- **FR-004**: The chart MUST include one additional slice representing the cycle's leftover amount, sized proportionally alongside the category slices.
- **FR-005**: The chart's category slices and leftover slice MUST use the same underlying totals already computed for the page's existing leftover and category breakdown figures — the chart MUST NOT introduce a separate or inconsistent calculation.
- **FR-006**: The chart MUST reflect whichever cycle is currently selected via the home page's existing cycle selector, defaulting to the current cycle exactly as the rest of the page does today.
- **FR-007**: When no pay schedule is recorded, the home page MUST render without a chart, matching the existing no-schedule state.
- **FR-008**: Hovering or otherwise inspecting a slice MUST reveal that slice's category (or "Leftover") name and dollar amount.
- **FR-009**: When the selected cycle's total expenses exceed its pay amount, the chart MUST omit the leftover slice entirely (rather than drawing a negative or zero-size slice) and the page MUST display the overspent amount as text near the chart.

### Key Entities

- **Cycle Chart Data**: A derived view for a single cycle — one (label, amount) pair per nonzero category plus one (label, amount) pair for leftover — used to render the pie chart. Sourced from the same computed totals as the existing Leftover Result and Category Breakdown for that cycle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can see, in a single glance at the home page, how their pay cycle's money splits between spending categories and leftover, without reading a numeric list.
- **SC-002**: The chart's slice values sum to exactly the cycle's pay amount, with 100% accuracy against the existing leftover and breakdown totals shown on the same page.
- **SC-003**: Switching the selected cycle updates the chart to match the newly selected cycle's data with no stale values shown.
- **SC-004**: The home page renders correctly (with the appropriate prompt, not a broken chart) for a user who has not yet recorded a pay schedule.

## Assumptions

- The chart is added to the existing home page ("/") alongside the current leftover text, not as a replacement for any existing content.
- The chart uses the same currently-selected cycle as the rest of the home page (driven by the existing cycle dropdown), not a separately-controlled date.
- Chart rendering may use a client-side charting approach (e.g., an inline `<svg>` or a small JS charting library); the specific technical approach is left to the planning phase, consistent with this spec being implementation-agnostic.
- No new data entities or persistence are required — the chart is a presentation layer over data the app already computes (Leftover Result, Category Breakdown).
- Category colors are assigned automatically/consistently rather than being user-configurable; a fixed, deterministic color-per-category assignment is sufficient for v1.
