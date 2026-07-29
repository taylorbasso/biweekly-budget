# Feature Specification: Pay Cycle Leftover

**Feature Branch**: `001-pay-cycle-leftover`

**Created**: 2026-07-28

**Status**: Draft

**Input**: User description: "Compute how much free/discretionary money the user has left to spend in the current biweekly pay cycle. Given the user's paycheck (date + amount) and a list of expenses/budget categories each with a due date and amount, find all expenses due between the current pay date (inclusive) and the day before the next pay date (inclusive), subtract their total from the paycheck amount, and report the leftover amount."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Check leftover spending money (Priority: P1)

As the user, I want to ask how much money I have left to spend before my next paycheck, so I can make near-term spending decisions without doing the date math myself.

**Why this priority**: This is the entire value proposition of the tool. Without it, nothing else matters.

**Independent Test**: With a pay schedule and at least one recurring expense recorded, requesting the leftover amount for today's date returns a dollar figure and the cycle's date range.

**Acceptance Scenarios**:

1. **Given** a pay schedule anchored on Jul 31 with amount $X and no expenses due between Jul 31 and Aug 13, **When** the user requests the leftover for Aug 1, **Then** the system reports $X as leftover and states the cycle range as Jul 31–Aug 13.
2. **Given** the same pay schedule and a recurring expense due on the 1st of every month for $Y, **When** the user requests the leftover for a cycle that includes the 1st, **Then** the system reports $X − $Y as leftover.
3. **Given** a recurring expense due on the exact date of the *next* pay date, **When** the user requests leftover for the current cycle, **Then** that expense is excluded from the current cycle's total (it belongs to the next cycle).

---

### User Story 2 - Record pay schedule (Priority: P2)

As the user, I want to record my paycheck anchor date and amount, so leftover calculations can project every past and future pay date from it.

**Why this priority**: Required before any leftover calculation can run, but only needs to be entered once.

**Independent Test**: Recording a pay schedule and then immediately requesting a leftover calculation succeeds using that schedule.

**Acceptance Scenarios**:

1. **Given** no pay schedule exists, **When** the user records an anchor pay date and a pay amount, **Then** subsequent leftover requests project cycles every 14 days from that anchor, both forward and backward in time.
2. **Given** a pay schedule already exists, **When** the user updates the anchor date or amount, **Then** subsequent leftover requests use the updated schedule.

---

### User Story 3 - Record and manage recurring expenses (Priority: P3)

As the user, I want to add, view, edit, and remove recurring expenses — either tied to a day of the month (e.g., rent on the 1st) or a day of the week (e.g., an investment transfer every Friday) — so my leftover calculation reflects my actual bills and recurring transfers.

**Why this priority**: Leftover is only useful once real expenses are factored in, but the schedule (US2) and the calculation shape (US1) can be built and tested first with a small hand full of test expenses.

**Independent Test**: Adding a recurring expense and then requesting a leftover calculation for a cycle containing an occurrence of that expense reflects it in the total.

**Acceptance Scenarios**:

1. **Given** a recurring expense is added with a day-of-month rule, **When** a leftover request covers a cycle containing that day, **Then** the expense amount is subtracted exactly once.
2. **Given** a recurring expense is added with a day-of-week rule (e.g., every Friday), **When** a leftover request covers a 14-day cycle, **Then** both occurrences of that weekday within the cycle are subtracted.
3. **Given** an existing recurring expense, **When** the user removes it, **Then** it no longer affects any subsequent leftover calculation.

---

### User Story 4 - Category spending breakdown (Priority: P2)

As the user, I want each expense tagged with a category (e.g., "Housing", "Subscriptions", "Investments") and a breakdown of how much I'm spending per category in the current pay cycle, so I can see where my money goes, not just the bottom-line leftover.

**Why this priority**: High value alongside the core leftover figure — same underlying data, but this is a secondary view rather than the primary question the tool answers, so it follows US1.

**Independent Test**: With categorized recurring expenses recorded, requesting a category breakdown for the current cycle returns a per-category subtotal that sums to the same total used in the leftover calculation.

**Acceptance Scenarios**:

1. **Given** recurring expenses tagged with categories, **When** the user requests a category breakdown for the current cycle, **Then** the system reports, for each category with at least one occurrence due in that cycle, the total amount due in that category.
2. **Given** a category breakdown request, **When** the per-category totals are summed, **Then** the sum equals the total expenses figure used in that cycle's leftover calculation.
3. **Given** a recurring expense with no category assigned, **When** a breakdown is requested, **Then** it is grouped under a single catch-all "Uncategorized" category rather than causing an error.

---

### Edge Cases

- A day-of-month expense's day does not exist in a given month (e.g., due on the 31st in a 30-day month, or the 29th/30th/31st in February): treated as due on the last day of that month instead.
- The requested reference date falls before the pay schedule's anchor date: the system still projects a valid historical cycle by extrapolating backward in fixed 14-day increments.
- An expense occurrence falls exactly on the next pay date: it belongs to the *next* cycle, not the current one (cycle end is the day before the next pay date).
- A zero or negative pay amount or expense amount is entered: rejected as invalid input.
- Two recurring expenses share the same name or due day: both are tracked and counted independently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to record a pay schedule consisting of one anchor pay date and a fixed pay amount.
- **FR-002**: The system MUST use the pay schedule to project pay dates every 14 days, indefinitely, both forward and backward from the anchor date.
- **FR-003**: Users MUST be able to update the pay schedule's anchor date or amount.
- **FR-004**: Users MUST be able to record a recurring expense with a name, a dollar amount, a recurrence rule that is either a day-of-month (1st–31st) or a day-of-week (Sunday–Saturday), and an optional category label.
- **FR-005**: Users MUST be able to view, edit, and remove previously recorded recurring expenses, including changing their category.
- **FR-006**: When a day-of-month recurrence's day does not exist in a given month, the system MUST treat that expense as due on the last day of that month instead.
- **FR-007**: Users MUST be able to request the leftover amount for the cycle containing any given reference date, defaulting to today's date when none is given.
- **FR-008**: The system MUST determine the requested cycle's start as the most recent projected pay date on or before the reference date, and the cycle's end as the day immediately before the next projected pay date.
- **FR-009**: The system MUST identify every occurrence of every recurring expense whose due date falls within the cycle's date range, inclusive of both the start and end dates.
- **FR-010**: The system MUST sum the amounts of all expense occurrences identified in FR-009 and subtract that sum from the cycle's pay amount to produce the leftover amount.
- **FR-011**: The system MUST report the leftover amount together with the cycle's start date, end date, and next pay date.
- **FR-012**: The system MUST reject a pay amount or expense amount that is zero or negative as invalid input.
- **FR-013**: The system MUST NOT assign a single expense occurrence to more than one cycle.
- **FR-014**: Users MUST be able to request a category breakdown for the cycle containing a given reference date, defaulting to today's date when none is given.
- **FR-015**: The system MUST group the expense occurrences identified for a cycle (per FR-009) by category and report the total amount due per category.
- **FR-016**: Expense occurrences with no category assigned MUST be grouped under a single "Uncategorized" category in the breakdown rather than being omitted or causing an error.

### Key Entities

- **Pay Schedule**: The single source used to project pay dates. Holds an anchor date and a fixed amount; pay dates recur every 14 days from the anchor, extending forward and backward indefinitely.
- **Recurring Expense**: A named, recurring bill or transfer. Holds a dollar amount, a recurrence rule — either a day-of-month or a day-of-week — and an optional category label, used to generate concrete due-date occurrences within any cycle.
- **Cycle**: A computed date range (start date, end date, next pay date) derived from the Pay Schedule for a given reference date.
- **Leftover Result**: The output of a leftover request — the cycle's date range, the pay amount, the matched expense occurrences and their total, and the resulting leftover amount.
- **Category Breakdown**: The output of a breakdown request for a cycle — a set of (category, total amount) pairs covering every expense occurrence due in that cycle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with a pay schedule and recurring expenses already recorded can obtain the leftover amount for the current cycle, including the cycle's date range, from a single request.
- **SC-002**: Every expense occurrence due within a cycle is counted exactly once, verified with 100% accuracy across boundary cases (occurrence on the cycle's start date, on its end date, and on the next pay date).
- **SC-003**: A user can determine how much they have left to spend and until what date without performing any date arithmetic themselves.
- **SC-004**: Pay dates and expense occurrences project correctly at least 2 years forward and backward from the anchor date without any manual re-entry of individual pay dates.
- **SC-005**: A user can see, per category, how much of the current cycle's expenses falls into each category, and those totals sum to the cycle's total expense figure with 100% accuracy.

## Assumptions

- The pay amount is constant across all projected pay dates for this feature; per-paycheck amount overrides (e.g., irregular bonus checks) are out of scope.
- Only a single pay schedule (one income source) is supported; multiple simultaneous income streams are out of scope.
- A single implicit currency is used; multi-currency support is out of scope.
- Payment status (paid vs. unpaid) is not tracked — every expense occurrence due within the cycle window counts toward the leftover calculation regardless of whether the user has actually paid it yet.
- "Due date" means the date the expense is expected to leave the user's account, not a purchase or authorization date.
- Category breakdown reporting covers pay-cycle windows only; calendar-month breakdowns are out of scope for this feature.
- A category is a simple free-text label on a recurring expense; a separate managed list of allowed categories is out of scope.
