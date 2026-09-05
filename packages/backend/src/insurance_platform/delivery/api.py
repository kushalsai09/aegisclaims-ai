from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import make_asgi_app

from insurance_platform.config import Settings, get_settings
from insurance_platform.delivery.components import Components, build_components
from insurance_platform.delivery.errors import register_error_handlers
from insurance_platform.delivery.middleware import (
    CrossSiteRequestMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from insurance_platform.delivery.routes import build_api_router, build_system_router
from insurance_platform.observability.logging import configure_logging
from insurance_platform.observability.telemetry import configure_telemetry


def create_app(settings: Settings | None = None, components: Components | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_components = components or build_components(resolved_settings)
    configure_logging(resolved_settings.log_level)
    configure_telemetry(resolved_settings, resolved_components.engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await app.state.components.object_storage.ensure_ready()
        yield

    app = FastAPI(
        title=resolved_settings.app_name,
        summary="Internal synthetic insurance evidence and governed model-assistance platform",
        description=(
            "Phase 7 APIs for authenticated synthetic claim operations, deterministic "
            "retrieval, governed model assistance, and durable human-authorized workflows. "
            "No autonomous claim "
            "decision, coverage authority, "
            "payment, fraud, or legal functionality is implemented."
        ),
        version=resolved_settings.app_version,
        docs_url="/docs" if resolved_settings.api_docs_enabled else None,
        redoc_url="/redoc" if resolved_settings.api_docs_enabled else None,
        openapi_url="/openapi.json" if resolved_settings.api_docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.components = resolved_components
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=resolved_settings.app_env.value in {"staging", "production"},
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=resolved_settings.trusted_hosts)
    app.add_middleware(
        CrossSiteRequestMiddleware,
        allowed_origins=resolved_settings.api_cors_origins,
        cookie_name=resolved_settings.session_cookie_name,
    )
    register_error_handlers(app)
    app.include_router(build_system_router())
    app.include_router(build_api_router(), prefix=resolved_settings.api_prefix)
    app.mount("/metrics", make_asgi_app())
    return app
