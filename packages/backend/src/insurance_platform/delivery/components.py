from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_platform.config import (
    AuthProvider,
    ModelProviderName,
    QueueProvider,
    RateLimitProvider,
    Settings,
    StorageProvider,
)
from insurance_platform.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from insurance_platform.infrastructure.object_storage import (
    FileSystemObjectStorage,
    InMemoryObjectStorage,
    S3ObjectStorage,
)
from insurance_platform.infrastructure.queue import InMemoryJobQueue, RedisJobQueue
from insurance_platform.infrastructure.rate_limit import InMemoryRateLimiter, RedisRateLimiter
from insurance_platform.model_assistance.bedrock import BedrockConverseProvider
from insurance_platform.model_assistance.provider import DeterministicBriefProvider
from insurance_platform.ports.identity import IdentityProvider
from insurance_platform.ports.model_provider import ModelProvider
from insurance_platform.ports.object_storage import ObjectStorage
from insurance_platform.ports.queue import JobQueue
from insurance_platform.ports.rate_limit import RateLimiter
from insurance_platform.security.local_identity import LocalIdentityProvider, OIDCIdentityProvider
from insurance_platform.security.oidc import OIDCAuthorizationCodeClient


@dataclass(slots=True)
class Components:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    identity_provider: IdentityProvider
    object_storage: ObjectStorage
    job_queue: JobQueue
    model_provider: ModelProvider
    rate_limiter: RateLimiter
    oidc_client: OIDCAuthorizationCodeClient | None


def build_components(settings: Settings) -> Components:
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    identity_provider: IdentityProvider
    if settings.auth_provider is AuthProvider.LOCAL:
        identity_provider = LocalIdentityProvider(settings.dev_auth_secret.get_secret_value())
        oidc_client = None
    else:
        identity_provider = OIDCIdentityProvider()
        assert settings.oidc_issuer is not None
        assert settings.oidc_audience is not None
        assert settings.oidc_client_id is not None
        assert settings.oidc_client_secret is not None
        oidc_client = OIDCAuthorizationCodeClient(
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret.get_secret_value(),
            scopes=settings.oidc_scopes,
        )

    object_storage: ObjectStorage
    if settings.object_storage_provider is StorageProvider.MEMORY:
        object_storage = InMemoryObjectStorage()
    elif settings.object_storage_provider is StorageProvider.FILESYSTEM:
        object_storage = FileSystemObjectStorage(settings.object_storage_path)
    else:
        object_storage = S3ObjectStorage(
            bucket=settings.object_storage_bucket,
            region=settings.object_storage_region,
            endpoint_url=settings.object_storage_endpoint,
            access_key=(
                settings.object_storage_access_key.get_secret_value()
                if settings.object_storage_access_key
                else None
            ),
            secret_key=(
                settings.object_storage_secret_key.get_secret_value()
                if settings.object_storage_secret_key
                else None
            ),
        )

    job_queue: JobQueue
    if settings.queue_provider is QueueProvider.MEMORY:
        job_queue = InMemoryJobQueue()
    elif settings.queue_provider is QueueProvider.REDIS:
        job_queue = RedisJobQueue(settings.redis_url, settings.queue_name)
    else:
        raise RuntimeError("SQS adapter is an approved boundary but is not implemented in Phase 2")

    model_provider: ModelProvider
    if settings.model_provider is ModelProviderName.DETERMINISTIC:
        model_provider = DeterministicBriefProvider()
    else:
        assert settings.bedrock_model_id is not None
        assert settings.bedrock_region is not None
        model_provider = BedrockConverseProvider(
            model_id=settings.bedrock_model_id,
            region=settings.bedrock_region,
        )

    rate_limiter: RateLimiter
    if settings.rate_limit_provider is RateLimitProvider.MEMORY:
        rate_limiter = InMemoryRateLimiter()
    else:
        rate_limiter = RedisRateLimiter(settings.redis_url)

    return Components(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        identity_provider=identity_provider,
        object_storage=object_storage,
        job_queue=job_queue,
        model_provider=model_provider,
        rate_limiter=rate_limiter,
        oidc_client=oidc_client,
    )
