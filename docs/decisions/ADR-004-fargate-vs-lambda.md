# ADR-004: Fargate versus Lambda

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

The platform has a continuously available API, SSE progress, document parsing, database connections, and potentially long/variable workflow jobs. It also has short event-driven adapters.

## Decision

Run the API and asynchronous workers as containers on ECS/Fargate. Use Lambda only for bounded, short event-handling functions whose duration, packaging, concurrency, and connection behavior fit Lambda well.

## Alternatives

- **Lambda for all workloads:** scale-to-zero and simple events, but awkward long tasks, container/parser size, streaming, connection management, and local parity.
- **EKS:** flexible orchestration but unjustified cluster complexity.
- **AgentCore Runtime:** potentially useful for agent isolation but optional and not the general application host initially.

## Trade-offs and consequences

Fargate has baseline running cost and demands autoscaling/task operations. It offers consistent containers and fewer execution constraints. SQS decouples workers; tasks must be idempotent. Lambda functions cannot become shadow workflow engines.

## Success criteria

API/worker meet measured availability, latency, queue-age, deployment, and cost targets; graceful shutdown and retry tests pass. Each Lambda has a documented event, timeout, idempotency, DLQ, security policy, and reason it is preferable to an existing worker.
