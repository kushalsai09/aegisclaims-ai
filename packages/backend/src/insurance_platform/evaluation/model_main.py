from __future__ import annotations

import json

from insurance_platform.config import get_settings
from insurance_platform.evaluation.model_assistance import evaluate_model_assistance
from insurance_platform.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)


def main() -> None:
    engine = create_database_engine(get_settings().database_url)
    with create_session_factory(engine)() as session:
        result = evaluate_model_assistance(session)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    raise SystemExit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
