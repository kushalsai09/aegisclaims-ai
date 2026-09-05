from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    user_id: UUID
    tenant_id: UUID
    subject: str


class IdentityError(Exception):
    """Raised when an identity token cannot be verified."""


class IdentityProvider(Protocol):
    async def verify(self, token: str) -> VerifiedIdentity: ...
