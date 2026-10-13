# Implementation Plan: Move Storage to Aurora Postgres Serverless v2

**Branch**: `007-aurora-postgres-migration` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

## Summary

Swap `sqlite3` for PostgreSQL (psycopg 3, plain SQL, no ORM) in `src/budget/db.py`. Deployed, the
app uses an Aurora PostgreSQL Serverless v2 cluster added to the existing `biweekly-budget`
Terraform stack in `~/code/basso-infra`. The database starts empty: no data transfer, and the
now-pointless `claim-legacy` command and nullable `user_id` are removed. Local dev and tests use
a local PostgreSQL. Business logic modules are untouched.

## Technical Context

- **Language**: Python 3.11; add dependency `psycopg[binary]>=3.2`
- **Storage**: PostgreSQL 17 (Aurora Serverless v2 deployed; local Postgres for dev/tests)
- **Testing**: pytest against a real local Postgres; mypy strict
- **Target**: ECS Fargate (ARM64) behind an ALB, us-west-2
- **Constraints**: no ORM; money stays integer cents; DB never public; no secrets in repo
- **Scale**: a few accounts, thousands of rows

## Constitution Check

All PASS, no violations (re-checked after design): single Flask app with plain driver and SQL
(I); calculation modules untouched (II); `mypy` strict stays clean (III); private, encrypted DB
with credentials from Secrets Manager (IV); money columns stay integer cents, existing boundary
tests rerun (V); every `db.py` function keeps `user_id` scoping and `test_isolation.py` runs on
Postgres (VI); schema lives in a tracked file (workflow).

## Design

### Application (this repo)

- **Connection config**: libpq's standard `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`,
  `PGDATABASE`, `PGSSLMODE` env vars only — `psycopg.connect("", row_factory=dict_row,
  connect_timeout=30)`. Missing/wrong config makes `create_app` raise (no fallback). `BUDGET_DB_PATH`
  and the `create_app(db_path)` argument are removed.
- **Schema**: one tracked `src/budget/schema.sql` of `CREATE TABLE IF NOT EXISTS` statements run
  at startup (replaces the SQLite `ALTER` ladder). Later changes append idempotent statements.
- **Conversion in `db.py`**: `?` → `%s`; `lastrowid` → `INSERT ... RETURNING id`;
  `sqlite3.IntegrityError` → `psycopg.errors.UniqueViolation`; drop `date.fromisoformat` /
  `isoformat()` (native `DATE`); `bool(row["essential"])` / `int(essential)` → native boolean.
  Function names and signatures are unchanged except the connection type; `routes.py`/`auth.py`
  only change the type annotation.
- **Removed**: `claim_legacy_rows`, the `claim-legacy` CLI command, `OWNED_TABLES`, the legacy
  migrations, `tests/integration/test_claim_legacy.py`, `test_db_migration.py`, the `Dockerfile`
  `/data` volume and `BUDGET_DB_PATH`, and the `claim-legacy` section of `CLAUDE.md`.
- **Tests**: `conftest.py` connects using `PG*` env (default `PGDATABASE=budget_test`) and, per
  test, runs `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` then the schema. Everything else
  in the suite is unchanged.
- **Dev**: `scripts/dev-server.sh` sets `PGDATABASE=budget_dev`.
- **Health check**: `/healthz` must not touch the DB, so the ALB doesn't keep the cluster awake or fail during a resume.

### Schema (types)

| Was | Now |
|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` |
| money `INTEGER` | `BIGINT` (exact cents) |
| ISO date `TEXT` | `DATE` |
| `created_at TEXT` | `TIMESTAMPTZ` |
| `essential INTEGER` | `BOOLEAN` |
| `interest_rate REAL` | `DOUBLE PRECISION` (model already uses `float`; not money) |
| nullable `user_id` | `user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE` |

Tables are otherwise as in the current `db.py` (`users`, `pay_schedule` with `UNIQUE(user_id)`,
`recurring_expense`, `account`, `credit_account`, plus the `user_id` indexes).

### Infrastructure (`~/code/basso-infra/basso-root/us-west-2/biweekly-budget`, new `database.tf`)

- DB subnet group from the existing `PrivateSubnet-*` subnets (looked up by Name tag, like the
  public ones already are); no public access.
- New DB security group: ingress 5432 only from the existing task security group.
- `aws_rds_cluster`: `aurora-postgresql` 17.x (SSL forced by default), `storage_encrypted`,
  `manage_master_user_password = true` (password lives in Secrets Manager, never in state),
  `database_name`/`master_username` = `budget`, no backup configuration (Aurora's 1-day minimum is left as is; it cannot be disabled),
  `skip_final_snapshot = true`, `serverlessv2_scaling_configuration { min_capacity = 0,
  max_capacity = 1, seconds_until_auto_pause = 300 }`. One `db.serverless` instance.
- Execution role: `secretsmanager:GetSecretValue` on the cluster's master secret only.
- Task definition: env `PGHOST` (cluster endpoint), `PGPORT`, `PGUSER`, `PGDATABASE`,
  `PGSSLMODE=require`; secret `PGPASSWORD` from `<secret_arn>:password::`.
- Order: push the new app image first, then apply (the task-definition change restarts the service).

## Complexity Tracking

None.
