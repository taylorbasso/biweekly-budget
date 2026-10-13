# Quickstart: Validating the Aurora Postgres Migration

## 1. Local development (US2)

```bash
brew install postgresql@16 && brew services start postgresql@16
createdb budget_dev && createdb budget_test
source .venv/bin/activate && pip install -e '.[dev]'
./scripts/check.sh              # pytest (against budget_test) + mypy — all green
./scripts/dev-server.sh restart # http://127.0.0.1:5001 against budget_dev
```
Expected: register an account, set a pay schedule, add expenses; data survives a server restart.
Run the Aug 14 worked example from `specs/001-pay-cycle-leftover/quickstart.md` unchanged.

## 2. Infrastructure (US3)

In `~/code/basso-infra/basso-root/us-west-2/biweekly-budget`: `terragrunt plan` shows only the additions in [contracts/infrastructure.md](contracts/infrastructure.md); apply.
Expected: from a laptop, `psql "host=<db_endpoint> ..."` times out (not public); the cluster shows encryption on, backups enabled, min capacity 0.

## 3. Cutover (US1)

1. Tag the current image `sqlite-final` in ECR (rollback anchor).
2. Push the new image; apply the task-definition change; wait for a healthy task.
3. Register at https://budget.taylorbasso.dev and re-enter your pay schedule and expenses.
4. Redeploy the service: data persists. Leave idle ≥5 min: the next request takes ~15–30 s, then is normal.

**Rollback**: redeploy the `sqlite-final` image/task definition.
