#!/bin/sh
set -eu

compose_file="infrastructure/docker/compose.yaml"
base_url="${BASE_URL:-http://localhost:5173}"
cookie_jar=$(mktemp)

restore_dependencies() {
  docker compose -f "$compose_file" start postgres redis minio >/dev/null 2>&1 || true
  rm -f "$cookie_jar"
}
trap restore_dependencies EXIT INT TERM

wait_ready() {
  attempts=0
  until curl --fail --silent "$base_url/health/ready" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    test "$attempts" -lt 45
    sleep 2
  done
}

expect_not_ready() {
  attempts=0
  status=000
  while [ "$attempts" -lt 20 ]; do
    status=$(curl --silent --output /tmp/phase7-readiness.json --write-out '%{http_code}' \
      "$base_url/health/ready" || true)
    test "$status" = "503" && return 0
    attempts=$((attempts + 1))
    sleep 1
  done
  echo "expected readiness 503, received $status" >&2
  return 1
}

wait_ready
curl --fail --silent --cookie-jar "$cookie_jar" \
  -H 'Content-Type: application/json' \
  -d '{"email":"casey.patel@example.invalid","password":"HarborView!Local2026","remember":false}' \
  "$base_url/api/v1/auth/login" >/dev/null

docker compose -f "$compose_file" stop redis >/dev/null
expect_not_ready
docker compose -f "$compose_file" start redis >/dev/null
wait_ready

docker compose -f "$compose_file" stop minio >/dev/null
expect_not_ready
docker compose -f "$compose_file" start minio >/dev/null
wait_ready

docker compose -f "$compose_file" stop postgres >/dev/null
expect_not_ready
docker compose -f "$compose_file" start postgres >/dev/null
wait_ready

docker compose -f "$compose_file" restart api worker >/dev/null
wait_ready
curl --fail --silent --cookie "$cookie_jar" "$base_url/api/v1/claims?limit=1" >/dev/null

echo "Phase 7 dependency-loss, recovery, process restart, and durable-session checks passed"

