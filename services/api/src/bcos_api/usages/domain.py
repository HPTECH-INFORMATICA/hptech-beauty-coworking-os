"""Usage domain model and invariants for BCOS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class InvalidUsage(ValueError):
    """Raised when Usage data violates a domain invariant."""


class UsageStatus(StrEnum):
    """Frozen BCOS Usage lifecycle states."""

    PENDING = "PENDING"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Usage:
    """Actual resource usage associated with one confirmed Booking."""

    id: UUID
    tenant_id: UUID
    booking_id: UUID
    resource_id: UUID
    professional_id: UUID
    status: UsageStatus
    checked_in_at: datetime | None
    checked_out_at: datetime | None


def validate_check_in_timestamp(checked_in_at: datetime) -> None:
    """Require an offset-aware timestamp for an actual check-in."""

    if checked_in_at.tzinfo is None or checked_in_at.utcoffset() is None:
        raise InvalidUsage("checked_in_at must be timezone-aware.")


def validate_check_out_timestamp(
    *,
    checked_in_at: datetime,
    checked_out_at: datetime,
) -> None:
    """Validate chronological and timezone invariants for check-out."""

    validate_check_in_timestamp(checked_in_at)

    if checked_out_at.tzinfo is None or checked_out_at.utcoffset() is None:
        raise InvalidUsage("checked_out_at must be timezone-aware.")

    if checked_out_at < checked_in_at:
        raise InvalidUsage(
            "checked_out_at cannot be earlier than checked_in_at."
        )
