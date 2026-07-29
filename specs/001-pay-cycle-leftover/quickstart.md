# Quickstart: Pay Cycle Leftover

Validates the feature end-to-end using the example from the spec: paid Friday July 31,
next paid Friday August 14.

## Prerequisites

- Python 3.11+
- Dependencies installed (Flask, pytest, mypy — see `research.md` for why each was
  chosen)
- A fresh local SQLite database file (no pay schedule or expenses recorded yet)

## Setup

```bash
# from repo root
python -m venv .venv && source .venv/bin/activate
pip install -e .
flask --app src.budget.app run
```

The app starts bound to `127.0.0.1:5000` (Constitution Principle IV — never exposed
beyond localhost by default).

## Scenario 1: Set the pay schedule (US2)

1. Open `http://127.0.0.1:5000/pay-schedule`.
2. Submit anchor date `2026-07-31`, amount `2000.00`.
3. **Expected**: page shows anchor date `2026-07-31` and amount `$2,000.00`.

## Scenario 2: Record recurring expenses with categories (US3, US4 setup)

1. Open `http://127.0.0.1:5000/expenses/new`.
2. Add: name `Rent`, amount `1200.00`, day-of-month `1`, category `Housing`.
3. Add: name `Investment transfer`, amount `100.00`, day-of-week `Friday`, category
   `Investments`.
4. Add: name `Streaming`, amount `15.00`, day-of-month `31`, category left blank.
5. **Expected**: `GET /expenses` lists all three.

## Scenario 3: Check leftover for the current cycle (US1)

1. Open `http://127.0.0.1:5000/?date=2026-08-01`.
2. **Expected**: cycle shown as `2026-07-31` through `2026-08-13`, next pay date
   `2026-08-14`.
   - `Rent` ($1200, day-of-month 1) is due Aug 1 — inside the cycle (`07-31`–`08-13`
     includes Aug 1) — confirms FR-008's inclusive start boundary.
   - `Investment transfer` ($100) occurs twice — Friday Jul 31 and Friday Aug 7 — for
     $200 total.
   - `Streaming` ($15, day-of-month 31): July has 31 days, so it's due Jul 31 — inside
     the cycle.
   - Total expenses: $1200 + $200 + $15 = $1415. Leftover:
     `$2000.00 − $1415.00 = $585.00`.

## Scenario 4: Category breakdown for the same cycle (US4)

1. Open `http://127.0.0.1:5000/breakdown?date=2026-08-01`.
2. **Expected**: same cycle range as Scenario 3.
   - `Housing`: $1200.00
   - `Investments`: $200.00
   - `Uncategorized`: $15.00 (the `Streaming` expense had no category)
   - Total across categories: $1415.00 — matches Scenario 3's total expenses exactly
     (spec US4 AC2).

## Scenario 5: Day-of-month clamping edge case (spec Edge Cases)

1. With `Streaming` still due on day-of-month `31`, check the cycle containing
   `2026-08-14` (`08-14`–`08-27`, next pay `08-28`).
2. **Expected**: August has 31 days too, so `Streaming` is due `2026-08-31` — outside
   this cycle (`08-27` is the last day). Check the following cycle (`08-28`–`09-10`,
   next pay `09-11`) instead: `2026-08-31` falls inside this cycle's range
   (`08-28` ≤ `08-31` ≤ `09-10`), so `Streaming` is due there. September's own clamped
   date (`2026-09-30`, since September has only 30 days) falls outside this cycle and
   is instead due in the *next* cycle after that. Confirms FR-006 clamps to month-end
   per calendar month rather than erroring or skipping the month entirely, and that
   every occurrence lands in exactly one cycle (Principle V) — never zero, never two.

## Automated validation

```bash
mypy src/
pytest tests/
```

Both MUST pass before the feature is considered complete (Constitution Principles III
and V).
