"""Resource-category domain models."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


class InvalidResourceCategory(Exception):
    """Raised when resource-category domain data is invalid."""


@dataclass(frozen=True)
class ResourceCategory:
    """Tenant-owned category used to classify physical resources."""

    id: UUID
    tenant_id: UUID
    name: str
    active: bool


def validate_resource_category_name(name: str) -> str:
    """Normalize and validate a resource-category name."""

    normalized = name.strip()

    if not normalized:
        raise InvalidResourceCategory(
            "Resource category name must not be blank."
        )

    if len(normalized) > 120:
        raise InvalidResourceCategory(
            "Resource category name must not exceed 120 characters."
        )

    return normalized
