from __future__ import annotations

import re
import time
import uuid

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from opentelemetry import trace
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

REQUESTS = Counter(
    "insurance_api_requests_total",
    "HTTP requests handled by the API",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "insurance_api_request_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
)

CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enable_hsts: bool):  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
        if self._enable_hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


class CrossSiteRequestMiddleware(BaseHTTPMiddleware):
    """Reject cross-site browser mutations authenticated by the session cookie."""

    def __init__(self, app, *, allowed_origins: list[str], cookie_name: str):  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._allowed_origins = frozenset(allowed_origins)
        self._cookie_name = cookie_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in {"GET", "HEAD", "OPTIONS"} and request.cookies.get(
            self._cookie_name
        ):
            origin = request.headers.get("origin")
            fetch_site = request.headers.get("sec-fetch-site")
            if (origin and origin not in self._allowed_origins) or fetch_site == "cross-site":
                return JSONResponse(
                    {
                        "type": "https://errors.insurance-ops.example/cross_site_request",
                        "title": "Request rejected",
                        "status": 403,
                        "code": "cross_site_request",
                        "detail": "The browser request origin is not allowed.",
                    },
                    status_code=403,
                )
        return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("X-Correlation-ID", "")
        correlation_id = (
            supplied if CORRELATION_ID_PATTERN.fullmatch(supplied) else str(uuid.uuid4())
        )
        request.state.correlation_id = correlation_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        started = time.perf_counter()
        status = 500
        route = request.url.path
        tracer = trace.get_tracer("insurance_platform.http")
        with tracer.start_as_current_span(f"{request.method} {route}") as span:
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("insurance.correlation_id", correlation_id)
            try:
                response = await call_next(request)
                status = response.status_code
            finally:
                elapsed = time.perf_counter() - started
                matched_route = request.scope.get("route")
                route_template = getattr(matched_route, "path", route)
                REQUESTS.labels(request.method, route_template, str(status)).inc()
                LATENCY.labels(request.method, route_template).observe(elapsed)
                structlog.get_logger().info(
                    "http_request_completed",
                    method=request.method,
                    path=route,
                    status=status,
                    duration_ms=round(elapsed * 1000, 2),
                )
                structlog.contextvars.clear_contextvars()
        response.headers["X-Correlation-ID"] = correlation_id
        return response
