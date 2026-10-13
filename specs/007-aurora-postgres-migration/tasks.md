# Tasks: Move Storage to Aurora Postgres Serverless v2

**Input**: `specs/007-aurora-postgres-migration/` (plan.md, spec.md, research.md, quickstart.md)

No new tests are written; existing tests are converted to run on PostgreSQL. Infra tasks edit the separate repo `~/code/basso-infra`. Order below follows dependency (US2 and US3 before US1 despite priority, since US1 is the deploy that needs both).

## Phase 1: Setup

- [ ] T001 Install and start a local PostgreSQL and create `budget_dev` and `budget_test` databases (`brew install postgresql@16`, `createdb`)
- [ ] T002 Add `psycopg[binary]>=3.2` to dependencies in `pyproject.toml` and install it into `.venv`

## Phase 2: Foundational (application code on PostgreSQL)

- [ ] T003 Create `src/budget/schema.sql` with idempotent `CREATE TABLE IF NOT EXISTS` for `users`, `pay_schedule` (`UNIQUE(user_id)`), `recurring_expense`, `account`, `credit_account`, using the types in plan.md (identity PKs, `BIGINT` money, `DATE`, `TIMESTAMPTZ`, `BOOLEAN`, `DOUBLE PRECISION`, `user_id NOT NULL ... ON DELETE CASCADE`) plus the `user_id` indexes; add `schema.sql` to package data in `pyproject.toml`
- [ ] T004 Rewrite `src/budget/db.py` for psycopg: `connect()` using `psycopg.connect("", row_factory=dict_row, connect_timeout=30)`; `init_db()` runs `schema.sql`; convert every CRUD function (`?`→`%s`, `RETURNING id`, `UniqueViolation`, native dates/booleans); remove `claim_legacy_rows`, `OWNED_TABLES`, and all SQLite migration helpers
- [ ] T005 Update `src/budget/app.py`: remove `db_path` argument, `DATABASE` config, `sqlite3` import, and the `claim-legacy` command; `create_app` calls `db.connect()` + `db.init_db()` and fails loudly if it can't; type `get_db()` as the psycopg connection
- [ ] T006 [P] Update `src/budget/wsgi.py` to call `create_app()` with no path
- [ ] T007 [P] Change the connection type annotations (`sqlite3.Connection` → psycopg connection) in `src/budget/routes.py` and `src/budget/auth.py`; confirm `/healthz` in `src/budget/auth.py` does not touch the database

## Phase 3: User Story 2 - Local dev and tests on PostgreSQL (P2)

**Goal**: app, dev server, and full test suite work locally. **Independent test**: `./scripts/check.sh` passes.

- [ ] T008 [US2] Update `tests/conftest.py`: drop `db_path`; default `PGDATABASE=budget_test`; per test run `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` then `init_db`; `create_app(config)` only
- [ ] T009 [P] [US2] Delete `tests/integration/test_claim_legacy.py` and `tests/integration/test_db_migration.py`
- [ ] T010 [US2] Fix remaining SQLite references in `tests/integration/test_auth.py`, `tests/integration/test_isolation.py`, and `tests/integration/test_routes.py` so they run on PostgreSQL
- [ ] T011 [US2] Set `PGDATABASE=budget_dev` in `scripts/dev-server.sh`; add a clear failure message to `scripts/check.sh` if PostgreSQL is unreachable
- [ ] T012 [US2] Run `./scripts/check.sh` until pytest and mypy pass clean; then start the dev server and walk the Aug 14 example from `specs/001-pay-cycle-leftover/quickstart.md` in the browser with chrome-devtools

## Phase 4: User Story 3 - Private database as code (P2)

**Goal**: Aurora cluster exists in `~/code/basso-infra`, private. **Independent test**: `terragrunt plan` shows only the additions below; no public access.

- [ ] T013 [US3] In `~/code/basso-infra/basso-root/us-west-2/biweekly-budget/`, create `database.tf` with: private subnet lookup (`tag:Name = PrivateSubnet-*`), `aws_db_subnet_group`, `aws_security_group.db` with ingress 5432 only from `aws_security_group.task`
- [ ] T014 [US3] In the same `database.tf` add `aws_rds_cluster` (`aurora-postgresql` 17.x, `database_name`/`master_username` = `budget`, `storage_encrypted`, `manage_master_user_password = true`, `skip_final_snapshot = true`, `serverlessv2_scaling_configuration { min_capacity = 0, max_capacity = 1, seconds_until_auto_pause = 300 }`, the db security group, subnet group) and one `aws_rds_cluster_instance` (`db.serverless`, `publicly_accessible = false`)
- [ ] T015 [US3] In `~/code/basso-infra/basso-root/us-west-2/biweekly-budget/main.tf` add an execution-role policy allowing `secretsmanager:GetSecretValue` on the cluster's master secret ARN; add `db_endpoint` to `outputs.tf`

## Phase 5: User Story 1 - Deployed app on Aurora (P1)

**Goal**: production runs on Aurora. **Independent test**: register at https://budget.taylorbasso.dev, enter data, redeploy, data persists.

- [ ] T016 [US1] Update `Dockerfile`: remove `/data`, the `VOLUME`, and `BUDGET_DB_PATH`
- [ ] T017 [US1] In `~/code/basso-infra/basso-root/us-west-2/biweekly-budget/main.tf` task definition add env `PGHOST` (cluster endpoint), `PGPORT=5432`, `PGUSER=budget`, `PGDATABASE=budget`, `PGSSLMODE=require` and secret `PGPASSWORD` from `<master secret ARN>:password::`
- [ ] T018 [US1] Build and push the new image with `deploy/deploy.py`, then run `terragrunt apply` in the biweekly-budget stack (image first, so the restarted service gets the new code)
- [ ] T019 [US1] Verify in production per `specs/007-aurora-postgres-migration/quickstart.md`: register, enter pay schedule and expenses, redeploy and confirm persistence, confirm `psql` to the cluster endpoint from the laptop times out

## Phase 6: Polish

- [ ] T020 Update `CLAUDE.md` and `README.md`: remove the `claim-legacy` sections, document local Postgres setup and the `PG*` env vars, drop `BUDGET_DB_PATH`; remove the SQLite lines from `.gitignore` only if nothing else uses them
- [ ] T021 Delete the stale local SQLite files (`budget.db`, `instance/`) if untracked and unwanted

## Dependencies

T001–T002 → T003–T007 → US2 (T008–T012) → US1 code (T016). US3 (T013–T015) is independent of the app code and can run in parallel with US2; T017 needs T014. T018 needs T012, T015, T016, T017. T019 needs T018. Polish last.

Parallel: T006 ∥ T007; T009 ∥ T008; US2 ∥ US3.

## Strategy

MVP = everything through T019 (it is one cutover). Nothing is partial-deployable: finish US2 locally first, then infra, then deploy.
