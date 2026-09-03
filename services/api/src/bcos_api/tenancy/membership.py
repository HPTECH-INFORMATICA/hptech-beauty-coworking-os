"""Tenant membership domain types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class MembershipRole(StrEnum):
    """Roles supported by the BCOS tenant membership model."""

    OWNER = "OWNER"
    ADMIN = "ADMIN"
    RECEPTION = "RECEPTION"
    PROFESSIONAL = "PROFESSIONAL"


class MembershipStatus(StrEnum):
    """Statuses supported by the BCOS tenant membership model."""

    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True)
class TenantMembership:
    """Authenticated user's membership within one BCOS tenant."""

    id: UUID
    tenant_id: UUID
    external_user_id: str
    role: MembershipRole
    status: MembershipStatus

    @property
    def is_active(self) -> bool:
        """Return whether this membership authorizes tenant access."""

        return self.status is MembershipStatus.ACTIVE
