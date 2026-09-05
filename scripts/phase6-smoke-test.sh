#!/bin/sh
set -eu

base_url="${BASE_URL:-http://localhost:5173}"
cookie_jar=$(mktemp)
trap 'rm -f "$cookie_jar"' EXIT

curl --fail --silent --cookie-jar "$cookie_jar" \
  -H 'Content-Type: application/json' \
  -d '{"email":"casey.patel@example.invalid","password":"HarborView!Local2026","remember":false}' \
  "$base_url/api/v1/auth/login" >/dev/null

claims=$(curl --fail --silent --cookie "$cookie_jar" "$base_url/api/v1/claims")
claim_id=$(printf '%s' "$claims" | python3 -c 'import json,sys; print(next(c["id"] for c in json.load(sys.stdin) if c["claim_number"] == "HVC-SYN-2026-00024"))')
run_key="phase6-smoke-$(date +%s)"
brief=$(curl --fail --silent --cookie "$cookie_jar" -H 'Content-Type: application/json' \
  -d "{\"task\":\"What property address is documented?\",\"idempotency_key\":\"$run_key\"}" \
  "$base_url/api/v1/claims/$claim_id/briefs")

printf '%s' "$brief" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["validation_state"] == "valid"
assert payload["provider"] == "local_deterministic"
assert payload["safety_flags"]
assert payload["human_review_required"] is True
assert payload["citations"]
'

curl --fail --silent --cookie "$cookie_jar" "$base_url/api/v1/operations/summary" >/dev/null
echo "Phase 6 professional session -> governed brief -> authorized operations passed"
