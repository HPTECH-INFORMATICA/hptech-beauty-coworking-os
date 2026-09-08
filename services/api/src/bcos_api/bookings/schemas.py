"""HTTP schemas for BCOS bookings."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BookingStatus(StrEnum):
    """Public booking status defined by the frozen OpenAPI contract."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class Booking(BaseModel):
    model_config = ConfigDict(title="Booking")

    id: UUID
    unit_id: UUID
    resource_id: UUID
    professional_id: UUID
    series_id: UUID | None = None
    status: BookingStatus
    starts_at: datetime
    ends_at: datetime
    buffer_before_minutes: int = Field(ge=0)
    buffer_after_minutes: int = Field(ge=0)
    pricing_snapshot: dict[str, Any]


class BookingCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        title="BookingCreate",
    )

    unit_id: UUID
    resource_id: UUID
    professional_id: UUID
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None


class BookingCancelRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        title="BookingCancelRequest",
    )

    reason: str | None = None


class BookingExtendRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        title="BookingExtendRequest",
    )

    ends_at: datetime


class BookingSeries(BaseModel):
    model_config = ConfigDict(title="BookingSeries")

    id: UUID
    professional_id: UUID
    rrule: str
    timezone: str
    starts_at: datetime
    ends_at: datetime | None = None
    cancelled_at: datetime | None = None


class BookingSeriesCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        title="BookingSeriesCreate",
    )

    unit_id: UUID
    resource_id: UUID
    professional_id: UUID
    starts_at: datetime
    duration_minutes: int = Field(ge=1)
    rrule: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    notes: str | None = None


class BookingSeriesResult(BaseModel):
    model_config = ConfigDict(title="BookingSeriesResult")

    series: BookingSeries
    bookings: list[Booking]
