from prometheus_client import Counter

AUTH_ATTEMPTS = Counter(
    "insurance_authentication_attempts_total",
    "Authentication outcomes without identity labels",
    ["provider", "outcome"],
)
RATE_LIMIT_REJECTIONS = Counter(
    "insurance_rate_limit_rejections_total",
    "Server-side abuse-control rejections",
    ["scope"],
)
WORKER_FAILURES = Counter(
    "insurance_worker_failures_total",
    "Worker processing or dependency failures",
    ["stage"],
)
