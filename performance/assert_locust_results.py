from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--csv", required=True, type=Path)
    args = parser.parse_args()
    profiles = json.loads(Path("performance/profiles.json").read_text())
    threshold = profiles[args.profile]
    with args.csv.open(newline="") as handle:
        aggregate = next(row for row in csv.DictReader(handle) if row["Name"] == "Aggregated")
    requests = int(aggregate["Request Count"])
    failures = int(aggregate["Failure Count"])
    failure_rate = failures / requests if requests else 1.0
    p95 = float(aggregate["95%"])
    p99 = float(aggregate["99%"])
    assert failure_rate <= threshold["max_failure_rate"], (
        f"failure rate {failure_rate:.2%} exceeds {threshold['max_failure_rate']:.2%}"
    )
    assert p95 <= threshold["p95_ms"], f"p95 {p95:.0f}ms exceeds {threshold['p95_ms']}ms"
    assert p99 <= threshold["p99_ms"], f"p99 {p99:.0f}ms exceeds {threshold['p99_ms']}ms"
    print(
        f"{args.profile}: {requests} requests, {failures} failures, "
        f"p95={p95:.0f}ms, p99={p99:.0f}ms"
    )


if __name__ == "__main__":
    main()
