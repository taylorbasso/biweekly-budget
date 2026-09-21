# Implementation Plan: Credit Cards Tracking

**Branch**: `005-credit-card-tracking` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-credit-card-tracking/spec.md`

## Summary

Add a new "Credit Cards" tab listing every tracked credit card/loan (`CreditAccount`:
name, balance, interest rate, minimum payment, actual payment) in a table with a Totals
row summing balance/minimum payment/actual payment, plus a per-row computed payoff-time
estimate (standard amortization from balance, interest rate, and effective payment — see
research.md). Users can add, edit, and delete entries via a CRUD form that mirrors the
existing `Account` (Runway) CRUD exactly. The feature is a standalone ledger — no
integration with the pay-cycle leftover calculation. All new math (`payoff_months`,
`effective_payment`, `compute_credit_cards`) lives in `calculations.py`; routes stay thin
wrappers over `db.py`/`calculations.py`.

## Technical Context

**Language/Version**: Python 3.11+ (matches existing project)

**Primary Dependencies**: Flask, Jinja2 (already in use), stdlib `math` (`log`, `ceil`)
for the amortization formula. No new third-party dependency.

**Storage**: SQLite, via the existing `db.py` (no ORM). One new table (`credit_account`),
no changes to existing tables.

**Testing**: pytest — unit tests in `tests/unit/test_models.py` for `CreditAccount`
validation; unit tests in `tests/unit/test_calculations.py` for `payoff_months`
(zero-balance, zero-payment, zero-interest, payment-below-interest, normal case),
`effective_payment` (actual-payment fallback to minimum), and `compute_credit_cards`
(totals sum correctly and independently, empty-list case); integration tests in
`tests/integration/test_routes.py` for `GET /credit-cards` and full CRUD round-trip.

**Target Platform**: Same local Flask dev server bound to `127.0.0.1` only.

**Project Type**: Single project — extends the existing `src/budget/` package.

**Performance Goals**: N/A — single local user, same scale as features 001-004.

**Constraints**: No new runtime dependency; payoff time computed fresh on every page load
from live data, never cached or stored; money stays integer cents at rest
(`balance`/`minimum_payment`/`actual_payment`), `interest_rate` is the one new non-money
float field (an annual percentage, not currency).

**Scale/Scope**: Single user, a handful to a few dozen credit cards/loans at most —
negligible computational cost either way.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Simplicity First (YAGNI) | No new dependency (stdlib `math` only), no new interface, no frontend build tooling, no integration with the leftover/cycle system beyond what's asked for | PASS |
| II. Library-Oriented Design | `payoff_months`, `effective_payment`, `compute_credit_cards` all live in `calculations.py`, independent of Flask; new routes (`credit_cards`, `credit_account_new/create/edit/update/delete`) are thin — parse input, call `db.py`/`calculations.py`, render template | PASS |
| III. Type Safety & Static Checking | `CreditAccount`, `CreditAccountRow`, `CreditCardsTotals` are typed frozen dataclasses; `int \| None` for payoff months is explicit; mypy strict must pass | PASS |
| IV. Local-First Data Privacy | No new network calls, no telemetry; still SQLite + `127.0.0.1`-only | PASS |
| V. Correctness of Financial Calculations (NON-NEGOTIABLE) | Not a cycle-boundary/leftover calculation, so not strictly gated by this principle's literal scope — but it's still money math with real edge cases (zero balance, zero/near-zero payment, zero interest), so dedicated unit tests cover each case in research.md Decision 1, consistent with the spirit of this principle | PASS |

No violations — Complexity Tracking is empty.

*Re-checked after Phase 1 design (data-model.md, contracts/, quickstart.md): still PASS,
no new violations introduced by the concrete design.*

## Project Structure

### Documentation (this feature)

```text
specs/005-credit-card-tracking/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── web-routes-delta.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── budget/
    ├── models.py                    # gains CreditAccount frozen dataclass + validation
    ├── db.py                        # SCHEMA gains `credit_account` table; new
    │                               # list/get/create/update/delete_credit_account
    │                               # functions (mirrors Account CRUD exactly)
    ├── calculations.py              # gains payoff_months(), effective_payment(),
    │                               # CreditAccountRow, CreditCardsTotals,
    │                               # compute_credit_cards()
    ├── routes.py                    # gains: credit_cards() GET /credit-cards;
    │                               # credit_account_new/create/edit/update/delete
    │                               # (mirrors account CRUD routes)
    ├── app.py                       # gains a `payoff` Jinja filter formatting
    │                               # int|None months as "N months" / "Paid off" /
    │                               # "Never at this rate"
    ├── templates/
    │   ├── layout.html              # gains "Credit Cards" nav link
    │   ├── credit_cards.html        # NEW — table + Totals row, mirrors runway.html's
    │   │                            # account table section
    │   └── credit_account_form.html # NEW — create/edit form, mirrors account_form.html
    └── static/
        └── style.css                # reuses existing table/form styles; no new dependency

tests/
├── unit/
│   ├── test_models.py          # extended — CreditAccount validation (negative balance/
│   │                           # payments/rate, empty name)
│   └── test_calculations.py    # extended — payoff_months (all edge cases from
│                               # research.md Decision 1), effective_payment,
│                               # compute_credit_cards (totals + empty-list)
└── integration/
    └── test_routes.py          # extended — GET /credit-cards renders (empty and
                               # populated); create/edit/delete round-trip through the
                               # DB; validation-error paths return 400 without persisting
```

**Structure Decision**: Single project, extending the existing `src/budget/` layout from
features 001-004. No new module — payoff math is added to `calculations.py` per
Constitution Principle II, following the same placement as the Runway feature's
`compute_runway`. Two new templates (`credit_cards.html`, `credit_account_form.html`)
mirroring `runway.html`'s account table and `account_form.html` respectively;
`layout.html`, `models.py`, `db.py`, `routes.py`, `app.py`, and both test files are edited
in place. `contracts/web-routes-delta.md` documents all new routes since none of them
exist today.

## Complexity Tracking

*No entries — Constitution Check passed with no violations.*
