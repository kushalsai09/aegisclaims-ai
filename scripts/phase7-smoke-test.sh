#!/bin/sh
set -eu

base_url="${BASE_URL:-http://localhost:5173}"
cookie_jar=$(mktemp)
headers=$(mktemp)
trap 'rm -f "$cookie_jar" "$headers"' EXIT

ready=$(curl --fail --silent "$base_url/health/ready")
printf '%s' "$ready" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["status"] == "ready"
assert all(value == "ready" for value in payload["checks"].values())
'

curl --fail --silent --dump-header "$headers" --output /dev/null "$base_url/health/live"
grep -qi '^X-Content-Type-Options: nosniff' "$headers"
grep -qi '^X-Frame-Options: DENY' "$headers"
grep -qi '^Content-Security-Policy:' "$headers"
grep -qi '^Permissions-Policy:' "$headers"

i=1
while [ "$i" -le 11 ]; do
  status=$(curl --silent --output /dev/null --write-out '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d '{"email":"phase7-limit@example.invalid","password":"wrong-password","remember":false}' \
    "$base_url/api/v1/auth/login")
  i=$((i + 1))
done
test "$status" = "429"

curl --fail --silent --cookie-jar "$cookie_jar" \
  -H 'Content-Type: application/json' \
  -d '{"email":"casey.patel@example.invalid","password":"HarborView!Local2026","remember":false}' \
  "$base_url/api/v1/auth/login" >/dev/null

claims=$(curl --fail --silent --cookie "$cookie_jar" \
  "$base_url/api/v1/claims?limit=2&offset=0")
printf '%s' "$claims" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert isinstance(payload, list) and len(payload) == 2
'

metrics=$(curl --fail --silent "http://localhost:8000/metrics/")
printf '%s' "$metrics" | grep -q 'insurance_authentication_attempts_total'
printf '%s' "$metrics" | grep -q 'insurance_rate_limit_rejections_total'

echo "Phase 7 readiness, security headers, distributed-limit boundary, session, pagination, and metrics passed"
