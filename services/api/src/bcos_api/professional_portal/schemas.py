"""Commercial self-service schemas for the BCOS Professional Portal."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfessionalCommercialOption(BaseModel):
    model_config = ConfigDict(title="ProfessionalCommercialOption")

    resource_id: UUID
    resource_name: str
    resource_category_id: UUID
    available: bool
    unavailable_reason: str | None = None
    pricing_snapshot: dict[str, Any] | None = None
    price_amount: str | None = None
    price_currency: str | None = None
    price_modality: str | None = None


class ProfessionalCommercialAvailability(BaseModel):
    model_config = ConfigDict(title="ProfessionalCommercialAvailability")

    unit_id: UUID
    starts_at: datetime
    ends_at: datetime
    resources: list[ProfessionalCommercialOption]


class ProfessionalBookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", title="ProfessionalBookingCreate")

    unit_id: UUID
    resource_id: UUID
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None
