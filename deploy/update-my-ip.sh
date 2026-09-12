#!/usr/bin/env bash
# Re-lock the security group's inbound rule to your current public IP.
# Run this whenever you can't reach the app and suspect your IP changed.
set -euo pipefail

cd "$(dirname "$0")"

CONTAINER_PORT=8000

if [ ! -f .env ]; then
  echo "deploy/.env not found — run ./deploy/setup.sh first." >&2
  exit 1
fi
source .env

MY_IP="$(curl -sS https://checkip.amazonaws.com)"
echo "Current public IP: $MY_IP"

EXISTING_CIDRS="$(aws ec2 describe-security-groups --group-ids "$SECURITY_GROUP_ID" \
  --query "SecurityGroups[0].IpPermissions[?FromPort==\`${CONTAINER_PORT}\`].IpRanges[].CidrIp" \
  --output text)"

for cidr in $EXISTING_CIDRS; do
  if [ "$cidr" != "${MY_IP}/32" ]; then
    aws ec2 revoke-security-group-ingress --group-id "$SECURITY_GROUP_ID" \
      --protocol tcp --port "$CONTAINER_PORT" --cidr "$cidr" >/dev/null
    echo "Revoked stale rule for $cidr"
  fi
done

aws ec2 authorize-security-group-ingress --group-id "$SECURITY_GROUP_ID" \
  --protocol tcp --port "$CONTAINER_PORT" --cidr "${MY_IP}/32" >/dev/null 2>&1 || true

echo "Security group ${SECURITY_GROUP_ID} now allows only ${MY_IP}/32 on port ${CONTAINER_PORT}."
