#!/bin/sh
set -eu

base_url="${BASE_URL:-http://localhost:5173}"
claim_id="41ab5d18-f804-5a3e-9d4c-7647bc76cc4c"
admin_id="60000000-0000-4000-8000-000000000004"
run_key="phase4-smoke-$(date +%s)"

session_json=$(curl --fail --silent \
  -H 'Content-Type: application/json' \
  -d "{\"user_id\":\"$admin_id\"}" \
  "$base_url/api/v1/auth/dev/session")
token=$(printf '%s' "$session_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

workflow=$(curl --fail --silent \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $token" \
  -d "{\"task\":\"What rule applies to the roof age evidence?\",\"idempotency_key\":\"$run_key\"}" \
  "$base_url/api/v1/claims/$claim_id/workflows")

workflow_id=$(printf '%s' "$workflow" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
checkpoint=$(printf '%s' "$workflow" | python3 -c 'import json,sys; print(json.load(sys.stdin)["checkpoint_version"])')
printf '%s' "$workflow" | python3 -c '
import json, sys
p = json.load(sys.stdin)
assert p["status"] == "awaiting_human_review"
assert p["human_review_required"] is True
assert p["artifact"]["citations"]
assert p["artifact"]["proposed_next_steps"]
assert "approve_or_deny_claim" in p["artifact"]["forbidden_actions"]
assert p["artifact"]["authority_notice"].startswith("SYSTEM-GENERATED PROPOSAL")
'

reviewed=$(curl --fail --silent \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $token" \
  -d "{\"action\":\"acknowledge\",\"reason\":\"Authorized synthetic smoke review completed.\",\"expected_checkpoint_version\":$checkpoint,\"idempotency_key\":\"$run_key-review\"}" \
  "$base_url/api/v1/workflows/$workflow_id/review")
printf '%s' "$reviewed" | python3 -c '
import json, sys
p = json.load(sys.stdin)
assert p["status"] == "completed"
assert p["approval_state"] == "acknowledged"
'

history=$(curl --fail --silent \
  -H "Authorization: Bearer $token" \
  "$base_url/api/v1/workflows/$workflow_id/history")
printf '%s' "$history" | python3 -c '
import json, sys
p = json.load(sys.stdin)
assert len(p["events"]) >= 6
assert p["events"][0]["event_type"] == "workflow.created"
assert p["events"][-1]["event_type"] == "review.acknowledge"
assert p["events"][-1]["actor_user_id"] is not None
'

echo "Phase 4 controlled workflow -> durable checkpoint -> authorized review -> audited resume passed"
