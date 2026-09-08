"""Public API schemas for BCOS Usage."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UsageStatus(StrEnum):
    """Public Usage status values frozen by OpenAPI V1."""

    PENDING = "PENDING"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Usage(BaseModel):
    """Public representation of actual resource usage."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    booking_id: UUID
    resource_id: UUID
    professional_id: UUID
    status: UsageStatus
    checked_in_at: datetime | None = None
    checked_out_at: datetime | None = None


class CheckInRequest(BaseModel):
    """Payload for starting actual Usage from a confirmed Booking."""

    model_config = ConfigDict(extra="forbid")

    booking_id: UUID
    checked_in_at: datetime | None = None


class CheckOutRequest(BaseModel):
    """Optional payload for completing actual Usage."""

    model_config = ConfigDict(extra="forbid")

    checked_out_at: datetime | None = None
