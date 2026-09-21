# Research: Credit Cards Tracking

No open technical unknowns — this feature follows the exact same stack, storage, and
CRUD/calculation patterns already established by features 001-004. This document records
the two non-obvious decisions specific to this feature's math.

## Decision 1: Payoff-time formula

**Decision**: Use the standard fixed-payment loan amortization formula to estimate months
to payoff:

```
i = (interest_rate / 100) / 12          # monthly periodic rate, interest_rate is APR
n = -ln(1 - i * balance / payment) / ln(1 + i)     # months, when i > 0
n = balance / payment                              # months, when i == 0
```

Result is rounded up (`ceil`) to whole months, since a partial month still requires a
payment.

**Rationale**: This is the textbook amortization formula (derived from the future-value-of-
an-annuity relation) used by virtually every online credit card/loan payoff calculator. It
needs only `balance`, `interest_rate`, and `payment` — exactly the fields the spec defines
— and stdlib `math.log`/`math.ceil`, no new dependency.

**Alternatives considered**:
- *Simulate month-by-month* (loop applying interest then subtracting payment until balance
  ≤ 0): mathematically equivalent, easier to read, but O(n) in the number of months instead
  of O(1) and requires an iteration cap to avoid an infinite loop on bad input. Rejected in
  favor of the closed-form formula, but the closed-form's edge-case guards (below) cover the
  same failure mode the iteration cap would have handled.
- *Simple linear estimate* (`balance / payment`, ignoring interest entirely): fails the
  spec's explicit requirement that interest rate be part of the payoff calculation
  (FR-009) and would understate payoff time for any account with a real interest rate.

**Edge cases handled explicitly** (per spec Edge Cases / User Story 4):
- `balance <= 0` → 0 months ("already paid off"), formula not evaluated.
- `payment <= 0` → never pays off (`None`), formula not evaluated (avoids division by
  zero).
- `interest_rate == 0` → falls back to simple `ceil(balance / payment)`, since the formula
  above has a `ln(1+i)` denominator that is undefined at `i = 0`.
- `payment <= monthly interest accrued on balance` (i.e. `i * balance / payment >= 1`) →
  the log's argument would be ≤ 0 (undefined); treated as never pays off (`None`), matching
  real-world behavior (the balance doesn't shrink).

## Decision 2: which payment amount drives the payoff estimate

**Decision**: Use `actual_payment` when it's greater than zero; otherwise fall back to
`minimum_payment`. This mirrors the spec's Edge Cases section verbatim.

**Rationale**: A user who hasn't yet decided on an "actual" payment plan still gets a
meaningful estimate based on the minimum payment, which is always required by the
creditor. Once they fill in an actual/planned payment, the estimate reflects their real
plan.

**Alternatives considered**: Always require actual_payment to be set — rejected, adds
friction for a field the spec treats as optional-in-practice (defaults to 0 like other
optional money fields in this codebase, e.g. `Account.penalty_tax_percent`).

## Non-decisions (reused as-is from existing codebase conventions)

- **Storage**: new `credit_account` SQLite table, same `db.py` module, no ORM (Principle
  I).
- **Money representation**: `balance`, `minimum_payment`, `actual_payment` stored as
  integer cents, matching every other money field in the app (Principle V / FR-013).
  `interest_rate` is not money — stored as a `REAL` (float) percentage, e.g. `24.99`.
- **CRUD route/template shape**: mirrors the existing `Account` CRUD (`account_new`,
  `account_create`, `account_edit`, `account_update`, `account_delete` in `routes.py`,
  `account_form.html` template) introduced for the Runway feature — same shape, new
  entity.
- **Delete confirmation**: none of the existing delete buttons (`expense_delete`,
  `account_delete`) have a confirmation step. This spec explicitly requires one (FR-007),
  so the new delete button gets a plain `onclick="return confirm(...)"` — no new
  dependency, smallest possible addition that satisfies the requirement without changing
  the existing delete buttons' behavior.
