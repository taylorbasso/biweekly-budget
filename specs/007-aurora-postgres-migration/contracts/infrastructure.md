# Contract: Changes to `~/code/basso-infra` (stack `basso-root/us-west-2/biweekly-budget`)

Add `database.tf` to the existing stack (it already owns the task SG, execution role, and task definition).

| Resource | Key settings |
|---|---|
| `data.aws_subnets.private` | filter VPC `MainVPC`, `tag:Name = PrivateSubnet-*` |
| `aws_db_subnet_group` | the private subnets (≥2 AZs) |
| `aws_security_group.db` | no egress needed; ingress 5432 via `aws_vpc_security_group_ingress_rule` from `aws_security_group.task` only |
| `aws_rds_cluster_parameter_group` | family `aurora-postgresql16`, `rds.force_ssl = 1` |
| `aws_rds_cluster` | `engine=aurora-postgresql`, `engine_version=16.x`, `database_name=budget`, `master_username=budget`, `manage_master_user_password=true`, `storage_encrypted=true`, `backup_retention_period=7`, `deletion_protection=true`, `skip_final_snapshot=false` (+ final snapshot id), `serverlessv2_scaling_configuration { min_capacity=0 max_capacity=1 seconds_until_auto_pause=300 }` |
| `aws_rds_cluster_instance` | `instance_class=db.serverless`, `publicly_accessible=false`, same engine |
| `aws_iam_role_policy.execution_db_secret` | `secretsmanager:GetSecretValue` on `aws_rds_cluster.app.master_user_secret[0].secret_arn` |
| task definition | env `PGHOST`(cluster endpoint) `PGPORT=5432` `PGUSER=budget` `PGDATABASE=budget` `PGSSLMODE=require`; secret `PGPASSWORD` ← `<secret_arn>:password::` |
| ECS Exec (for import) | `enable_execute_command=true` on the service; new task role with `ssmmessages:*Channel` permissions (needed only during import — may be applied then removed) |

Outputs to add: `db_endpoint`, `db_secret_arn`.

Apply order: infra first (cluster + SG + env, task keeps running the SQLite image until the new image is pushed — the old image ignores `PG*`), then app image deploy.
Note: the Terraform task definition change itself rolls the service, so the new image should be pushed *before* applying the task-definition change, or apply the cluster alone first via `-target`.
