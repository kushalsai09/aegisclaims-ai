#!/bin/sh
set -eu

base_url="${BASE_URL:-http://localhost:5173}"
claim_id="41ab5d18-f804-5a3e-9d4c-7647bc76cc4c"
user_id="60000000-0000-4000-8000-000000000004"

session_json=$(curl --fail --silent \
  -H 'Content-Type: application/json' \
  -d "{\"user_id\":\"$user_id\"}" \
  "$base_url/api/v1/auth/dev/session")

token=$(printf '%s' "$session_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

answer=$(curl --fail --silent \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $token" \
  -d '{"question":"What rule applies to the roof age evidence?","limit":5}' \
  "$base_url/api/v1/claims/$claim_id/questions")

printf '%s' "$answer" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["state"] == "answerable"
assert payload["answerable"] is True
assert payload["citations"]
assert all(item["claim_id"] == "41ab5d18-f804-5a3e-9d4c-7647bc76cc4c" for item in payload["citations"])
assert all(item["source_url"].startswith("/documents/") for item in payload["citations"])
assert payload["human_review_required"] is True
assert payload["retrieval_configuration"] == "hybrid_rrf_k60_v1"
assert payload["generator_provider"] == "local_deterministic"
'

echo "Phase 3 authorized retrieval -> stable citations -> grounded answer smoke test passed"
