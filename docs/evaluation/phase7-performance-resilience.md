# Phase 7 Performance and Resilience Evaluation

The Locust workload signs in through real application sessions and mixes
bounded claim lists, claim workspace, document detail, dashboard, hybrid
evidence search, grounded question, latest evidence brief, and latest workflow
reads. Four fictional employees distribute authentication/model limits without
disabling the production controls.

| Profile | Users | Ramp | Duration | Error ceiling | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|
| smoke | 2 | 2/s | 20 s | 1% | 1.5 s | 3.0 s |
| normal | 10 | 2/s | 2 min | 1% | 1.5 s | 3.0 s |
| stress | 25 | 5/s | 3 min | 2% | 2.5 s | 5.0 s |

The assertion script reads Locust aggregate CSV output and fails the run when
any ceiling is exceeded. Smoke is the routine local/CI-sized evidence run;
normal and stress are manually scheduled because they consume time and can
disturb a developer stack.

The resilience exercise verifies readiness becomes 503 during loss of Valkey,
MinIO, and PostgreSQL, returns after each dependency recovers, then confirms an
application session survives API/worker restart. The backup exercise restores
to an isolated database and checks the authoritative migration and fixture
counts. These tests demonstrate local adapter/process behavior, not AWS
multi-AZ failover or regional recovery.

