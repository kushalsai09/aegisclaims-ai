import pytest
from pydantic import ValidationError

from insurance_platform.config import Environment, Settings
from insurance_platform.synthetic.generator import repository_root


def test_local_auth_is_rejected_outside_local_or_test() -> None:
    with pytest.raises(ValidationError, match="local authentication"):
        Settings(
            _env_file=None,
            app_env=Environment.PRODUCTION,
            auth_provider="local",
            dev_auth_secret="a-production-looking-secret-that-is-long-enough",
            object_storage_provider="aws_s3",
            object_storage_access_key="not-a-real-key",
            object_storage_secret_key="not-a-real-secret",
            queue_provider="sqs",
        )


def test_cors_origin_string_is_parsed() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        api_cors_origins="http://one.invalid,http://two.invalid",
        dev_auth_secret="test-secret-that-is-definitely-longer-than-thirty-two",
    )
    assert settings.api_cors_origins == ["http://one.invalid", "http://two.invalid"]


def test_compose_environment_template_parses_through_settings() -> None:
    settings = Settings(_env_file=repository_root() / ".env.example")

    assert settings.api_cors_origins == ["http://localhost:5173"]
    assert settings.database_url.endswith("@postgres:5432/insurance_ops")
    assert settings.object_storage_endpoint == "http://minio:9000"
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.model_provider.value == "deterministic"
    assert settings.model_timeout_seconds == 8
    assert settings.model_max_retries == 1
