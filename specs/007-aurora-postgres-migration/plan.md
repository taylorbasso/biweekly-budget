# Implementation Plan: Move Storage to Aurora Postgres Serverless v2

**Branch**: `007-aurora-postgres-migration` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-aurora-postgres-migration/spec.md`

## Summary

Replace the `sqlite3` storage layer in `src/budget/db.py` with PostgreSQL via psycopg 3 and
plain SQL (no ORM). Deployed, the app talks to an Aurora PostgreSQL Serverless v2 cluster
defined in the existing `biweekly-budget` stack of `~/code/basso-infra` (private subnets, SG
open only to the app's task SG, encrypted, backups, master password in Secrets Manager
injected by ECS). Schema is applied from numbered SQL migration files tracked in the repo.
The database starts empty; no data is carried over, so the legacy `claim-legacy` command and nullable `user_id` are removed. Local dev and the whole test suite run against a
local PostgreSQL. Business logic modules (`cycles`, `calculations`, `charts`, `accounts`,
`models`) are untouched.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Flask, Flask-Login, Flask-WTF, Flask-Limiter, gunicorn (existing); add `psycopg[binary]>=3.2`

**Storage**: PostgreSQL 16 — Aurora PostgreSQL Serverless v2 (deployed), local PostgreSQL (dev/tests)

**Testing**: pytest against a real local PostgreSQL (`BUDGET_TEST_DATABASE_URL`); mypy strict

**Target Platform**: ECS Fargate (ARM64) behind an ALB in us-west-2; macOS dev machine

**Project Type**: web-service (single Flask app)

**Performance Goals**: pages < 2 s warm; first request after the 5-minute auto-pause may take up to ~30 s (see research R3)

**Constraints**: no ORM; money stays integer cents; DB never publicly reachable; credentials never in the repo or in Terraform state beyond what AWS-managed secrets provide

**Scale/Scope**: a handful of accounts, thousands of rows; 4 owned tables + `users`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Simplicity First | PASS | Still one Flask app; plain driver + SQL, no ORM, no Alembic; hand-rolled migration runner is ~20 lines and avoids a new dependency. Baseline now PostgreSQL per v4.0.0. |
| II. Library-Oriented | PASS | Only `db.py`, `app.py`, `wsgi.py` change; calculation modules untouched. |
| III. Type Safety | PASS | `psycopg.Connection[dict[str, Any]]` typed; `mypy src/` must stay clean. |
| IV. Data Privacy | PASS | DB private, encrypted at rest/in transit, creds from Secrets Manager; no third-party transfer, no telemetry. |
| V. Financial Correctness | PASS | Money columns stay integer cents (`BIGINT`); dates become `DATE`; existing boundary tests unchanged and rerun. |
| VI. Auth & Isolation | PASS | Every `db.py` function keeps `user_id` filtering; `test_isolation.py` runs on Postgres. |
| Workflow: tracked migrations | PASS | `src/budget/migrations/NNNN_*.sql` + `schema_migrations` table. |

No violations; Complexity Tracking not needed. **Post-design re-check: still PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/007-aurora-postgres-migration/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── configuration.md     # env vars, CLI commands
│   └── infrastructure.md    # changes to ~/code/basso-infra
├── checklists/requirements.md
└── tasks.md                 # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
src/budget/
├── db.py                    # rewritten for psycopg: connect(), run_migrations(), CRUD (same function names/signatures except conn type)
├── migrations/
│   └── 0001_initial.sql     # full current schema (users, pay_schedule, recurring_expense, account, credit_account)
├── app.py                   # create_app(database_url=...); get_db() returns psycopg connection; claim-legacy command removed
├── wsgi.py                  # reads BUDGET_DATABASE_URL / PG* env
└── routes.py, auth.py       # type annotation changes only (sqlite3.Connection → db.Connection)
tests/
├── conftest.py              # Postgres fixture: fresh schema per test
├── integration/             # test_db_migration.py replaced by test_migrations.py; test_claim_legacy.py deleted
scripts/
├── dev-server.sh            # sets BUDGET_DATABASE_URL for local dev DB
└── check.sh                 # unchanged; requires local Postgres up
Dockerfile                   # drop /data volume and BUDGET_DB_PATH
pyproject.toml               # + psycopg[binary]
```

**Structure Decision**: keep the existing single-project layout; add a `migrations/` data dir. The old in-place SQLite `ALTER` migrations and legacy-ownership code are dropped; there is no old data to upgrade.

## Complexity Tracking

None.
