"""HTTP schemas for BCOS resources."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bcos_api.resources.domain import ResourceStatus


class ResourceResponse(BaseModel):
    model_config = ConfigDict(title="Resource")

    id: UUID
    unit_id: UUID
    category_id: UUID
    name: str
    operational_status: ResourceStatus
    buffer_before_minutes: int
    buffer_after_minutes: int
    active: bool


class ResourceCreateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        title="ResourceCreate",
    )

    unit_id: UUID
    category_id: UUID
    name: str = Field(min_length=1)
    buffer_before_minutes: int = Field(default=0, ge=0)
    buffer_after_minutes: int = Field(default=0, ge=0)
    active: bool = True


class ResourceUpdateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        title="ResourceUpdate",
        json_schema_extra={
            "minProperties": 1,
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                },
                "operational_status": {
                    "$ref": "#/components/schemas/ResourceStatus"
                },
                "buffer_before_minutes": {
                    "type": "integer",
                    "minimum": 0,
                },
                "buffer_after_minutes": {
                    "type": "integer",
                    "minimum": 0,
                },
                "active": {
                    "type": "boolean",
                },
            },
        },
    )

    name: str | None = Field(default=None, min_length=1)
    operational_status: ResourceStatus | None = None
    buffer_before_minutes: int | None = Field(default=None, ge=0)
    buffer_after_minutes: int | None = Field(default=None, ge=0)
    active: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> ResourceUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        for field_name in (
            "name",
            "operational_status",
            "buffer_before_minutes",
            "buffer_after_minutes",
            "active",
        ):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} must not be null.")

        return self

    def resolve_name(self, current: str) -> str:
        if "name" not in self.model_fields_set:
            return current
        if self.name is None:
            raise ValueError("name must not be null.")
        return self.name

    def resolve_operational_status(
        self,
        current: ResourceStatus,
    ) -> ResourceStatus:
        if "operational_status" not in self.model_fields_set:
            return current
        if self.operational_status is None:
            raise ValueError("operational_status must not be null.")
        return self.operational_status

    def resolve_buffer_before_minutes(self, current: int) -> int:
        if "buffer_before_minutes" not in self.model_fields_set:
            return current
        if self.buffer_before_minutes is None:
            raise ValueError("buffer_before_minutes must not be null.")
        return self.buffer_before_minutes

    def resolve_buffer_after_minutes(self, current: int) -> int:
        if "buffer_after_minutes" not in self.model_fields_set:
            return current
        if self.buffer_after_minutes is None:
            raise ValueError("buffer_after_minutes must not be null.")
        return self.buffer_after_minutes

    def resolve_active(self, current: bool) -> bool:
        if "active" not in self.model_fields_set:
            return current
        if self.active is None:
            raise ValueError("active must not be null.")
        return self.active
