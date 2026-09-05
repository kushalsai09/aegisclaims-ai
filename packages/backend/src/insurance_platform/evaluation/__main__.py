from __future__ import annotations

from insurance_platform.config import get_settings
from insurance_platform.delivery.components import build_components
from insurance_platform.evaluation.retrieval import evaluate, report


def main() -> None:
    components = build_components(get_settings())
    with components.session_factory() as session:
        result = evaluate(session)
        print(report(result))
        if not result.passed:
            raise SystemExit(1)
    components.engine.dispose()


if __name__ == "__main__":
    main()
