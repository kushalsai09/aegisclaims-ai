from __future__ import annotations

import json
from dataclasses import asdict

from insurance_platform.config import get_settings
from insurance_platform.evaluation.workflows import evaluate_workflows
from insurance_platform.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)


def main() -> None:
    engine = create_database_engine(get_settings().database_url)
    with create_session_factory(engine)() as session:
        result = evaluate_workflows(session)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    raise SystemExit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
