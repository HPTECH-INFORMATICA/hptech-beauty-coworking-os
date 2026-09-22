"""HPTECH platform administration HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.platform.dependencies import get_platform_context
from bcos_api.platform.domain import PlatformContext
from bcos_api.platform.onboarding.domain import InvalidTenantOnboarding
from bcos_api.platform.onboarding.schemas import (
    ContractingTenant as ContractingTenantResponse,
)
from bcos_api.platform.onboarding.schemas import (
    ContractingTenantCreate,
    ContractingTenantStatusUpdate,
)
from bcos_api.platform.onboarding.repository import (
    get_contracting_tenant,
    list_contracting_tenants,
    update_contracting_tenant_status,
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


@router.get("/tenants", response_model=list[ContractingTenantResponse])
async def list_tenants_endpoint(
    session: SessionDependency,
    context: PlatformContextDependency,
) -> list[ContractingTenantResponse]:
    del context
    tenants = await list_contracting_tenants(session)
    return [ContractingTenantResponse.model_validate(item, from_attributes=True) for item in tenants]


@router.get("/tenants/{tenant_id}", response_model=ContractingTenantResponse)
async def get_tenant_endpoint(
    tenant_id: UUID,
    session: SessionDependency,
    context: PlatformContextDependency,
) -> ContractingTenantResponse:
    del context
    tenant = await get_contracting_tenant(session, tenant_id=tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Contracting tenant not found.")
    return ContractingTenantResponse.model_validate(tenant, from_attributes=True)


@router.patch("/tenants/{tenant_id}/status", response_model=ContractingTenantResponse)
async def update_tenant_status_endpoint(
    tenant_id: UUID,
    payload: ContractingTenantStatusUpdate,
    session: SessionDependency,
    context: PlatformContextDependency,
) -> ContractingTenantResponse:
    del context
    tenant = await update_contracting_tenant_status(
        session,
        tenant_id=tenant_id,
        status=payload.status,
    )
    if tenant is None:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Contracting tenant not found.")
    await session.commit()
    return ContractingTenantResponse.model_validate(tenant, from_attributes=True)
