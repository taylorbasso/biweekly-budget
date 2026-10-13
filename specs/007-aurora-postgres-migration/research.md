# Research: Aurora Postgres Migration

## R1. Driver
- **Decision**: `psycopg` 3 (`psycopg[binary]`), `row_factory=dict_row`, no pool.
- **Rationale**: current standard Postgres driver, typed, `%s` params map 1:1 from the existing `?` SQL. One connection per request mirrors today's `get_db()`/teardown. Aurora handles a few connections trivially.
- **Alternatives**: psycopg2 (older, weaker typing); SQLAlchemy (ORM/Core — violates "no ORM", more machinery); psycopg_pool (unneeded at this scale).

## R2. Schema management
- **Decision**: numbered `.sql` files in `src/budget/migrations/`, applied in order at startup, recorded in a `schema_migrations(version)` table, guarded by `pg_advisory_xact_lock` so concurrent starts can't double-apply.
- **Rationale**: satisfies "tracked migrations" with ~20 lines and no dependency. The existing runtime `ALTER TABLE` ladder is dropped; `0001_initial` is the current final schema.
- **Alternatives**: Alembic/yoyo (extra dependency, overkill for one app); keep `CREATE IF NOT EXISTS` (not tracked, can't evolve).

## R3. Serverless v2 capacity & idle behavior
- **Decision**: min 0 ACU with auto-pause after 5 min, max 1 ACU, single writer instance, no Multi-AZ replica. App sets `connect_timeout=30` so a resume (~15 s) succeeds instead of erroring.
- **Rationale**: hobby app, cost matters; pausing makes idle cost ≈ storage only. Cost of the choice: first request after idle is slow. SC-003 (<2 s) therefore applies to warm requests; adjust spec wording.
- **Alternatives**: min 0.5 ACU (~$40/mo, always warm). Switch is one Terraform variable.
- Note: `/healthz` must not touch the DB, or the ALB health check would keep the cluster awake (and fail during resume). Verify during implementation.

## R4. Network placement
- **Decision**: cluster in the existing `PrivateSubnet-*` subnets (DB subnet group over ≥2 AZs, looked up by Name tag like the stack already does for public subnets), `publicly_accessible = false`, SG ingress 5432 only from the existing task SG. Tasks stay in public subnets with a public IP as today.
- **Rationale**: no NAT or VPC endpoints needed (Aurora needs no outbound); DB has no route to the internet. Satisfies FR-011.

## R5. Credentials
- **Decision**: `manage_master_user_password = true` (RDS-managed secret in Secrets Manager). ECS injects `PGPASSWORD` from the secret's `password` JSON key via `valueFrom = "<secret_arn>:password::"`; host/user/dbname/port/sslmode are plain env vars (`PGHOST`, `PGUSER`, `PGDATABASE`, `PGPORT`, `PGSSLMODE`). Execution role gets `secretsmanager:GetSecretValue` on that ARN only.
- **Rationale**: no password in Terraform state or repo, mirrors the existing SSM secret-key pattern, libpq reads `PG*` env natively so the app needs no extra config code. App uses the master user (hobby app; a separate app role is unneeded complexity).
- **Alternatives**: IAM database auth (token refresh logic); hand-made SSM password (more manual steps).

## R6. Encryption in transit
- **Decision**: `PGSSLMODE=require` plus cluster parameter `rds.force_ssl=1`.
- **Rationale**: encrypted and enforced server-side. `verify-full` would need the RDS CA bundle baked into the image; skipped as unnecessary inside a private VPC for a hobby app.

## R7. Type mapping
| SQLite | Postgres | Reason |
|---|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGINT GENERATED ALWAYS AS IDENTITY` | importer uses `OVERRIDING SYSTEM VALUE` then `setval` |
| money `INTEGER` | `BIGINT` | exact cents (FR-004) |
| ISO date `TEXT` | `DATE` | psycopg returns `date`, removing `fromisoformat` calls |
| `created_at TEXT` | `TIMESTAMPTZ` | |
| `essential INTEGER` | `BOOLEAN` | |
| `interest_rate REAL` | `DOUBLE PRECISION` | model already uses `float`; not money; avoids `Decimal` leaking into code |
- `cursor.lastrowid` → `INSERT ... RETURNING id`; `sqlite3.IntegrityError` → `psycopg.errors.UniqueViolation`; `INSERT OR`/`ON CONFLICT` upsert syntax already compatible; `PRAGMA foreign_keys` dropped (always on).

## R8. Test database
- **Decision**: tests require a local PostgreSQL reachable at `BUDGET_TEST_DATABASE_URL` (default `postgresql://localhost/budget_test`). Each test starts from `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` then runs migrations.
- **Rationale**: same engine as production (constitution workflow rule), simple, isolated. `./scripts/check.sh` fails fast with a clear message if the DB is unreachable.
- **Alternatives**: testcontainers/Docker (extra dependency); SQLite for tests (hides dialect bugs).
- Local install: `brew install postgresql@16` (or any Postgres ≥14); no Docker required.

## R9. Data transfer
- **Decision**: `flask import-sqlite --path FILE` (logic in `importer.py`). Reads the SQLite file read-only, then in **one Postgres transaction**: aborts if the target tables are non-empty unless `--replace` (truncates then loads), copies tables in FK order preserving ids, resets identity sequences, then verifies per-table counts and each user's leftover/breakdown computed from source vs target. Nonconforming values (non-integer money, unparsable dates) abort with the row identified. Source file is never written.
- **Rationale**: single-transaction + `--replace` makes it safe to re-run (FR-007); verification covers SC-001/SC-002.
- **Reaching the private DB**: the deployed DB is unreachable from a laptop by design. Run the command inside the Fargate task via ECS Exec (`enable_execute_command` + minimal `ssmmessages` task-role permissions, added to the stack), shipping the small SQLite file as base64 in the exec command. Local→local imports (dev) need nothing special.
- **Open point**: the current task definition has no persistent volume, so `/data/budget.sqlite3` in production is ephemeral. Before cutover confirm whether any production data exists worth carrying over; if not, only the local `budget.db`/`instance/` data needs importing.

## R10. Rollback
- Old image stays in ECR by digest; the SQLite file/backup is kept untouched. Rollback = redeploy previous task definition/image (infra keeps `:latest`, so tag the pre-cutover image `sqlite-final` before pushing the new one) and, if desired, leave the Aurora cluster in place (paused cost ≈ storage). Data written to Aurora after cutover is not back-ported (acceptable for a hobby app; stated in quickstart).
