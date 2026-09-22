"""HPTECH platform administration HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.platform.dependencies import get_platform_context
from bcos_api.platform.domain import PlatformContext
from bcos_api.platform.onboarding.domain import InvalidTenantOnboarding
from bcos_api.platform.onboarding.schemas import (
    ContractingTenant as ContractingTenantResponse,
    ContractingTenantCreate,
)
from bcos_api.platform.onboarding.service import onboard_contracting_tenant

router = APIRouter(prefix="/api/v1/platform", tags=["Platform Administration"])

SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
PlatformContextDependency = Annotated[PlatformContext, Depends(get_platform_context)]


@router.post(
    "/tenants",
    response_model=ContractingTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant_endpoint(
    payload: ContractingTenantCreate,
    session: SessionDependency,
    context: PlatformContextDependency,
) -> ContractingTenantResponse:
    try:
        tenant = await onboard_contracting_tenant(
            session,
            context=context,
            **payload.model_dump(),
        )
        await session.commit()
    except InvalidTenantOnboarding as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant slug or identity binding already exists.",
        ) from exc

    return ContractingTenantResponse.model_validate(tenant, from_attributes=True)
