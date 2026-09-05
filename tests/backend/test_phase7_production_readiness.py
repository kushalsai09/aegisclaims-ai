from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import sign_in
from insurance_platform.config import Environment, Settings
from insurance_platform.delivery.api import create_app
from insurance_platform.delivery.components import build_components
from insurance_platform.infrastructure.database import Base
from insurance_platform.infrastructure.rate_limit import InMemoryRateLimiter
from insurance_platform.security.oidc import OIDCAuthorizationCodeClient
from insurance_platform.seed import TENANT_ID, seed


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "app_env": "production",
        "api_cors_origins": ["https://claims.example.invalid"],
        "trusted_hosts": ["claims.example.invalid"],
        "public_base_url": "https://claims.example.invalid",
        "api_docs_enabled": False,
        "database_url": "postgresql+psycopg://app:secret@db.internal/claims",
        "auth_provider": "oidc",
        "oidc_issuer": "https://identity.example.invalid",
        "oidc_audience": "claims-platform",
        "oidc_client_id": "claims-client",
        "oidc_client_secret": "a-production-secret-kept-outside-source-control",
        "oidc_redirect_uri": ("https://claims.example.invalid/api/v1/auth/oidc/callback"),
        "oidc_tenant_id": TENANT_ID,
        "object_storage_provider": "aws_s3",
        "queue_provider": "redis",
        "redis_url": "rediss://cache.internal:6379/0",
        "rate_limit_provider": "redis",
        "model_provider": "bedrock",
        "bedrock_model_id": "provider.model-v1",
        "bedrock_region": "us-east-1",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_production_configuration_accepts_only_externalized_secure_adapters() -> None:
    settings = production_settings()
    assert settings.app_env is Environment.PRODUCTION
    assert settings.object_storage_access_key is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"api_cors_origins": ["*"]}, "CORS"),
        ({"trusted_hosts": ["*"]}, "TRUSTED_HOSTS"),
        ({"public_base_url": "http://claims.example.invalid"}, "HTTPS"),
        ({"api_docs_enabled": True}, "documentation"),
        ({"auth_provider": "local"}, "local authentication"),
        ({"database_url": "sqlite:///claims.db"}, "PostgreSQL"),
        ({"rate_limit_provider": "memory"}, "Redis-backed"),
        ({"redis_url": "redis://cache.internal:6379/0"}, "TLS"),
        ({"oidc_issuer": "http://identity.example.invalid"}, "HTTPS"),
        ({"object_storage_access_key": "static-key"}, "workload identity"),
    ],
)
def test_insecure_production_configuration_fails_closed(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        production_settings(**overrides)


def test_in_memory_rate_limiter_enforces_fixed_window(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = InMemoryRateLimiter()
    monkeypatch.setattr("insurance_platform.infrastructure.rate_limit.time.time", lambda: 100.0)
    first = limiter.check(scope="model", subject="user", limit=2, window_seconds=60)
    second = limiter.check(scope="model", subject="user", limit=2, window_seconds=60)
    rejected = limiter.check(scope="model", subject="user", limit=2, window_seconds=60)
    assert (first.allowed, second.allowed, rejected.allowed) == (True, True, False)
    assert rejected.remaining == 0
    assert rejected.retry_after_seconds == 20

    monkeypatch.setattr("insurance_platform.infrastructure.rate_limit.time.time", lambda: 121.0)
    assert limiter.check(scope="model", subject="user", limit=2, window_seconds=60).allowed


def test_login_rate_limit_returns_problem_detail_and_retry_after(client: TestClient) -> None:
    client.app.state.components.settings.auth_rate_limit = 1
    payload = {
        "email": "avery.morgan@example.invalid",
        "password": "wrong-password",
        "remember": False,
    }
    assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 429
    assert response.json()["code"] == "rate_limit_exceeded"
    assert int(response.headers["Retry-After"]) > 0


def test_security_headers_host_validation_and_correlation_id_sanitization(
    client: TestClient,
) -> None:
    response = client.get("/health/live", headers={"X-Correlation-ID": "invalid header value"})
    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"].startswith("default-src 'none'")
    assert response.headers["X-Correlation-ID"] != "invalid header value"
    assert client.get("/health/live", headers={"Host": "attacker.example"}).status_code == 400


def test_claim_list_pagination_is_bounded_without_changing_response_shape(
    client: TestClient,
) -> None:
    headers = sign_in(client, "admin")
    first_page = client.get("/api/v1/claims?limit=2&offset=0", headers=headers)
    second_page = client.get("/api/v1/claims?limit=2&offset=2", headers=headers)
    assert first_page.status_code == second_page.status_code == 200
    assert len(first_page.json()) == len(second_page.json()) == 2
    assert {item["id"] for item in first_page.json()}.isdisjoint(
        item["id"] for item in second_page.json()
    )
    assert client.get("/api/v1/claims?limit=201", headers=headers).status_code == 422


def test_oidc_authorization_code_pkce_flow_maps_preprovisioned_subject_and_is_one_time(
    tmp_path: Path,
) -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'oidc.db'}",
        auth_provider="oidc",
        oidc_issuer="https://identity.example.invalid",
        oidc_audience="claims-platform",
        oidc_client_id="claims-client",
        oidc_client_secret="test-oidc-client-secret-with-thirty-two-characters",
        oidc_redirect_uri="http://testserver/api/v1/auth/oidc/callback",
        oidc_tenant_id=TENANT_ID,
        object_storage_provider="memory",
        queue_provider="memory",
        rate_limit_provider="memory",
        otel_enabled=False,
    )
    components = build_components(settings)
    Base.metadata.create_all(components.engine)
    seed(components.session_factory)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk.update({"kid": "test-key", "use": "sig", "alg": "RS256"})
    expected_nonce = ""

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": "https://identity.example.invalid",
                    "authorization_endpoint": "https://identity.example.invalid/authorize",
                    "token_endpoint": "https://identity.example.invalid/token",
                    "jwks_uri": "https://identity.example.invalid/keys",
                },
            )
        if request.url.path == "/token":
            claims = {
                "iss": "https://identity.example.invalid",
                "aud": "claims-platform",
                "sub": "synthetic-claims_adjuster",
                "email": "avery.morgan@example.invalid",
                "name": "Avery Morgan",
                "nonce": expected_nonce,
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            }
            token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})
            return httpx.Response(200, json={"id_token": token})
        if request.url.path == "/keys":
            return httpx.Response(200, json={"keys": [jwk]})
        raise AssertionError(f"unexpected OIDC request: {request.method} {request.url}")

    components.oidc_client = OIDCAuthorizationCodeClient(
        issuer=settings.oidc_issuer or "",
        audience=settings.oidc_audience or "",
        client_id=settings.oidc_client_id or "",
        client_secret=(settings.oidc_client_secret or "").get_secret_value(),  # type: ignore[union-attr]
        scopes=settings.oidc_scopes,
        transport=httpx.MockTransport(provider),
    )
    app = create_app(settings=settings, components=components)
    with TestClient(app) as oidc_client:
        start = oidc_client.get("/api/v1/auth/oidc/start", follow_redirects=False)
        assert start.status_code == 302
        query = parse_qs(urlparse(start.headers["location"]).query)
        expected_nonce = query["nonce"][0]
        assert query["code_challenge_method"] == ["S256"]
        assert query["state"][0]

        callback_path = f"/api/v1/auth/oidc/callback?code=test-code&state={query['state'][0]}"
        callback = oidc_client.get(callback_path, follow_redirects=False)
        assert callback.status_code == 303
        assert callback.headers["location"] == settings.public_base_url
        assert "HttpOnly" in callback.headers["set-cookie"]
        assert oidc_client.get("/api/v1/auth/session").json()["roles"] == ["claims_adjuster"]

        replay = oidc_client.get(callback_path, follow_redirects=False)
        assert replay.status_code == 401
        assert replay.json()["code"] == "identity_invalid"

    components.engine.dispose()
