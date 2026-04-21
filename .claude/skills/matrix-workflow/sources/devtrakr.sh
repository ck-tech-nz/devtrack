#!/bin/bash
# sources/devtrakr.sh — fetch a DevTrack issue and emit the common adapter JSON.
# Input:  $1 = issue id (numeric)
# Output (stdout): {"title": "...", "body": "...", "url": "...", "labels": [...]}
# Exit codes:
#   0 = success
#   2 = not configured
#   other = runtime failure (issue not found, network, auth, etc.)
# Config (config.env): DEVTRAKR_TOKEN, DEVTRAKR_BASE_URL (site root, e.g. https://devtrack.matrixai.xin)

# shellcheck disable=SC1091
source "$(dirname "$0")/../config.env" 2>/dev/null || true

set -eu

if [ -z "${DEVTRAKR_TOKEN:-}" ] || [ -z "${DEVTRAKR_BASE_URL:-}" ]; then
  echo "devtrakr source not configured: set DEVTRAKR_TOKEN and DEVTRAKR_BASE_URL in .claude/skills/matrix-workflow/config.env" >&2
  exit 2
fi

id="${1:-}"
if [ -z "$id" ]; then
  echo "Usage: sources/devtrakr.sh <issue_id>" >&2
  exit 1
fi

base="${DEVTRAKR_BASE_URL%/}"
api_url="${base}/api/external/issues/${id}/"

response=$(curl -sS --fail-with-body -w "\n%{http_code}" \
  -H "Authorization: Bearer ${DEVTRAKR_TOKEN}" \
  "$api_url") || {
    echo "devtrakr fetch failed for issue ${id}: $response" >&2
    exit 3
  }

http_code="${response##*$'\n'}"
body="${response%$'\n'*}"

if [ "$http_code" != "200" ]; then
  echo "devtrakr fetch failed (HTTP ${http_code}): $body" >&2
  exit 3
fi

echo "$body" | jq --arg base "$base" '{
  title: .title,
  url: ($base + "/issues/" + (.id | tostring)),
  labels: (.labels // []),
  body: (
    "**Issue:** " + (.issue_number // ("ISS-" + (.id | tostring))) + "\n" +
    "**Status:** " + (.status // "n/a") + "\n" +
    "**Priority:** " + (.priority // "n/a") + "\n" +
    "**Assignee:** " + (.assignee // "n/a") + "\n" +
    (if .source_feedback_id then "**Source feedback:** " + .source_feedback_id + "\n" else "" end) +
    "**Created:** " + (.created_at // "n/a") + "\n" +
    "**Updated:** " + (.updated_at // "n/a") + "\n" +
    (if .resolved_at then "**Resolved:** " + .resolved_at + "\n" else "" end) +
    (if .description then "\n" + .description + "\n" else "" end) +
    "\n---\n" +
    "[View in DevTrack](" + $base + "/issues/" + (.id | tostring) + ")"
  )
}'
