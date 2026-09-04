"""Resource domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class InvalidResource(Exception):
    """Raised when resource domain data is invalid."""


class ResourceStatus(StrEnum):
    """Operational states defined by the BCOS database baseline."""

    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    CLEANING = "CLEANING"
    MAINTENANCE = "MAINTENANCE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class Resource:
    """Physical resource available for coworking operations."""

    id: UUID
    tenant_id: UUID
    unit_id: UUID
    category_id: UUID
    name: str
    operational_status: ResourceStatus
    buffer_before_minutes: int
    buffer_after_minutes: int
    active: bool


def validate_resource_name(name: str) -> str:
    """Normalize and validate a resource name."""

    normalized = name.strip()

    if not normalized:
        raise InvalidResource("Resource name must not be blank.")

    if len(normalized) > 160:
        raise InvalidResource(
            "Resource name must not exceed 160 characters."
        )

    return normalized


def validate_resource_buffer(
    minutes: int,
    *,
    field_name: str,
) -> int:
    """Validate a non-negative resource buffer."""

    if minutes < 0:
        raise InvalidResource(
            f"{field_name} must not be negative."
        )

    return minutes
