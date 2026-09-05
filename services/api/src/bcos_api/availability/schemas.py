"""HTTP schemas for BCOS availability."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AvailabilityItem(BaseModel):
    """Public availability item defined by the frozen OpenAPI contract."""

    model_config = ConfigDict(title="AvailabilityItem")

    resource_id: UUID
    available: bool
    reason: str | None = None


class AvailabilityResponse(BaseModel):
    """Public availability response defined by the frozen OpenAPI contract."""

    model_config = ConfigDict(title="AvailabilityResponse")

    starts_at: datetime
    ends_at: datetime
    resources: list[AvailabilityItem]
