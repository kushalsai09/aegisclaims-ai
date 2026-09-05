# Cost Management

## Principles

Cost is a design constraint and observable quality dimension. Optimize cost per acceptable supported workflow—not token price in isolation. A cheaper model that increases review or error rates may cost more operationally.

## Cost attribution

Every model invocation records provider/model, prompt/schema versions, returned input/output tokens when available, retries, outcome, and latency. No provider pricing is hard-coded in Phase 7. A future effective-dated price-catalog adapter may estimate cost from recorded billing units and reconcile it to AWS billing aggregates; until that adapter exists, the product must not present token estimates as currency.

## Application controls

- Per-task model policy and maximum input/output tokens.
- Per-workflow model-call, tool-call, retry, elapsed-time, and estimated-cost budgets.
- Evidence deduplication and task-specific context assembly rather than whole-document prompts.
- Batch and content-hash cache embeddings; never cache across unauthorized scopes.
- Use deterministic logic or smaller evaluated models for narrow tasks.
- Rerank only a bounded candidate set and only if measured quality benefit justifies it.
- Stop workflows early on missing prerequisites or mandatory deterministic escalation.
- Rate/concurrency limits and circuit breakers for denial-of-wallet resistance.

## Infrastructure controls

- Right-size Fargate API/worker tasks and autoscale workers on queue depth/age.
- Schedule nonproduction scale-down and delete ephemeral resources.
- S3 lifecycle derived artifacts; retain originals/audit per approved policy.
- PostgreSQL query/index tuning before adding OpenSearch.
- Telemetry sampling and retention by value/data class without dropping security/audit events.
- AWS Budgets, Cost Anomaly Detection, service quotas, tags, and owner alerts.

## Required tags/dimensions

Environment, service, component, owner, cost center/project, managed-by, data classification, and ephemeral/expiry where supported. AI invocation dimensions add task and model policy; they must not contain claim/customer content.

## Gates and reporting

Evaluation reports quality, latency, and cost together by scenario. Candidate promotion requires no unapproved regression in cost per successful supported artifact and no budget breach. Dashboards show daily/monthly forecast, per-workflow distributions, retries/waste, idle resources, top task/model contributors, and review-adjusted cost.

## Optional-service economics

OpenSearch, Textract, AgentCore, and SageMaker require a written workload estimate, benchmark against the current adapter, incremental operational cost, security impact, and shutdown criterion. Portfolio visibility alone is not justification.
