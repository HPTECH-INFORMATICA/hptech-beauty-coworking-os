"""Professional domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class InvalidProfessional(Exception):
    """Raised when professional domain data is invalid."""


class ProfessionalStatus(StrEnum):
    """Professional states defined by the BCOS database baseline."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True)
class Professional:
    """Professional operating inside one BCOS tenant."""

    id: UUID
    tenant_id: UUID
    external_user_id: str | None
    name: str
    email: str | None
    phone: str | None
    status: ProfessionalStatus


def validate_professional_name(name: str) -> str:
    """Normalize and validate a professional name."""

    normalized = name.strip()

    if not normalized:
        raise InvalidProfessional(
            "Professional name must not be blank."
        )

    if len(normalized) > 160:
        raise InvalidProfessional(
            "Professional name must not exceed 160 characters."
        )

    return normalized


def normalize_optional_text(
    value: str | None,
    *,
    field_name: str,
    max_length: int,
) -> str | None:
    """Normalize an optional textual professional field."""

    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        return None

    if len(normalized) > max_length:
        raise InvalidProfessional(
            f"{field_name} must not exceed {max_length} characters."
        )

    return normalized
