#!/usr/bin/env bash
# Build the image, push it to ECR, register a new task definition revision,
# and create (first run) or update (subsequent runs) the ECS service.
# Requires deploy/setup.sh to have been run first.
set -euo pipefail

cd "$(dirname "$0")"

APP_NAME="biweekly-budget"

if [ ! -f .env ]; then
  echo "deploy/.env not found — run ./deploy/setup.sh first." >&2
  exit 1
fi
source .env

CONTAINER_CMD="${CONTAINER_CMD:-podman}"
IMAGE_URI="${ECR_REPO_URI}:latest"

echo "==> Building image ($CONTAINER_CMD)"
"$CONTAINER_CMD" build -t "$IMAGE_URI" ..

echo "==> Logging in to ECR"
aws ecr get-login-password --region "$AWS_REGION" | \
  "$CONTAINER_CMD" login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> Pushing image"
"$CONTAINER_CMD" push "$IMAGE_URI"

echo "==> Registering task definition"
sed \
  -e "s|__EXECUTION_ROLE_ARN__|${EXECUTION_ROLE_ARN}|g" \
  -e "s|__IMAGE_URI__|${IMAGE_URI}|g" \
  -e "s|__AWS_REGION__|${AWS_REGION}|g" \
  task-def.json > task-def.rendered.json
aws ecs register-task-definition --cli-input-json file://task-def.rendered.json >/dev/null

SERVICE_STATUS="$(aws ecs describe-services --cluster "$APP_NAME" --services "$APP_NAME" \
  --query 'services[0].status' --output text 2>/dev/null || echo MISSING)"

if [ "$SERVICE_STATUS" = "ACTIVE" ]; then
  echo "==> Updating existing service"
  aws ecs update-service --cluster "$APP_NAME" --service "$APP_NAME" \
    --task-definition "$APP_NAME" --force-new-deployment >/dev/null
else
  echo "==> Creating service"
  aws ecs create-service --cluster "$APP_NAME" --service-name "$APP_NAME" \
    --task-definition "$APP_NAME" --desired-count 1 \
    --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_IDS}],securityGroups=[${SECURITY_GROUP_ID}],assignPublicIp=ENABLED}" >/dev/null
fi

echo "==> Waiting for task to reach RUNNING"
aws ecs wait services-stable --cluster "$APP_NAME" --services "$APP_NAME"

TASK_ARN="$(aws ecs list-tasks --cluster "$APP_NAME" --service-name "$APP_NAME" \
  --query 'taskArns[0]' --output text)"
ENI_ID="$(aws ecs describe-tasks --cluster "$APP_NAME" --tasks "$TASK_ARN" \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)"
PUBLIC_IP="$(aws ec2 describe-network-interfaces --network-interface-ids "$ENI_ID" \
  --query 'NetworkInterfaces[0].Association.PublicIp' --output text)"

echo
echo "Deployed: http://${PUBLIC_IP}:8000"
echo "(Only reachable from the IP allowed in the ${APP_NAME}-sg security group — run deploy/update-my-ip.sh if your IP changed.)"
