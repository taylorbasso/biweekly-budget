# Feature Specification: Savings Runway

**Feature Branch**: `004-savings-runway`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Add a \"Runway\" tab that shows how long money in savings/401k/other accounts would cover only essential recurring expenses if income stopped. Each recurring expense gets a persisted 'essential' checkbox (a new DB column, toggled directly on this tab). The user can add as many named accounts as they want (cash, savings, personal investment, 401k, whatever), each persisted with a balance and its own optional penalty/tax percentage (default 0%) applied only to that account's balance — since some accounts (401k) have early-withdrawal penalties/taxes and others (cash, savings) don't. Monthly essential burn rate is derived by converting each essential expense's recurrence to a monthly-equivalent amount, reusing the existing annual-cost calculation (annual cost / 12) rather than a new conversion. Runway in months = total spendable across all accounts (after each account's own haircut) divided by monthly essential burn, shown like '3.53 months'. Needs to handle zero essential expenses (divide-by-zero) and zero accounts gracefully. Business logic belongs in a plain Python module, not routes or templates, per the project's library-oriented design rule."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mark expenses as essential (Priority: P1)

As the user, I want to mark which of my recurring expenses are essential (rent,
insurance, minimum debt payments) versus discretionary (subscriptions, dining out), so
the app knows which bills I'd still have to pay if my income stopped.

**Why this priority**: Without a way to distinguish essential from discretionary
expenses, there is no meaningful "bare minimum" burn rate to compute a runway against.
This is the foundation every other capability in this feature depends on.

**Independent Test**: Can be fully tested by editing a few expenses, ticking
"Essential" in the expense form and saving, then confirming those expenses show an
"Essential" tag on the Expenses list and count toward the Runway tab's burn rate.

**Acceptance Scenarios**:

1. **Given** a recurring expense that is not marked essential, **When** the user ticks
   "Essential" in its add/edit expense form and saves, **Then** the expense is marked
   essential and included in the essential burn-rate calculation.
2. **Given** an expense marked essential, **When** the user unticks "Essential" in its
   edit form and saves, **Then** it is excluded from the essential burn-rate calculation.
3. **Given** an expense was marked essential in a previous visit, **When** the user
   reopens the Runway tab (or any other tab that lists expenses), **Then** its essential
   status is still reflected as previously set.

---

### User Story 2 - Enter account balances and see runway in months (Priority: P1)

As the user, I want to add one or more named accounts (e.g. "Cash", "Savings", "401k")
with their current balances, and see how many months my essential expenses would be
covered by that total money, so I can answer "if I lost my job today, how long could I
survive on just the essentials?"

**Why this priority**: This is the headline output of the feature — the runway number
is the entire reason to build this tab. It's tied for top priority with marking
expenses essential because neither half is useful without the other.

**Independent Test**: Can be fully tested by adding one or more accounts with known
balances, marking a known set of expenses essential, and confirming the displayed
runway in months matches total spendable balance divided by monthly essential burn.

**Acceptance Scenarios**:

1. **Given** essential expenses with a combined monthly burn rate of $2,000 and a single
   account with a $7,060 balance and 0% penalty/tax, **When** the user opens the Runway
   tab, **Then** the displayed runway is 3.53 months (7,060 / 2,000).
2. **Given** two accounts — "Cash" with $2,000 at 0% haircut and "401k" with $10,000 at
   30% haircut — and a $2,000 monthly essential burn, **When** the user opens the Runway
   tab, **Then** total spendable is $9,000 (2,000 + 10,000 × 0.70) and the displayed
   runway is 4.5 months.
3. **Given** no essential expenses are marked, **When** the user opens the Runway tab,
   **Then** the page shows a clear message (e.g. "no essential expenses selected") instead
   of attempting a division by zero.
4. **Given** no accounts have been added yet, **When** the user opens the Runway tab,
   **Then** total spendable is $0 and the runway is displayed as 0 months (assuming at
   least one essential expense exists).

---

### User Story 3 - Manage multiple accounts (Priority: P2)

As the user, I want to add, edit, and remove named accounts with their own balance and
penalty/tax rate, so I can model my real mix of cash, savings, investments, and
retirement accounts rather than being limited to one or two fixed fields.

**Why this priority**: Supporting an arbitrary number of accounts with individual
haircut rates makes the runway number realistic across a variety of account types, but
the feature already delivers core value with even a single account (covered by User
Story 2). This story adds flexibility on top.

**Independent Test**: Can be fully tested by adding several accounts with different
names, balances, and penalty/tax percentages, confirming each is listed with its own
values, and confirming the total spendable amount reflects all of them summed after
each one's individual haircut.

**Acceptance Scenarios**:

1. **Given** the Runway tab, **When** the user adds a new account with a name, balance,
   and penalty/tax percentage, **Then** the account appears in the account list and
   contributes to the total spendable amount.
2. **Given** an existing account, **When** the user edits its balance or penalty/tax
   percentage, **Then** the runway recalculates using the updated values.
3. **Given** an existing account, **When** the user removes it, **Then** it no longer
   contributes to the total spendable amount or appears in the account list.
4. **Given** an account with no penalty/tax percentage entered, **When** the runway is
   calculated, **Then** that account's full balance counts toward spendable total (0%
   default haircut).

### Edge Cases

- What happens when an essential expense uses a recurrence type that doesn't divide
  evenly into a month (day-of-week, biweekly)? The monthly-equivalent amount MUST reuse
  the existing annual-cost conversion (annual cost ÷ 12) rather than a new approximation,
  so the same recurrence produces a consistent value across the Annual Cost and Runway
  tabs.
- What happens when a penalty/tax percentage would be entered as negative or over 100%?
  System MUST reject values outside 0–100.
- What happens when an account balance is entered as negative? System MUST reject
  negative balances.
- What happens when all expenses are marked essential? The essential burn rate equals
  the same figure the Annual Cost tab would show divided by 12, summed across every
  expense.
- What happens when the runway divides evenly (e.g. exactly 4 months)? The result MUST
  still display with the same precision/rounding convention as a non-even result, so the
  display format doesn't change based on the value.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a new page reachable from the main navigation,
  labeled "Runway," alongside the existing Leftover, Pay Schedule, Expenses, and Annual
  Cost tabs.
- **FR-002**: System MUST persist an "essential" flag on every recurring expense,
  defaulting to not-essential for existing and newly created expenses.
- **FR-003**: System MUST let the user set an expense's essential flag in the add/edit
  expense form, and MUST show which expenses are essential (an "Essential" tag) on the
  Expenses list. *(Amended 2026-10-20: previously an inline checkbox that saved
  immediately; moved into the form so there is one place to change it.)*
- **FR-004**: System MUST let the user create named accounts, each with a balance and an
  optional penalty/tax percentage (0–100, default 0), and persist them.
- **FR-005**: System MUST let the user edit and delete existing accounts.
- **FR-006**: System MUST reject negative account balances and penalty/tax percentages
  outside the 0–100 range.
- **FR-007**: System MUST compute each essential expense's monthly-equivalent amount by
  reusing the existing annual-cost conversion for its recurrence type, divided by 12.
- **FR-008**: System MUST compute total monthly essential burn as the sum of the
  monthly-equivalent amounts of every expense currently marked essential.
- **FR-009**: System MUST compute each account's spendable contribution as its balance
  reduced by its own penalty/tax percentage, and sum these across all accounts for the
  total spendable amount.
- **FR-010**: System MUST compute and display the runway as total spendable amount
  divided by total monthly essential burn, expressed in months to two decimal places
  (e.g. "3.53 months").
- **FR-011**: System MUST display a clear message instead of a runway number when total
  monthly essential burn is $0 (no essential expenses marked), avoiding a divide-by-zero
  result.
- **FR-012**: System MUST display a runway of 0 months when total spendable amount is
  $0 and at least one essential expense exists.
- **FR-013**: System MUST always compute essential burn rate and runway from current,
  live expense and account data at request time — it MUST NOT cache a stale computed
  runway value.

### Key Entities

- **RecurringExpense (extended)**: gains a persisted boolean `essential` attribute
  (default false) alongside its existing name, amount, category, and recurrence fields.
- **Account** (new): a named store of money the user could draw on if income stopped.
  Attributes: name (free text, e.g. "Cash", "Savings", "401k"), balance (money),
  penalty/tax percentage (0–100, default 0, representing the portion lost to early-
  withdrawal penalties or taxes before the balance is usable). Independent of
  RecurringExpense; the user manages an arbitrary number of these.
- **Runway** (computed, not persisted): monthly essential burn rate (derived from
  RecurringExpense records marked essential), total spendable amount (derived from all
  Account records), and the resulting runway expressed in months.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can mark their essential expenses and see a runway-in-months figure
  within a single page view, with no manual arithmetic required.
- **SC-002**: The displayed runway always equals total spendable amount (after each
  account's own haircut) divided by total monthly essential burn, with no rounding
  discrepancy beyond the displayed precision.
- **SC-003**: A user can model an arbitrary mix of account types (e.g. 3+ accounts with
  different haircut rates) and see them all reflected in a single combined spendable
  total.
- **SC-004**: Marking or unmarking an expense as essential, or adding/editing/removing
  an account, is reflected in the displayed runway the next time the page is viewed,
  with no manual refresh or stale data.

## Assumptions

- "Monthly-equivalent" burn reuses the Annual Cost feature's fixed-multiplier
  annualization (×12 day-of-month, ×52 day-of-week, ×26 biweekly) divided by 12, rather
  than a new day-counting method — consistent with that feature's existing, tested
  conversion and the project's preference for reusing library logic.
- Account balances and penalty/tax percentages are entered and stored as of "now" — this
  feature does not track balance history over time or project future contributions/
  growth; it answers "if I stopped earning today, using what I have right now."
- Penalty/tax percentage is a single blended estimate the user supplies per account
  (e.g. combining an early-withdrawal penalty and an estimated marginal tax rate into
  one number); the system does not model tax brackets or specific penalty rules.
- Money continues to be handled as integer cents internally; the penalty/tax percentage
  is the only non-cent numeric input, and the final runway-in-months value is the only
  fractional (non-cents) computed output.
- Essential/non-essential is a manual, per-expense user judgment — the system does not
  infer essentiality from category or any other heuristic.
