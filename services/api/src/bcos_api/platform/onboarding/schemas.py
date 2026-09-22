"""HTTP schemas for HPTECH contracting-company onboarding."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from bcos_api.platform.onboarding.domain import TenantCommercialStatus


class ContractingTenantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=100)
    legal_name: str = Field(min_length=1, max_length=200)
    trade_name: str = Field(min_length=1, max_length=200)
    tax_id: str | None = Field(default=None, max_length=32)
    email: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    owner_external_user_id: str = Field(min_length=1, max_length=255)


class ContractingTenant(BaseModel):
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
