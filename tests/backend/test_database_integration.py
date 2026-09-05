from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from insurance_platform.infrastructure.models import ClaimModel, UserModel


def test_seeded_domain_relations_are_queryable(client: TestClient) -> None:
    components = client.app.state.components
    assert "claims" in inspect(components.engine).get_table_names()
    with components.session_factory() as session:
        claim = session.scalar(select(ClaimModel))
        users = list(session.scalars(select(UserModel)))
        assert claim is not None
        assert claim.policy.product_code == "HO-SYN-01"
        assert len(users) == 4
