#!/bin/sh
set -eu

base_url="${BASE_URL:-http://localhost:5173}"
claim_id="b9fce608-59c9-55d1-a865-db09b3e66db8"
admin_id="60000000-0000-4000-8000-000000000004"
run_key="phase5-smoke-$(date +%s)"

session_json=$(curl --fail --silent -H 'Content-Type: application/json' \
  -d "{\"user_id\":\"$admin_id\"}" "$base_url/api/v1/auth/dev/session")
token=$(printf '%s' "$session_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

brief=$(curl --fail --silent -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $token" \
  -d "{\"task\":\"What property address is documented?\",\"idempotency_key\":\"$run_key\"}" \
  "$base_url/api/v1/claims/$claim_id/briefs")
brief_id=$(printf '%s' "$brief" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
printf '%s' "$brief" | python3 -c '
import json, sys
p = json.load(sys.stdin)
assert p["status"] == "supported"
assert p["human_review_required"] is True
assert p["safety_flags"]
assert p["citations"] and all(c["claim_id"] == p["claim_id"] for c in p["citations"])
assert p["provider"] == "local_deterministic"
assert p["validation_state"] == "valid"
assert p["authority_notice"].startswith("AI-assisted evidence brief")
assert "approve this claim" not in (p["claim_summary"] + p["evidence_summary"]).lower()
'

retrieved=$(curl --fail --silent -H "Authorization: Bearer $token" "$base_url/api/v1/briefs/$brief_id")
printf '%s' "$retrieved" | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p["id"] == sys.argv[1]' "$brief_id"

echo "Phase 5 authorized retrieval -> deterministic model -> strict validation -> cited brief passed"
