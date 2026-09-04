"""HTTP schemas for BCOS resource categories."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResourceCategory(BaseModel):
    """Public representation of a BCOS resource category."""

    id: UUID
    name: str
    active: bool


class ResourceCategoryCreate(BaseModel):
    """Payload for creating a BCOS resource category."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    active: bool = True
