#!/bin/sh
set -eu

base_url="${BASE_URL:-http://localhost:5173}"
claim_id="30000000-0000-4000-8000-000000000001"
user_id="60000000-0000-4000-8000-000000000001"
upload_file="${UPLOAD_FILE:-data/synthetic/uploads/browser-demo-estimate.txt}"

session_json=$(curl --fail --silent \
  -H 'Content-Type: application/json' \
  -d "{\"user_id\":\"$user_id\"}" \
  "$base_url/api/v1/auth/dev/session")

token=$(printf '%s' "$session_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

upload_response=$(curl --silent --write-out '\n%{http_code}' \
  -H "Authorization: Bearer $token" \
  -F "file=@$upload_file;type=text/plain" \
  "$base_url/api/v1/claims/$claim_id/documents")
upload_status=$(printf '%s' "$upload_response" | tail -n 1)
upload_body=$(printf '%s' "$upload_response" | sed '$d')

if [ "$upload_status" = "201" ]; then
  document_id=$(printf '%s' "$upload_body" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["processing_status"] == "ready"
assert payload["document_type"] == "contractor_estimate"
assert payload["page_count"] == 1
print(payload["id"])
')
elif [ "$upload_status" = "409" ]; then
  document_id=$(printf '%s' "$upload_body" | python3 -c '
import json, re, sys
detail = json.load(sys.stdin)["detail"]
match = re.search(r"[0-9a-f-]{36}", detail)
assert match
print(match.group(0))
')
else
  printf '%s\n' "$upload_body"
  exit 1
fi

detail=$(curl --fail --silent \
  -H "Authorization: Bearer $token" \
  "$base_url/api/v1/documents/$document_id")

printf '%s' "$detail" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["pages"][0]["page_number"] == 1
assert payload["pages"][0]["extraction_method"] == "utf8_text_v1"
facts = {fact["fact_type"]: fact for fact in payload["facts"]}
assert facts["estimate_amount"]["normalized_value"] == "10425.00"
assert facts["estimate_amount"]["page_number"] == 1
assert payload["processing_history"][-1]["status"] == "ready"
'

echo "Phase 2 upload -> storage -> extraction -> classification -> facts -> provenance smoke test passed"
