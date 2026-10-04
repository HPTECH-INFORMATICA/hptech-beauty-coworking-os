"""Tenant membership domain types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class MembershipRole(StrEnum):
    """Internal membership categories.

    OWNER is the protected tenant authority. Non-owner values remain as
    compatibility categories while business access is governed by the
    tenant-managed access_role_id.
    """

    OWNER = "OWNER"
    ADMIN = "ADMIN"
    RECEPTION = "RECEPTION"
    PROFESSIONAL = "PROFESSIONAL"


class MembershipStatus(StrEnum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True)
class TenantMembership:
    id: UUID
    tenant_id: UUID
    external_user_id: str
    role: MembershipRole
    status: MembershipStatus
    display_name: str | None = None
    email: str | None = None
    access_role_id: UUID | None = None

    @property
    def is_active(self) -> bool:
        return self.status is MembershipStatus.ACTIVE
