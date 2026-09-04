"""Unit domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class InvalidUnit(Exception):
    """Raised when unit domain data is invalid."""


@dataclass(frozen=True)
class Unit:
    """Physical BCOS operating unit."""

    id: UUID
    tenant_id: UUID
    name: str
    timezone: str
    active: bool
    created_at: datetime
    updated_at: datetime


def validate_unit_name(name: str) -> str:
    """Normalize and validate a unit name."""

    normalized = name.strip()

    if not normalized:
        raise InvalidUnit("Unit name must not be blank.")

    if len(normalized) > 160:
        raise InvalidUnit(
            "Unit name must not exceed 160 characters."
        )

    return normalized


def validate_unit_timezone(timezone: str) -> str:
    """Normalize and validate an IANA timezone."""

    normalized = timezone.strip()

    if not normalized:
        raise InvalidUnit("Unit timezone must not be blank.")

    if len(normalized) > 100:
        raise InvalidUnit(
            "Unit timezone must not exceed 100 characters."
        )

    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise InvalidUnit(
            "Unit timezone must be a valid IANA timezone."
        ) from exc

    return normalized
