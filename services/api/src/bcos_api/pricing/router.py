"""HTTP routes for BCOS pricing rules."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.pricing.domain import (
    InvalidPricingRule,
)
from bcos_api.pricing.domain import (
    PricingRule as DomainPricingRule,
)
from bcos_api.pricing.schemas import (
    PricingRule as PricingRuleResponse,
)
from bcos_api.pricing.schemas import (
    PricingRuleCreate as PricingRuleCreateRequest,
)
from bcos_api.pricing.service import (
    PricingRuleResourceCategoryNotFound,
    PricingRuleUnitNotFound,
    create_tenant_pricing_rule,
    list_tenant_pricing_rules,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context

router = APIRouter(
    prefix="/api/v1/pricing-rules",
    tags=["Pricing"],
)

SessionDependency = Annotated[
    AsyncSession,
    Depends(get_async_session),
]
TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]


def _to_response(rule: DomainPricingRule) -> PricingRuleResponse:
    """Convert the trusted pricing domain model to its API representation."""

    return PricingRuleResponse(
        id=rule.id,
        unit_id=rule.unit_id,
        resource_category_id=rule.resource_category_id,
        name=rule.name,
        status=rule.status,
        priority=rule.priority,
        currency=rule.currency,
        rule_definition=rule.rule_definition,
        valid_from=rule.valid_from,
        valid_until=rule.valid_until,
    )


@router.get(
    "",
    response_model=list[PricingRuleResponse],
    operation_id="listPricingRules",
)
async def list_pricing_rules(
    session: SessionDependency,
    context: TenantContextDependency,
) -> list[PricingRuleResponse]:
    """List pricing rules inside the authorized tenant."""

    rules = await list_tenant_pricing_rules(
        session,
        context=context,
    )

    return [_to_response(rule) for rule in rules]


@router.post(
    "",
    response_model=PricingRuleResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPricingRule",
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_pricing_rule(
    payload: PricingRuleCreateRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> PricingRuleResponse:
    """Create one pricing rule inside the authorized tenant."""

    try:
        rule = await create_tenant_pricing_rule(
            session,
            context=context,
            unit_id=payload.unit_id,
            resource_category_id=payload.resource_category_id,
            name=payload.name,
            priority=payload.priority,
            currency=payload.currency,
            rule_definition=payload.rule_definition,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
        )
        await session.commit()
    except (
        InvalidPricingRule,
        PricingRuleUnitNotFound,
        PricingRuleResourceCategoryNotFound,
    ) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Pricing rule violates the pricing contract.",
        ) from exc
    except Exception:
        await session.rollback()
        raise

    return _to_response(rule)
