from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class InvalidBooking(Exception):
    """Raised when booking domain data is invalid."""


class BookingStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


@dataclass(frozen=True)
class Booking:
    id: UUID
    tenant_id: UUID
    unit_id: UUID
    resource_id: UUID
    professional_id: UUID
    series_id: UUID | None
    status: BookingStatus
    starts_at: datetime
    ends_at: datetime
    buffer_before_minutes: int
    buffer_after_minutes: int
    pricing_snapshot: dict[str, Any]
    notes: str | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    completed_at: datetime | None


def validate_booking_period(starts_at: datetime, ends_at: datetime) -> None:
    """Validate the canonical booking business interval."""

    if starts_at.tzinfo is None or starts_at.utcoffset() is None:
        raise InvalidBooking("starts_at must be timezone-aware.")

    if ends_at.tzinfo is None or ends_at.utcoffset() is None:
        raise InvalidBooking("ends_at must be timezone-aware.")

    if ends_at <= starts_at:
        raise InvalidBooking("ends_at must be after starts_at.")


def validate_booking_buffers(
    buffer_before_minutes: int,
    buffer_after_minutes: int,
) -> None:
    """Validate captured resource buffers."""

    if buffer_before_minutes < 0:
        raise InvalidBooking("buffer_before_minutes must be non-negative.")

    if buffer_after_minutes < 0:
        raise InvalidBooking("buffer_after_minutes must be non-negative.")
