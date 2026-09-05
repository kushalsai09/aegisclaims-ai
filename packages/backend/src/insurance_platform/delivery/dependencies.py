from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from insurance_platform.domain.entities import Actor
from insurance_platform.infrastructure.repositories import UserRepository, actor_from_user
from insurance_platform.ports.identity import IdentityError


def components(request: Request):  # type: ignore[no-untyped-def]
    return request.app.state.components


def database_session(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.components.session_factory()
    try:
        yield session
    finally:
        session.close()


SessionDependency = Annotated[Session, Depends(database_session)]


async def current_actor(
    request: Request,
    session: SessionDependency,
    authorization: Annotated[str | None, Header()] = None,
) -> Actor:
    settings = request.app.state.components.settings
    session_token = request.cookies.get(settings.session_cookie_name)
    if session_token:
        from insurance_platform.security.sessions import LocalAccountSessionService

        user = LocalAccountSessionService(
            session,
            ttl_seconds=settings.session_ttl_seconds,
            remember_ttl_seconds=settings.session_remember_ttl_seconds,
        ).verify(session_token)
    else:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise IdentityError("an authenticated session is required")
        token = authorization.split(" ", maxsplit=1)[1]
        verified = await request.app.state.components.identity_provider.verify(token)
        verified_user = UserRepository(session).get_active(verified.user_id, verified.tenant_id)
        if verified_user is None or verified_user.subject != verified.subject:
            raise IdentityError("identity does not map to an active user")
        user = verified_user
    return actor_from_user(user)


ActorDependency = Annotated[Actor, Depends(current_actor)]
