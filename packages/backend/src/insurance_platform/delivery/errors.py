from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from insurance_platform.ports.identity import IdentityError
from insurance_platform.security.authorization import AuthorizationError
from insurance_platform.security.sessions import DisabledAccountError


class ResourceNotFoundError(Exception):
    pass


class DocumentValidationError(Exception):
    def __init__(self, detail: str, code: str = "document_invalid") -> None:
        super().__init__(detail)
        self.code = code


class ResourceConflictError(Exception):
    pass


class RateLimitExceededError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Too many requests. Try again later.")
        self.retry_after_seconds = retry_after_seconds


class DependencyUnavailableError(Exception):
    pass


def problem(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "type": f"https://errors.insurance-ops.example/{code}",
        "title": title,
        "status": status,
        "code": code,
        "detail": detail,
        "correlation_id": getattr(request.state, "correlation_id", None),
    }
    if errors:
        payload["errors"] = errors
    return JSONResponse(payload, status_code=status, media_type="application/problem+json")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DependencyUnavailableError)
    async def dependency_unavailable(
        request: Request, exc: DependencyUnavailableError
    ) -> JSONResponse:
        return problem(
            request,
            status=503,
            code="dependency_unavailable",
            title="Service temporarily unavailable",
            detail=str(exc),
        )

    @app.exception_handler(RateLimitExceededError)
    async def rate_limited(request: Request, exc: RateLimitExceededError) -> JSONResponse:
        response = problem(
            request,
            status=429,
            code="rate_limit_exceeded",
            title="Request rate limit exceeded",
            detail=str(exc),
        )
        response.headers["Retry-After"] = str(exc.retry_after_seconds)
        return response

    @app.exception_handler(DisabledAccountError)
    async def disabled_account(request: Request, exc: DisabledAccountError) -> JSONResponse:
        return problem(
            request,
            status=403,
            code="account_disabled",
            title="Account unavailable",
            detail=str(exc),
        )

    @app.exception_handler(IdentityError)
    async def identity_error(request: Request, exc: IdentityError) -> JSONResponse:
        return problem(
            request,
            status=401,
            code="identity_invalid",
            title="Authentication required",
            detail=str(exc),
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error(request: Request, exc: AuthorizationError) -> JSONResponse:
        return problem(
            request,
            status=403,
            code="action_forbidden",
            title="Action is not permitted",
            detail=f"The current role cannot perform '{exc.action.value}'.",
        )

    @app.exception_handler(ResourceNotFoundError)
    async def not_found(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
        return problem(
            request,
            status=404,
            code="resource_not_found",
            title="Resource not found",
            detail=str(exc),
        )

    @app.exception_handler(ResourceConflictError)
    async def conflict(request: Request, exc: ResourceConflictError) -> JSONResponse:
        return problem(
            request,
            status=409,
            code="resource_conflict",
            title="Resource conflict",
            detail=str(exc),
        )

    @app.exception_handler(DocumentValidationError)
    async def document_invalid(request: Request, exc: DocumentValidationError) -> JSONResponse:
        return problem(
            request,
            status=422,
            code=exc.code,
            title="Document rejected",
            detail=str(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem(
            request,
            status=422,
            code="request_invalid",
            title="Request validation failed",
            detail="One or more request fields are invalid.",
            errors=[
                {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
                for error in exc.errors()
            ],
        )
