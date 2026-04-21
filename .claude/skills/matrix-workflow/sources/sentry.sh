#!/bin/bash
# sources/sentry.sh — fetch a Sentry issue and emit the common adapter JSON.
# Input:  $1 = Sentry issue id (numeric)
# Output (stdout): {"title": "...", "body": "...", "url": "...", "labels": []}
# Exit codes:
#   0 = success
#   2 = not configured
#   other = runtime failure (issue not found, network, auth, etc.)
# Config (config.env): SENTRY_TOKEN, SENTRY_BASE_URL (e.g. https://sentry.matrixai.xin)

# shellcheck disable=SC1091
source "$(dirname "$0")/../config.env" 2>/dev/null || true

set -eu

if [ -z "${SENTRY_TOKEN:-}" ] || [ -z "${SENTRY_BASE_URL:-}" ]; then
  echo "sentry source not configured: set SENTRY_TOKEN and SENTRY_BASE_URL in .claude/skills/matrix-workflow/config.env" >&2
  exit 2
fi

id="${1:-}"
if [ -z "$id" ]; then
  echo "Usage: sources/sentry.sh <issue_id>" >&2
  exit 1
fi

base="${SENTRY_BASE_URL%/}"
url="${base}/api/0/issues/${id}/"

response=$(curl -sS --fail-with-body -w "\n%{http_code}" \
  -H "Authorization: Bearer ${SENTRY_TOKEN}" \
  "$url") || {
    echo "sentry fetch failed for issue ${id}: $response" >&2
    exit 3
  }

http_code="${response##*$'\n'}"
body="${response%$'\n'*}"

if [ "$http_code" != "200" ]; then
  echo "sentry fetch failed (HTTP ${http_code}): $body" >&2
  exit 3
fi

echo "$body" | jq --arg base "$base" '
  def err:
    (.metadata.type // "") as $t | (.metadata.value // "") as $v |
    if ($t == "" and $v == "") then ""
    else "**Error:** " + $t + (if $t != "" and $v != "" then ": " else "" end) + $v + "\n\n"
    end;
  {
    title: .title,
    url: (.permalink // ($base + "/issues/" + (.id // "")) ),
    labels: [],
    body: (
      "**Short ID:** " + (.shortId // "n/a") + "\n" +
      "**Culprit:** " + (.culprit // "n/a") + "\n" +
      "**Platform:** " + (.platform // "n/a") + "\n" +
      "**Level:** " + (.level // "n/a") + "\n" +
      "**Status:** " + (.status // "n/a") + "\n" +
      "**Events:** " + (.count // "0" | tostring) +
        "  **Users:** " + (.userCount // 0 | tostring) + "\n" +
      "**First seen:** " + (.firstSeen // "n/a") + "\n" +
      "**Last seen:** " + (.lastSeen // "n/a") + "\n\n" +
      err +
      "---\n" +
      "[View in Sentry](" + (.permalink // "") + ")"
    )
  }'
