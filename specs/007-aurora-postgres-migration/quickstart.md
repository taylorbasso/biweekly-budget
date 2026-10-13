# Quickstart: Validating the Aurora Postgres Migration

## 1. Local development (US3)

```bash
brew install postgresql@16 && brew services start postgresql@16
createdb budget_dev && createdb budget_test
source .venv/bin/activate && pip install -e '.[dev]'
./scripts/check.sh              # pytest (against budget_test) + mypy — all green
./scripts/dev-server.sh restart # http://127.0.0.1:5001 against budget_dev
```
Expected: register an account, set a pay schedule, add expenses; data survives a server restart.
Run the Aug 14 worked example from `specs/001-pay-cycle-leftover/quickstart.md` unchanged.

## 2. Data transfer rehearsal (US2)

```bash
cp budget.db /tmp/rehearsal.sqlite3          # or instance/budget.sqlite3
flask --app src.budget.app import-sqlite --path /tmp/rehearsal.sqlite3 --replace
```
Expected: exit 0; every table line shows equal source/target counts; every account shows equal leftover. Re-run: same result. Corrupt a money value in the copy: exits 1 naming the row.

## 3. Infrastructure (US4)

In `~/code/basso-infra/basso-root/us-west-2/biweekly-budget`: `terragrunt plan` shows only the additions in [contracts/infrastructure.md](contracts/infrastructure.md); apply.
Expected: from a laptop, `psql "host=<db_endpoint> ..."` times out (not public); the cluster shows encryption on and backups enabled.

## 4. Cutover (US1)

1. Tag the current image `sqlite-final` in ECR (rollback anchor).
2. Push the new image; apply the task-definition change; wait for a healthy task.
3. Import production data through ECS Exec (see research R9) if any exists worth keeping.
4. Sign in at https://budget.taylorbasso.dev: leftover and breakdown match pre-cutover numbers.
5. Redeploy the service: data persists. First request after ≥5 min idle may take ~15–30 s, then normal.

**Rollback**: redeploy the `sqlite-final` image/task definition; Aurora data written after cutover is not carried back.
