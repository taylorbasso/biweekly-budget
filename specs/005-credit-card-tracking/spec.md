# Feature Specification: Credit Cards Tracking

**Feature Branch**: `005-credit-card-tracking`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Add a \"Credit Cards\" tab/page for tracking credit card and loan balances. For each entry (credit card or loan) the user can record: name, amount owed (balance), minimum payment, actual/planned payment, and payoff time (estimated time to pay off the balance given the payment amount). The page lists all entries in a table and shows a \"Totals\" row summing the applicable numeric columns (balance, minimum payment, actual payment). Payoff time is a computed/derived value based on balance, payment amount, and interest rate (need an interest rate field per entry to compute amortization/payoff time correctly) — not a simple total since it doesn't sum across rows. Users should be able to add, edit, and delete entries. Feature should be usable for both credit cards and loans, but the tab/page is named \"Credit Cards\"."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View all balances at a glance (Priority: P1)

A user opens the new "Credit Cards" tab and sees a table listing every credit card and loan they've entered, with columns for balance owed, minimum payment, actual (planned) payment, and estimated payoff time. A "Totals" row at the bottom sums the balance, minimum payment, and actual payment columns across all entries.

**Why this priority**: This is the core value of the feature — a single place to see total debt and payment obligations. Without this view, nothing else in the feature matters.

**Independent Test**: Can be fully tested by seeding a few credit card/loan entries directly in the database and loading the page, then confirming the table renders each entry's fields correctly and the Totals row shows the correct sums.

**Acceptance Scenarios**:

1. **Given** three entries exist with balances of $1,000, $2,500, and $500, **When** the user opens the Credit Cards page, **Then** the table shows all three rows and a Totals row with balance = $4,000.
2. **Given** no entries exist yet, **When** the user opens the Credit Cards page, **Then** the page shows an empty state (no rows, no Totals row, or a Totals row showing zero) and a clear way to add a new entry.
3. **Given** entries with different minimum and actual payments, **When** the user views the Totals row, **Then** minimum payment and actual payment are each summed independently (not combined).

---

### User Story 2 - Add and edit entries (Priority: P1)

A user adds a new credit card or loan by entering its name, balance, interest rate, minimum payment, and actual/planned payment. They can later edit any of these fields as balances and rates change.

**Why this priority**: The table is only useful if the user can populate and maintain it themselves; this is required for the feature to be usable at all, tied for top priority with the view.

**Independent Test**: Can be fully tested by using the add form to create an entry, confirming it appears in the table, then editing one of its fields and confirming the change is reflected.

**Acceptance Scenarios**:

1. **Given** the user is on the Credit Cards page, **When** they submit the add-entry form with a name, balance, interest rate, minimum payment, and actual payment, **Then** a new row appears in the table with those values.
2. **Given** an existing entry, **When** the user edits its balance and actual payment and saves, **Then** the table reflects the updated values and the payoff time recalculates accordingly.
3. **Given** the add or edit form is submitted with a negative balance, negative payment, or non-numeric input, **Then** the system rejects the submission with a clear validation message and no entry is created or changed.

---

### User Story 3 - Delete an entry (Priority: P2)

A user removes a credit card or loan that has been paid off or was entered by mistake.

**Why this priority**: Necessary for long-term upkeep of the list, but the feature is still useful without it for initial adoption (a user can simply zero out a paid-off balance in the short term).

**Independent Test**: Can be fully tested by deleting an existing entry and confirming it no longer appears in the table and is excluded from the Totals row.

**Acceptance Scenarios**:

1. **Given** an existing entry, **When** the user deletes it, **Then** it no longer appears in the table and the Totals row updates to exclude it.
2. **Given** the user attempts to delete an entry, **When** they have not confirmed the deletion, **Then** the entry is not removed (accidental deletion is prevented by a confirmation step).

---

### User Story 4 - See estimated payoff time (Priority: P2)

A user wants to know, given an entry's current balance, interest rate, and actual (or minimum, if no actual payment is set) payment, roughly how long it will take to pay off that balance.

**Why this priority**: This is valuable context for decision-making (e.g., "should I pay more than the minimum?") but the tracker is still useful as a balance/payment ledger without it, so it can follow the core CRUD functionality.

**Independent Test**: Can be fully tested by creating an entry with a known balance, interest rate, and payment, and confirming the displayed payoff time matches a hand-calculated amortization result for that input.

**Acceptance Scenarios**:

1. **Given** an entry with a balance, a positive interest rate, and a payment greater than the monthly interest charge, **When** the table renders, **Then** the payoff time column shows an estimated number of months (or years/months) to reach a zero balance.
2. **Given** an entry whose payment is less than or equal to the monthly interest accrued on its balance, **When** the table renders, **Then** the payoff time column shows a clear indicator that the balance will never be paid off at that payment level (rather than a misleading or nonsensical number).
3. **Given** an entry with a zero balance, **When** the table renders, **Then** the payoff time column shows that the entry is already paid off (e.g., "Paid off" / 0 months), not an error or a blank cell.
4. **Given** an entry with an interest rate of 0%, **When** the table renders, **Then** the payoff time is the balance divided by the payment, rounded up to the nearest whole period.

---

### Edge Cases

- What happens when an entry has a balance greater than zero but no payment amount is set (both minimum and actual are $0)? The payoff time should indicate the debt will never be paid off, consistent with the "payment doesn't cover interest" case.
- What happens when only a minimum payment is set and no actual payment is provided? The payoff time calculation uses the actual payment when present, falling back to the minimum payment otherwise.
- How does the system handle an interest rate entered as a whole number vs. a decimal (e.g., "18" vs "0.18")? The UI must make the expected unit (annual percentage, e.g., "18" means 18% APR) unambiguous via a label.
- What happens to the Totals row when there are zero entries? It is either omitted or shown with all-zero totals rather than erroring.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a "Credit Cards" page, reachable from the app's main navigation, listing every stored credit card/loan entry in a table.
- **FR-002**: Each entry MUST record: a name/label, current balance owed, annual interest rate, minimum payment amount, actual (planned) payment amount, and an optional credit limit.
- **FR-003**: The table MUST display, per entry, at minimum: name, balance, minimum payment, actual payment, estimated payoff time, credit limit, and usage percentage (balance ÷ credit limit).
- **FR-004**: The table MUST include a "Totals" row summing the balance, minimum payment, actual payment, and credit limit columns across all entries, plus an aggregate usage percentage (total balance ÷ total credit limit). The payoff time column MUST NOT be summed in the Totals row (it is not a meaningful aggregate).
- **FR-014**: When an entry's credit limit is unset (zero), its usage percentage MUST display as not-applicable rather than 0% or an error; an unset limit MUST be excluded from the Totals row's aggregate usage percentage denominator only insofar as it contributes 0 to the credit-limit sum (i.e. aggregate usage is always total balance ÷ total credit limit, computed once, not an average of per-row percentages).
- **FR-005**: Users MUST be able to add a new entry via a form capturing all fields in FR-002.
- **FR-006**: Users MUST be able to edit any field of an existing entry.
- **FR-007**: Users MUST be able to delete an existing entry, with a confirmation step to prevent accidental deletion.
- **FR-008**: System MUST reject negative values for balance, interest rate, minimum payment, and actual payment, and MUST reject non-numeric input for these fields, surfacing a clear validation error without saving.
- **FR-009**: System MUST compute an estimated payoff time for each entry from its balance, annual interest rate, and payment amount (actual payment if set and greater than zero, otherwise minimum payment), using standard amortization: monthly interest accrues on the remaining balance, and the payment reduces principal after interest.
- **FR-010**: System MUST express payoff time in a human-readable duration (e.g., months, or years and months for long durations).
- **FR-011**: System MUST distinguish, in the payoff time display, between "will pay off in N months," "already paid off" (zero balance), and "will never pay off at this payment level" (payment does not exceed accruing interest).
- **FR-012**: This feature stores and displays credit card/loan data independently of the existing pay-cycle leftover and category-breakdown calculations; entries here are not automatically counted as recurring expenses in the leftover calculation.
- **FR-013**: Money fields (balance, minimum payment, actual payment, credit limit) MUST be stored and computed internally as integer cents, consistent with the rest of the application.

### Key Entities

- **CreditAccount**: Represents a single credit card or loan being tracked. Attributes: name/label, current balance (integer cents), annual interest rate (percentage), minimum payment (integer cents), actual/planned payment (integer cents), credit limit (integer cents, optional — 0 means "not tracked"). Payoff time and usage percentage are computed values, not stored. Independent of PaySchedule, RecurringExpense, and any other existing entity — no relationship to pay cycles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can view total debt balance and total monthly payment obligations across all tracked cards/loans in a single glance, without doing any manual addition.
- **SC-002**: A user can add a new credit card or loan entry and see it reflected in the table and Totals row in under 30 seconds.
- **SC-003**: A user can edit an existing entry's balance or payment and see the updated payoff time estimate immediately after saving, with no separate recalculation step.
- **SC-004**: Payoff time estimates match a manually-computed amortization schedule for the same balance, rate, and payment within rounding tolerance (±1 period).
- **SC-005**: Attempting to save invalid data (negative numbers, non-numeric text) never corrupts existing entries or produces an incorrect Totals row.

## Assumptions

- The page tracks credit cards and loans as a standalone ledger; it does not integrate with the existing pay-cycle leftover calculation or recurring-expense scheduling in this iteration. A future feature could add that linkage if a concrete need arises (per the project's simplicity-first principle).
- Interest rate is entered and stored as an annual percentage rate (APR) and converted to a monthly rate (APR ÷ 12) for amortization purposes, matching common consumer credit card/loan conventions.
- "Actual payment" represents the amount the user actually plans to pay each period (which may equal, exceed, or — though not recommended — fall short of the minimum payment); it is the value used for payoff-time estimation when present and nonzero.
- There is exactly one payment per month assumed for amortization purposes (this app's biweekly pay-cycle cadence does not need to align with the credit account's payment cadence).
- No support for one-time/lump-sum payment tracking or payment history in this iteration — only the current balance and payment amounts are tracked, not a ledger of past payments.
- Single user, local-only storage, consistent with the rest of the application (no multi-user or sharing concerns).
