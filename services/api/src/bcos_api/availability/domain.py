"""Availability domain models and invariants."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class InvalidAvailabilityInterval(Exception):
    """Raised when an availability interval is invalid."""


@dataclass(frozen=True)
class Availability:
    """Availability result for one tenant-scoped resource."""

    resource_id: UUID
    available: bool
    reason: str | None = None


def validate_availability_interval(
    starts_at: datetime,
    ends_at: datetime,
) -> tuple[datetime, datetime]:
    """Validate the canonical non-empty availability interval."""

    if starts_at.tzinfo is None or starts_at.utcoffset() is None:
        raise InvalidAvailabilityInterval(
            "starts_at must include timezone information."
        )

    if ends_at.tzinfo is None or ends_at.utcoffset() is None:
        raise InvalidAvailabilityInterval(
            "ends_at must include timezone information."
        )

    if starts_at >= ends_at:
        raise InvalidAvailabilityInterval(
            "starts_at must be earlier than ends_at."
        )

    return starts_at, ends_at
