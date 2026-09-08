"""Application service for tenant-scoped BCOS pricing rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.pricing.domain import PricingRule, validate_pricing_rule_definition
from bcos_api.pricing.repository import (
    create_pricing_rule,
    list_pricing_rules,
)
from bcos_api.resource_categories.repository import get_resource_category
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission
from bcos_api.units.repository import get_unit


class PricingRuleUnitNotFound(Exception):
    """Raised when a referenced unit is outside the authorized tenant."""


class PricingRuleResourceCategoryNotFound(Exception):
    """Raised when a referenced resource category is unavailable."""


async def list_tenant_pricing_rules(
    session: AsyncSession,
    *,
    context: TenantContext,
) -> list[PricingRule]:
    """List pricing rules for the authorized tenant."""

    require_permission(context, Permission.TENANT_ADMIN)

    return await list_pricing_rules(
        session,
        tenant_id=context.tenant_id,
    )


async def create_tenant_pricing_rule(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID | None,
    resource_category_id: UUID | None,
    name: str,
    priority: int,
    currency: Literal["BRL"],
    rule_definition: dict[str, Any],
    valid_from: datetime | None,
    valid_until: datetime | None,
) -> PricingRule:
    """Validate and create one pricing rule for the authorized tenant."""

    require_permission(context, Permission.TENANT_ADMIN)

    normalized_name = name.strip()

    validate_pricing_rule_definition(
        name=normalized_name,
        priority=priority,
        currency=currency,
        rule_definition=rule_definition,
        valid_from=valid_from,
        valid_until=valid_until,
    )

    if unit_id is not None:
        unit = await get_unit(
            session,
            tenant_id=context.tenant_id,
            unit_id=unit_id,
        )

        if unit is None:
            raise PricingRuleUnitNotFound(
                "Pricing rule unit was not found in the authorized tenant."
            )

    if resource_category_id is not None:
        category = await get_resource_category(
            session,
            tenant_id=context.tenant_id,
            category_id=resource_category_id,
        )

        if category is None:
            raise PricingRuleResourceCategoryNotFound(
                "Pricing rule resource category was not found "
                "in the authorized tenant."
            )

    return await create_pricing_rule(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
        resource_category_id=resource_category_id,
        name=normalized_name,
        priority=priority,
        currency=currency,
        rule_definition=rule_definition,
        valid_from=valid_from,
        valid_until=valid_until,
    )
