#!/usr/bin/env bash
# One-time AWS setup for the biweekly-budget ECS deployment: ECR repo, log
# group, task execution IAM role, ECS cluster (Fargate + Fargate Spot), and a
# security group locked to the caller's current public IP on port 8000.
#
# Safe to re-run: every step checks for the existing resource first.
set -euo pipefail

cd "$(dirname "$0")"

APP_NAME="biweekly-budget"
CONTAINER_PORT=8000

AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
AWS_REGION="$(aws configure get region)"
if [ -z "$AWS_REGION" ]; then
  echo "No default AWS region configured (aws configure set region <region>)." >&2
  exit 1
fi

ECR_REPO_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${APP_NAME}"

echo "==> ECR repository"
aws ecr describe-repositories --repository-names "$APP_NAME" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "$APP_NAME" >/dev/null
echo "$ECR_REPO_URI"

echo "==> CloudWatch log group"
aws logs describe-log-groups --log-group-name-prefix "/ecs/${APP_NAME}" \
  --query "logGroups[?logGroupName=='/ecs/${APP_NAME}']" --output text | grep -q . || \
  aws logs create-log-group --log-group-name "/ecs/${APP_NAME}"

echo "==> IAM task execution role"
ROLE_NAME="${APP_NAME}-execution-role"
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
  echo "Waiting for IAM role to propagate..."
  sleep 10
fi
EXECUTION_ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)"

echo "==> ECS cluster"
CLUSTER_STATUS="$(aws ecs describe-clusters --clusters "$APP_NAME" \
  --query 'clusters[0].status' --output text 2>/dev/null || echo MISSING)"
if [ "$CLUSTER_STATUS" != "ACTIVE" ]; then
  aws ecs create-cluster --cluster-name "$APP_NAME" \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 >/dev/null
fi

echo "==> Default VPC + subnets"
VPC_ID="$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text)"
if [ "$VPC_ID" = "None" ]; then
  echo "No default VPC found — create one or edit this script to use a specific VPC." >&2
  exit 1
fi
SUBNET_IDS="$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC_ID" \
  --query 'Subnets[].SubnetId' --output text | tr '\t' ',')"

echo "==> Security group locked to your current public IP"
MY_IP="$(curl -sS https://checkip.amazonaws.com)"
SG_NAME="${APP_NAME}-sg"
SG_ID="$(aws ec2 describe-security-groups \
  --filters Name=group-name,Values="$SG_NAME" Name=vpc-id,Values="$VPC_ID" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo None)"
if [ "$SG_ID" = "None" ]; then
  SG_ID="$(aws ec2 create-security-group --group-name "$SG_NAME" \
    --description "biweekly-budget: inbound ${CONTAINER_PORT} from owner's IP only" \
    --vpc-id "$VPC_ID" --query GroupId --output text)"
fi
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
  --protocol tcp --port "$CONTAINER_PORT" --cidr "${MY_IP}/32" >/dev/null 2>&1 || true

cat > .env <<EOF
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
AWS_REGION=$AWS_REGION
ECR_REPO_URI=$ECR_REPO_URI
EXECUTION_ROLE_ARN=$EXECUTION_ROLE_ARN
VPC_ID=$VPC_ID
SUBNET_IDS=$SUBNET_IDS
SECURITY_GROUP_ID=$SG_ID
EOF

echo
echo "Setup complete. Wrote deploy/.env:"
cat .env
echo
echo "Next: ./deploy/deploy.sh"
