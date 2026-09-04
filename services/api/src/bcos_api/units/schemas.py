"""HTTP schemas for BCOS units."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Unit(BaseModel):
    """Public representation of a BCOS unit."""

    model_config = ConfigDict(title="Unit")

    id: UUID
    name: str
    timezone: str
    active: bool
    created_at: datetime
    updated_at: datetime


class UnitCreate(BaseModel):
    """Payload for creating a BCOS unit."""

    model_config = ConfigDict(
        extra="forbid",
        title="UnitCreate",
    )

    name: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    active: bool = True


class UnitUpdate(BaseModel):
    """Partial payload for updating a BCOS unit."""

    model_config = ConfigDict(
        extra="forbid",
        title="UnitUpdate",
        json_schema_extra={
            "minProperties": 1,
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                },
                "timezone": {
                    "type": "string",
                    "minLength": 1,
                },
                "active": {"type": "boolean"},
            },
        },
    )

    name: str | None = None
    timezone: str | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        """Require one field and reject explicit null values."""

        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null.")

        return self

    def resolved_name(self, current: str) -> str:
        return self.name if self.name is not None else current

    def resolved_timezone(self, current: str) -> str:
        return self.timezone if self.timezone is not None else current

    def resolved_active(self, current: bool) -> bool:
        return self.active if self.active is not None else current
