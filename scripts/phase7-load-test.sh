#!/bin/sh
set -eu

profile="${1:-smoke}"
base_url="${BASE_URL:-http://localhost:5173}"
output_dir="${LOAD_RESULTS_DIR:-.local/load-results}"

case "$profile" in
  smoke) users=2; spawn_rate=2; run_time=20s ;;
  normal) users=10; spawn_rate=2; run_time=2m ;;
  stress) users=25; spawn_rate=5; run_time=3m ;;
  *) echo "profile must be smoke, normal, or stress" >&2; exit 2 ;;
esac

mkdir -p "$output_dir"
prefix="$output_dir/phase7-$profile"
.venv/bin/locust -f performance/locustfile.py --headless --host "$base_url" \
  --users "$users" --spawn-rate "$spawn_rate" --run-time "$run_time" \
  --csv "$prefix" --only-summary
.venv/bin/python performance/assert_locust_results.py \
  --profile "$profile" --csv "${prefix}_stats.csv"
