"""HTTP schemas for BCOS reception hours."""

from __future__ import annotations

from datetime import time

from pydantic import BaseModel, ConfigDict, Field


class ReceptionHoursResponse(BaseModel):
    """Public representation of one reception-hours day."""

    day_of_week: int = Field(ge=0, le=6)
    opens_at: time | None = None
    closes_at: time | None = None
    is_closed: bool


class ReceptionHoursInput(BaseModel):
    """Payload item for replacing reception hours."""

    model_config = ConfigDict(extra="forbid")

    day_of_week: int = Field(ge=0, le=6)
    opens_at: time | None = None
    closes_at: time | None = None
    is_closed: bool
