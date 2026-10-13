# Research: Aurora Postgres Migration

Decisions, each chosen for simplicity:

- **Driver**: `psycopg` 3, no pool, one connection per request (as today). Not SQLAlchemy (ORM/extra layer), not psycopg2 (older).
- **Schema management**: a single idempotent `schema.sql` run at startup, as the app does now. No Alembic or migration runner; there is no old data to upgrade.
- **Credentials**: RDS-managed master secret in Secrets Manager, injected by ECS as `PGPASSWORD`; the rest are plain `PG*` env vars that libpq reads natively, so the app needs no config code. No IAM auth, no separate app role.
- **Encryption in transit**: Aurora PostgreSQL 17 forces SSL by default; `PGSSLMODE=require`. No CA bundle in the image.
- **Network**: DB in the existing private subnets, SG open only to the task SG. Tasks stay in public subnets as today; Aurora needs no NAT or VPC endpoints.
- **Idle behavior (confirmed)**: min 0 ACU, pause after 5 min, max 1 ACU, single instance. First request after a pause takes ~15 s; `connect_timeout=30` lets it succeed.
- **Tests**: real local PostgreSQL (same engine as production), schema reset per test. No Docker or testcontainers.
- **Data transfer / legacy ownership**: none. Fresh start, so importer, `claim-legacy`, and nullable `user_id` are all removed.
- **Rollback**: redeploy the previous commit's image.
