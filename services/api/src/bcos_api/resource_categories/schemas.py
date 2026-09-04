"""HTTP schemas for BCOS resource categories."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResourceCategoryResponse(BaseModel):
    """Public representation of a BCOS resource category."""

    id: str
    name: str
    active: bool


class ResourceCategoryCreateRequest(BaseModel):
    """Payload for creating a BCOS resource category."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    active: bool = True
