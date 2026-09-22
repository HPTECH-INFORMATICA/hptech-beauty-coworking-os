"""Contracting-company onboarding domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class TenantCommercialStatus(StrEnum):
    PENDING_ACTIVATION = "PENDING_ACTIVATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True)
class ContractingTenant:
    id: UUID
    name: str
    slug: str
    status: TenantCommercialStatus
    legal_name: str
    trade_name: str
    tax_id: str | None
    email: str
    phone: str | None
    owner_external_user_id: str
    created_at: datetime


class InvalidTenantOnboarding(Exception):
    pass


def required_text(value: str, *, field: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise InvalidTenantOnboarding(f"{field} must not be blank.")
    if len(normalized) > maximum:
        raise InvalidTenantOnboarding(f"{field} must not exceed {maximum} characters.")
    return normalized
