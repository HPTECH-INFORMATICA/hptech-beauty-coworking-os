"""HPTECH-side platform authority domain types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class PlatformOperatorRole(StrEnum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"


class PlatformOperatorStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True)
class PlatformOperator:
    id: UUID
    external_user_id: str
    role: PlatformOperatorRole
    status: PlatformOperatorStatus

    @property
    def is_active(self) -> bool:
        return self.status is PlatformOperatorStatus.ACTIVE


@dataclass(frozen=True)
class PlatformContext:
    operator_id: UUID
    external_user_id: str
    role: PlatformOperatorRole


class PlatformAccessDenied(Exception):
    """Raised when an identity lacks active HPTECH platform authority."""
