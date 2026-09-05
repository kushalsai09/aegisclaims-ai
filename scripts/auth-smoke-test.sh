#!/bin/sh
set -eu

base_url="${BASE_URL:-http://localhost:5173}"
cookie_jar=$(mktemp)
trap 'rm -f "$cookie_jar"' EXIT

login=$(curl --fail --silent --cookie-jar "$cookie_jar" \
  -H 'Content-Type: application/json' \
  -d '{"email":"avery.morgan@example.invalid","password":"HarborView!Local2026","remember":false}' \
  "$base_url/api/v1/auth/login")

printf '%s' "$login" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["user"]["display_name"] == "Avery Morgan"
assert payload["user"]["roles"] == ["claims_adjuster"]
assert "access_token" not in payload
'

curl --fail --silent --cookie "$cookie_jar" "$base_url/api/v1/auth/session" \
  | python3 -c 'import json,sys; assert json.load(sys.stdin)["email"] == "avery.morgan@example.invalid"'
curl --fail --silent --cookie "$cookie_jar" "$base_url/api/v1/claims" >/dev/null
curl --fail --silent --cookie "$cookie_jar" -X POST "$base_url/api/v1/auth/logout" >/dev/null

status=$(curl --silent --output /dev/null --write-out '%{http_code}' --cookie "$cookie_jar" "$base_url/api/v1/claims")
test "$status" = "401"

echo "Phase 6 email/password -> HttpOnly session -> authorized claims -> logout passed"
