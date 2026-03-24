#!/usr/bin/env bash
# MinIO initialization for DevTrack
# Prerequisites: mc (MinIO Client) installed and alias configured
#
# Usage:
#   1. Set your MinIO alias:  mc alias set myminio http://121.31.38.35:19000 minioadmin minioadmin123
#   2. Run this script:       bash scripts/minio-init.sh myminio
#   3. Copy the access key and secret key output into backend/.env

set -euo pipefail

ALIAS="${1:?Usage: $0 <mc-alias>}"
BUCKET="devtrack-uploads"
USER="devtrack-app"

echo "==> Creating bucket: ${BUCKET}"
mc mb "${ALIAS}/${BUCKET}" --ignore-existing

echo "==> Setting public read policy on bucket"
mc anonymous set download "${ALIAS}/${BUCKET}"

echo "==> Creating policy: ${USER}-policy"
cat > /tmp/devtrack-policy.json <<'POLICY'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::devtrack-uploads/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::devtrack-uploads"]
    }
  ]
}
POLICY
mc admin policy create "${ALIAS}" "${USER}-policy" /tmp/devtrack-policy.json

echo "==> Creating user: ${USER}"
# Generate a random password
PASSWORD=$(openssl rand -base64 24)
mc admin user add "${ALIAS}" "${USER}" "${PASSWORD}"
mc admin policy attach "${ALIAS}" "${USER}-policy" --user "${USER}"

echo "==> Creating access key for ${USER}"
mc admin user svcacct add "${ALIAS}" "${USER}"

echo ""
echo "============================================"
echo "Add the access key and secret key above to backend/.env:"
echo ""
echo "MINIO_ENDPOINT=121.31.38.35:19000"
echo "MINIO_ACCESS_KEY=<access key from above>"
echo "MINIO_SECRET_KEY=<secret key from above>"
echo "MINIO_BUCKET=devtrack-uploads"
echo "MINIO_USE_SSL=False"
echo "MINIO_PUBLIC_URL=http://121.31.38.35:19000/devtrack-uploads"
echo "============================================"

rm -f /tmp/devtrack-policy.json
