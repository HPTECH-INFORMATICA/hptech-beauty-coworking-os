"""HPTECH platform administration HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.platform.audit import create_platform_audit_log
from bcos_api.platform.dependencies import get_platform_context
from bcos_api.platform.domain import PlatformContext
from bcos_api.platform.onboarding.domain import InvalidTenantOnboarding
from bcos_api.platform.onboarding.repository import (
    create_owner_invitation,
    get_contracting_tenant,
    list_contracting_tenants,
    update_contracting_tenant_status,
)
from bcos_api.platform.onboarding.schemas import (
    ContractingTenant as ContractingTenantResponse,
)
from bcos_api.platform.onboarding.schemas import (
    ContractingTenantCreate,
    ContractingTenantStatusUpdate,
    OwnerInvitation,
    OwnerInvitationCreate,
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
        await create_platform_audit_log(
            session,
            actor_external_user_id=context.external_user_id,
            action="TENANT_CREATED",
            entity_type="tenant",
            entity_id=tenant.id,
            tenant_id=tenant.id,
            metadata={"status": tenant.status.value, "owner_external_user_id": tenant.owner_external_user_id},
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
    tenant = await update_contracting_tenant_status(
        session,
        tenant_id=tenant_id,
        status=payload.status,
    )
    if tenant is None:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Contracting tenant not found.")
    await create_platform_audit_log(
        session,
        actor_external_user_id=context.external_user_id,
        action="TENANT_STATUS_CHANGED",
        entity_type="tenant",
        entity_id=tenant.id,
        tenant_id=tenant.id,
        metadata={"status": tenant.status.value},
    )
    await session.commit()
    return ContractingTenantResponse.model_validate(tenant, from_attributes=True)


@router.post(
    "/tenants/{tenant_id}/owner-invitations",
    response_model=OwnerInvitation,
    status_code=status.HTTP_201_CREATED,
)
async def create_owner_invitation_endpoint(
    tenant_id: UUID,
    payload: OwnerInvitationCreate,
    session: SessionDependency,
    context: PlatformContextDependency,
) -> OwnerInvitation:
    external_user_id = payload.external_user_id.strip()
    if not external_user_id:
        raise HTTPException(status_code=422, detail="external_user_id must not be blank.")
    try:
        membership_id = await create_owner_invitation(
            session,
            tenant_id=tenant_id,
            external_user_id=external_user_id,
        )
        if membership_id is None:
            await session.rollback()
            raise HTTPException(status_code=404, detail="Contracting tenant not found.")
        await create_platform_audit_log(
            session,
            actor_external_user_id=context.external_user_id,
            action="TENANT_OWNER_INVITED",
            entity_type="tenant_membership",
            entity_id=membership_id,
            tenant_id=tenant_id,
            metadata={"external_user_id": external_user_id, "role": "OWNER", "status": "INVITED"},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identity already has a membership in this tenant.",
        ) from exc
    return OwnerInvitation(
        membership_id=membership_id,
        tenant_id=tenant_id,
        external_user_id=external_user_id,
    )
