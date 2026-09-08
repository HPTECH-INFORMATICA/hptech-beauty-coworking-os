"""API schemas for BCOS pricing rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from bcos_api.pricing.domain import PricingRuleStatus


class PricingRule(BaseModel):
    """Frozen OpenAPI representation of one pricing rule."""

    id: UUID
    unit_id: UUID | None = None
    resource_category_id: UUID | None = None
    name: str
    status: PricingRuleStatus
    priority: int = Field(ge=0)
    currency: Literal["BRL"]
    rule_definition: dict[str, Any]
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class PricingRuleCreate(BaseModel):
    """Frozen OpenAPI payload for creating one pricing rule."""

    model_config = ConfigDict(extra="forbid")

    unit_id: UUID | None = None
    resource_category_id: UUID | None = None
    name: str = Field(min_length=1)
    priority: int = Field(default=100, ge=0)
    currency: Literal["BRL"] = "BRL"
    rule_definition: dict[str, Any]
    valid_from: datetime | None = None
    valid_until: datetime | None = None
