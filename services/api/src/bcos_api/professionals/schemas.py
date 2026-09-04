"""HTTP schemas for BCOS professionals."""

from __future__ import annotations

from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from bcos_api.professionals.domain import ProfessionalStatus


class Professional(BaseModel):
    """Public representation of a BCOS professional."""

    model_config = ConfigDict(title="Professional")

    id: UUID
    external_user_id: str | None = None
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    status: ProfessionalStatus


class ProfessionalCreate(BaseModel):
    """Payload for creating a BCOS professional."""

    model_config = ConfigDict(
        extra="forbid",
        title="ProfessionalCreate",
    )

    external_user_id: str | None = None
    name: str = Field(min_length=1)
    email: EmailStr | None = None
    phone: str | None = None


class ProfessionalUpdate(BaseModel):
    """Partial payload for updating a BCOS professional."""

    model_config = ConfigDict(
        extra="forbid",
        title="ProfessionalUpdate",
        json_schema_extra={
            "minProperties": 1,
            "properties": {
                "external_user_id": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"},
                    ]
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                },
                "email": {
                    "anyOf": [
                        {
                            "type": "string",
                            "format": "email",
                        },
                        {"type": "null"},
                    ]
                },
                "phone": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"},
                    ]
                },
                "status": {
                    "$ref": "#/components/schemas/ProfessionalStatus"
                },
            },
        },
    )

    external_user_id: str | None = None
    name: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None
    phone: str | None = None
    status: ProfessionalStatus | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> ProfessionalUpdate:
        """Require one field and reject null for non-nullable fields."""

        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        for field_name in ("name", "status"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} must not be null.")

        return self
