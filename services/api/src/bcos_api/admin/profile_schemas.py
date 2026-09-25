"""Tenant self-administration schemas."""

from pydantic import BaseModel, ConfigDict, Field


class TenantProfileResponse(BaseModel):
    legal_name: str
    trade_name: str
    tax_id: str | None = None
    email: str
    phone: str | None = None


class TenantProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal_name: str = Field(min_length=1, max_length=200)
    trade_name: str = Field(min_length=1, max_length=200)
    tax_id: str | None = Field(default=None, max_length=32)
    email: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
