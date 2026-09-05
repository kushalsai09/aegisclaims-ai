from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from insurance_platform.domain.enums import RoleName


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: UUID
    tenant_id: UUID
    subject: str
    display_name: str
    roles: frozenset[RoleName]

    @property
    def is_admin(self) -> bool:
        return RoleName.ADMIN in self.roles
