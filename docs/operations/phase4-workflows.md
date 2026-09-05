# Phase 4 Workflow Operations

Each transition records workflow ID, claim ID, workflow version, stage, checkpoint version, actor when human, correlation ID, and timestamp. Audit and workflow events exclude question bodies and document bodies. The workflow input is retained on the workflow record for reviewer context; logs contain neither it nor evidence text.

For a waiting workflow, inspect the API workflow and history endpoints, confirm the latest checkpoint and input fingerprint, then use an authorized supervisor/admin review. A 409 means the form is stale or the lifecycle has already advanced; reload rather than resubmitting an older version.

For a failed workflow, inspect `error_code`, bounded `error_detail`, history, infrastructure readiness, and correlation ID. Retry only after correcting the dependency and within the two-attempt budget. Do not relabel infrastructure failure as insufficient evidence.

Container verification uses the established Compose stack, `scripts/wait-for-stack.sh`, and `scripts/phase4-smoke-test.sh`. Restart/resume validation starts a mandatory-review workflow, restarts the API/worker containers, retrieves the same checkpoint, and then submits the authorized human action.

