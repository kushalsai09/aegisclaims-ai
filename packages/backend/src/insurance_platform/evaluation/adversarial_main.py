from __future__ import annotations

import json

from insurance_platform.evaluation.adversarial_model import evaluate_adversarial_model


def main() -> None:
    result = evaluate_adversarial_model()
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    if not result.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
