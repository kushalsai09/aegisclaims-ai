#!/bin/sh
set -eu

base_url="${BASE_URL:-http://localhost:5173}"
claim_id="30000000-0000-4000-8000-000000000001"
user_id="60000000-0000-4000-8000-000000000001"

curl --fail --silent "$base_url/" | grep -q '<div id="app"></div>'

session_json=$(curl --fail --silent \
  -H 'Content-Type: application/json' \
  -d "{\"user_id\":\"$user_id\"}" \
  "$base_url/api/v1/auth/dev/session")

token=$(printf '%s' "$session_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

workspace=$(curl --fail --silent \
  -H "Authorization: Bearer $token" \
  "$base_url/api/v1/claims/$claim_id")

printf '%s' "$workspace" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["claim"]["claim_number"] == "HVC-SYN-2026-00017"
assert payload["policy"]["product_code"] == "HO-SYN-01"
document_names = {item["name"] for item in payload["documents"]}
assert {"Synthetic Notice of Loss.pdf", "Synthetic Contractor Estimate.pdf"} <= document_names
assert all(section["status"] == "not_implemented" for section in payload["future_sections"])
'

echo "Frontend -> API -> configured database smoke test passed"
