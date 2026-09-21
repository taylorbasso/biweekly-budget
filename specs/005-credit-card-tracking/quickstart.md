# Quickstart: Credit Cards Tracking

Worked example for manual validation, in the style of the 001 feature's quickstart.

## Setup

1. Start the dev server: `./scripts/dev-server.sh restart` (after implementation lands).
2. Navigate to `/credit-cards`. With no entries yet, the page shows an empty state and a
   link to add one (User Story 1, Acceptance Scenario 2).

## Scenario A: add two entries, verify independent column totals

Add entry 1 (a credit card):

- Name: `Visa`
- Balance: `2000.00`
- Interest rate: `20` (20% APR)
- Minimum payment: `50.00`
- Actual payment: `100.00`

Add entry 2 (a loan, using the same form):

- Name: `Car Loan`
- Balance: `5000.00`
- Interest rate: `6`
- Minimum payment: `150.00`
- Actual payment: *(leave blank / 0)*

**Expected table**:

| Name     | Balance   | Min. Payment | Actual Payment | Payoff Time |
|----------|-----------|--------------|-----------------|-------------|
| Visa     | $2,000.00 | $50.00       | $100.00         | ~25 months  |
| Car Loan | $5,000.00 | $150.00      | $0.00           | ~37 months  |
| **Totals** | **$7,000.00** | **$200.00** | **$100.00** | *(blank)*   |

This confirms FR-004 (Totals sums balance/min/actual independently, not payoff time) and
User Story 1's Acceptance Scenario 3.

**Payoff time hand-check** (research.md Decision 1 formula):

- Visa: `i = 0.20/12 ≈ 0.016667`; payment used = actual ($100, since it's > 0);
  `n = -ln(1 - 0.016667*2000/100) / ln(1.016667) ≈ 24.5` → rounds up to **25 months**.
- Car Loan: `i = 0.06/12 = 0.005`; payment used = minimum ($150, since actual is 0);
  `n = -ln(1 - 0.005*5000/150) / ln(1.005) ≈ 36.6` → rounds up to **37 months**.

This validates SC-004 (payoff estimate matches manual amortization calc within ±1 period)
and the "falls back to minimum payment when actual is unset" rule (research.md Decision 2,
Edge Cases).

## Scenario B: edit and see payoff time recalculate

Edit `Visa`: change actual payment from `100.00` to `50.00` (equal to its minimum). Save.

**Expected**: payoff time for Visa increases substantially (smaller payment → longer
payoff) with no separate recalculation step (SC-003).

## Scenario C: never-pays-off case

Add a third entry: `Maxed Card`, balance `1000.00`, interest rate `24`, minimum payment
`0.00`, actual payment `0.00`.

**Expected**: payoff time column shows a clear "Never" / "Won't pay off at this rate"
indicator (User Story 4, Acceptance Scenario 2) — not an error, not a misleading number,
not a blank cell.

## Scenario D: paid-off case

Edit `Maxed Card`: set balance to `0.00`.

**Expected**: payoff time column shows "Paid off" (User Story 4, Acceptance Scenario 3).

## Scenario E: validation

Attempt to add an entry with balance `-50` or with non-numeric text in the balance field.

**Expected**: form re-renders with a validation error, no new row is created, existing
rows and Totals are unaffected (SC-005).

## Scenario F: delete with confirmation

Click "Remove" on any entry.

**Expected**: a confirmation dialog appears; dismissing it leaves the entry in place;
confirming it removes the row and updates the Totals row (User Story 3).
