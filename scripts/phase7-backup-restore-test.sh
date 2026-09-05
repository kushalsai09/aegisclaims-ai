#!/bin/sh
set -eu

compose_file="infrastructure/docker/compose.yaml"
restore_db="insurance_ops_phase7_restore"
dump_file=$(mktemp -t phase7-backup.XXXXXX)

cleanup() {
  docker compose -f "$compose_file" exec -T postgres \
    dropdb --if-exists -U insurance "$restore_db" >/dev/null 2>&1 || true
  rm -f "$dump_file"
}
trap cleanup EXIT INT TERM

source_counts=$(docker compose -f "$compose_file" exec -T postgres psql \
  -U insurance -d insurance_ops -Atc \
  "SELECT (SELECT count(*) FROM claims) || ':' || (SELECT count(*) FROM documents) || ':' || (SELECT version_num FROM alembic_version);")
docker compose -f "$compose_file" exec -T postgres \
  pg_dump -U insurance -d insurance_ops -Fc >"$dump_file"
docker compose -f "$compose_file" exec -T postgres \
  dropdb --if-exists -U insurance "$restore_db" >/dev/null
docker compose -f "$compose_file" exec -T postgres \
  createdb -U insurance "$restore_db"
docker compose -f "$compose_file" exec -T postgres \
  pg_restore -U insurance -d "$restore_db" --no-owner --no-privileges <"$dump_file"

verification=$(docker compose -f "$compose_file" exec -T postgres psql \
  -U insurance -d "$restore_db" -Atc \
  "SELECT (SELECT count(*) FROM claims) || ':' || (SELECT count(*) FROM documents) || ':' || (SELECT version_num FROM alembic_version);")

printf '%s' "$verification" | python3 -c '
import sys
restored = sys.stdin.read().strip()
assert restored == sys.argv[1]
assert restored.split(":")[2] == "20260826_0007"
' "$source_counts"

echo "Phase 7 isolated PostgreSQL backup and restore verification passed: $verification"
