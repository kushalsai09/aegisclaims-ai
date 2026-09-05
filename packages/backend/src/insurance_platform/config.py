from __future__ import annotations

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AuthProvider(StrEnum):
    LOCAL = "local"
    OIDC = "oidc"


class StorageProvider(StrEnum):
    MEMORY = "memory"
    FILESYSTEM = "filesystem"
    S3_COMPATIBLE = "s3_compatible"
    AWS_S3 = "aws_s3"


class QueueProvider(StrEnum):
    MEMORY = "memory"
    REDIS = "redis"
    SQS = "sqs"


class ModelProviderName(StrEnum):
    DETERMINISTIC = "deterministic"
    BEDROCK = "bedrock"


class RateLimitProvider(StrEnum):
    MEMORY = "memory"
    REDIS = "redis"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Enterprise AI Insurance Operations Platform"
    app_env: Environment = Environment.LOCAL
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    api_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    public_base_url: str = "http://localhost:5173"
    api_docs_enabled: bool = True

    database_url: str = "sqlite+pysqlite:///./.local/insurance_ops.db"

    auth_provider: AuthProvider = AuthProvider.LOCAL
    dev_auth_secret: SecretStr = SecretStr("local-development-secret-change-before-shared-use")
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: SecretStr | None = None
    oidc_redirect_uri: str | None = None
    oidc_tenant_id: UUID | None = None
    oidc_scopes: str = "openid profile email"
    session_cookie_name: str = "harborview_session"
    session_ttl_seconds: int = Field(default=28_800, ge=300, le=86_400)
    session_remember_ttl_seconds: int = Field(default=2_592_000, ge=3_600, le=2_592_000)

    object_storage_provider: StorageProvider = StorageProvider.MEMORY
    object_storage_endpoint: str | None = None
    object_storage_region: str = "us-east-1"
    object_storage_bucket: str = "insurance-documents"
    object_storage_path: str = ".local/object-storage"
    object_storage_access_key: SecretStr | None = None
    object_storage_secret_key: SecretStr | None = None

    queue_provider: QueueProvider = QueueProvider.MEMORY
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "insurance-operations"

    rate_limit_provider: RateLimitProvider = RateLimitProvider.MEMORY
    auth_rate_limit: int = Field(default=10, ge=1, le=1_000)
    retrieval_rate_limit: int = Field(default=60, ge=1, le=10_000)
    model_rate_limit: int = Field(default=10, ge=1, le=1_000)
    upload_rate_limit: int = Field(default=20, ge=1, le=1_000)
    rate_limit_window_seconds: int = Field(default=60, ge=10, le=3_600)

    model_provider: ModelProviderName = ModelProviderName.DETERMINISTIC
    model_timeout_seconds: float = Field(default=8.0, ge=0.1, le=60)
    model_max_retries: int = Field(default=1, ge=0, le=2)
    model_max_input_characters: int = Field(default=30_000, ge=1_000, le=120_000)
    model_max_output_tokens: int = Field(default=1_200, ge=128, le=4_096)
    bedrock_model_id: str | None = None
    bedrock_region: str | None = None

    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "insurance-api"

    @field_validator("api_cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_environment_safety(self) -> Settings:
        safe_local = self.app_env in {Environment.LOCAL, Environment.TEST}
        if not self.api_cors_origins or "*" in self.api_cors_origins:
            raise ValueError("credentialed CORS requires an explicit non-wildcard origin allowlist")
        if not self.trusted_hosts or "*" in self.trusted_hosts:
            raise ValueError("TRUSTED_HOSTS must contain an explicit non-wildcard allowlist")
        if self.auth_provider is AuthProvider.LOCAL and not safe_local:
            raise ValueError("local authentication is allowed only in local or test environments")
        if (
            self.object_storage_provider
            in {
                StorageProvider.MEMORY,
                StorageProvider.FILESYSTEM,
            }
            and not safe_local
        ):
            raise ValueError("local object storage is allowed only in local or test environments")
        if self.queue_provider is QueueProvider.MEMORY and not safe_local:
            raise ValueError("memory queue is allowed only in local or test environments")
        if self.model_provider is ModelProviderName.DETERMINISTIC and not safe_local:
            raise ValueError("deterministic model provider is allowed only locally or in tests")
        if self.model_provider is ModelProviderName.BEDROCK and (
            not self.bedrock_model_id or not self.bedrock_region
        ):
            raise ValueError("BEDROCK_MODEL_ID and BEDROCK_REGION are required for Bedrock")
        if self.auth_provider is AuthProvider.LOCAL:
            if len(self.dev_auth_secret.get_secret_value()) < 32:
                raise ValueError("DEV_AUTH_SECRET must contain at least 32 characters")
        elif not all(
            (
                self.oidc_issuer,
                self.oidc_audience,
                self.oidc_client_id,
                self.oidc_client_secret,
                self.oidc_redirect_uri,
                self.oidc_tenant_id,
            )
        ):
            raise ValueError(
                "OIDC issuer, audience, client, redirect URI, secret, "
                "and tenant mapping are required"
            )
        elif not safe_local and (
            not (self.oidc_issuer or "").startswith("https://")
            or not (self.oidc_redirect_uri or "").startswith("https://")
        ):
            raise ValueError("OIDC issuer and redirect URI must use HTTPS outside local/test")
        if self.object_storage_provider is StorageProvider.S3_COMPATIBLE:
            if not self.object_storage_endpoint:
                raise ValueError("OBJECT_STORAGE_ENDPOINT is required for S3-compatible storage")
            if not self.object_storage_access_key or not self.object_storage_secret_key:
                raise ValueError("object storage credentials are required")
        if (
            self.object_storage_provider is StorageProvider.AWS_S3
            and not safe_local
            and (self.object_storage_access_key or self.object_storage_secret_key)
        ):
            raise ValueError("production AWS S3 must use workload identity, not static access keys")
        if not safe_local:
            if not self.public_base_url.startswith("https://"):
                raise ValueError("PUBLIC_BASE_URL must use HTTPS outside local/test")
            if not self.database_url.startswith("postgresql+"):
                raise ValueError("production-like environments require PostgreSQL")
            if self.queue_provider is not QueueProvider.REDIS:
                raise ValueError("production-like environments require the Redis queue adapter")
            if not self.redis_url.startswith("rediss://"):
                raise ValueError("production-like Redis connections must use TLS (rediss://)")
            if self.rate_limit_provider is not RateLimitProvider.REDIS:
                raise ValueError("production-like environments require Redis-backed rate limiting")
            if self.api_docs_enabled:
                raise ValueError(
                    "interactive API documentation must be disabled outside local/test"
                )
        return self


def get_settings() -> Settings:
    return Settings()
