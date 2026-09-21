# Quickstart: Savings Runway

Manual validation walkthrough, mirroring the worked examples in `spec.md` User Story 2.

## Prerequisites

```bash
./scripts/dev-server.sh restart   # after implementation lands in src/budget/*.py
```

Open `http://127.0.0.1:5001/runway` in a browser (or drive it with the chrome-devtools
MCP tools per this project's UI-testing convention).

## Scenario A: single account, simple runway

1. On `/expenses`, ensure (or add) recurring expenses whose combined monthly-equivalent
   cost is $2,000 — e.g. a `day_of_month` rent expense of $2,000 (monthly-equivalent =
   $2,000 exactly, since `annual_cost = amount × 12` for day-of-month).
2. On `/runway`, check the "Essential" box for that expense.
3. Add an account: name "Cash", balance `7060.00`, penalty/tax % `0`.
4. **Expected**: the page displays a runway of **3.53 months** (7,060 ÷ 2,000).

## Scenario B: multiple accounts with different haircuts

1. With the same $2,000/month essential burn from Scenario A:
2. Add a second account: name "401k", balance `10000.00`, penalty/tax % `30`.
3. **Expected**: total spendable is $9,000 (2,000 + 10,000 × 0.70) and the displayed
   runway is **4.5 months**.

## Scenario C: zero essential expenses

1. Uncheck every expense's "Essential" box.
2. **Expected**: the page shows a message such as "No essential expenses selected" in
   place of a runway number — no error page, no divide-by-zero.

## Scenario D: zero accounts

1. Re-check at least one essential expense so monthly burn is > $0.
2. Delete every account.
3. **Expected**: total spendable is $0 and the displayed runway is **0.00 months**.

## Regression check

- `/annual-cost` still shows the same annual cost figures as before (the Runway feature
  only adds a new `monthly_equivalent` wrapper around the existing `annual_cost()`, it
  doesn't change it).
- `/expenses` still lists and edits expenses normally — the new `essential` column
  doesn't appear on that page (it's only editable from `/runway`, per FR-003).

## Automated checks

```bash
./scripts/check.sh   # pytest tests/ + mypy src/ — must both pass clean
```
