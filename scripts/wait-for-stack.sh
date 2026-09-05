#!/bin/sh
set -eu

attempt=0
until curl --fail --silent http://localhost:5173/healthz >/dev/null && \
      curl --fail --silent http://localhost:8000/health/ready | grep -q '"status":"ready"'; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    echo "Stack did not become ready within 120 seconds" >&2
    exit 1
  fi
  sleep 2
done

echo "Stack is ready"
