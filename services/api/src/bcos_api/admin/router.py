"""Tenant administration HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.admin.domain import InvalidMembershipAdministration, validate_invited_role
from bcos_api.audit.repository import create_audit_log
from bcos_api.admin.profile_repository import get_tenant_profile, update_tenant_profile
from bcos_api.admin.profile_schemas import TenantProfileResponse, TenantProfileUpdate
from bcos_api.admin.schemas import (
    MembershipDetailsUpdate,
    MembershipInvitationCreate,
    MembershipResponse,
    MembershipStatusUpdate,
    TeamInvitationResponse,
)
from bcos_api.admin.service import (
    invite_tenant_membership,
    list_tenant_memberships,
    remove_tenant_membership,
    update_tenant_membership_details,
    update_tenant_membership_status,
)
from bcos_api.db.session import get_async_session
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.rbac import Permission, require_permission

router=APIRouter(prefix="/api/v1/admin/memberships", tags=["Tenant Administration"])
profile_router=APIRouter(prefix="/api/v1/admin/profile", tags=["Tenant Administration"])
SessionDependency=Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency=Annotated[TenantContext, Depends(get_tenant_context)]


@router.get("", response_model=list[MembershipResponse])
async def list_memberships_endpoint(session: SessionDependency, context: TenantContextDependency) -> list[MembershipResponse]:
    items=await list_tenant_memberships(session, context=context)
    return [MembershipResponse.model_validate(item) for item in items]


@router.post("/invitations", response_model=TeamInvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_membership_endpoint(payload: MembershipInvitationCreate, session: SessionDependency, context: TenantContextDependency) -> TeamInvitationResponse:
    require_permission(context, Permission.TENANT_ADMIN)
    validate_invited_role(actor_role=context.role, invited_role=payload.role)
    email=payload.email.strip().lower()
    name=payload.display_name.strip()
    if not name or "@" not in email:
        raise HTTPException(status_code=422, detail="Nome e e-mail válidos são obrigatórios.")
    await session.execute(text("""UPDATE tenant_user_invitations SET status='REVOKED', updated_at=now() WHERE tenant_id=:tenant_id AND lower(email)=:email AND status='PENDING' AND deleted_at IS NULL"""), {"tenant_id":context.tenant_id,"email":email})
    result=await session.execute(text("""INSERT INTO tenant_user_invitations (tenant_id,display_name,email,role,invited_by_external_user_id) VALUES (:tenant_id,:display_name,:email,CAST(:role AS membership_role),:actor) RETURNING id,tenant_id,display_name,email,role::text AS role,status,expires_at"""), {"tenant_id":context.tenant_id,"display_name":name,"email":email,"role":payload.role.value,"actor":context.external_user_id})
    row=dict(result.mappings().one())
    await create_audit_log(session, tenant_id=context.tenant_id, actor_external_user_id=context.external_user_id, action="TENANT_USER_INVITED", entity_type="tenant_user_invitation", entity_id=row["id"], metadata={"display_name":name,"email":email,"role":payload.role.value})
    await session.commit()
    row["expires_at"]=row["expires_at"].isoformat()
    return TeamInvitationResponse.model_validate(row)


@router.patch("/{membership_id}/status", response_model=MembershipResponse)
async def update_membership_status_endpoint(membership_id: UUID, payload: MembershipStatusUpdate, session: SessionDependency, context: TenantContextDependency) -> MembershipResponse:
    try:
        item=await update_tenant_membership_status(session, context=context, membership_id=membership_id, status=payload.status)
        if item is None:
            raise HTTPException(status_code=404, detail="Membership not found.")
        await session.commit()
    except InvalidMembershipAdministration as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return MembershipResponse.model_validate(item)


@router.patch("/{membership_id}", response_model=MembershipResponse)
async def update_membership_details_endpoint(membership_id: UUID, payload: MembershipDetailsUpdate, session: SessionDependency, context: TenantContextDependency) -> MembershipResponse:
    try:
        item=await update_tenant_membership_details(session, context=context, membership_id=membership_id, display_name=payload.display_name, email=payload.email, role=payload.role)
        if item is None:
            raise HTTPException(status_code=404, detail="Membership not found or protected.")
        await session.commit()
    except InvalidMembershipAdministration as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return MembershipResponse.model_validate(item)


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_membership_endpoint(membership_id: UUID, session: SessionDependency, context: TenantContextDependency) -> None:
    item=await remove_tenant_membership(session, context=context, membership_id=membership_id)
    if item is None:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Membership not found or protected.")
    await session.commit()


@profile_router.get("", response_model=TenantProfileResponse)
async def get_profile_endpoint(session: SessionDependency, context: TenantContextDependency) -> TenantProfileResponse:
    require_permission(context, Permission.TENANT_ADMIN)
    profile = await get_tenant_profile(session, context=context)
    if profile is None:
        raise HTTPException(status_code=404, detail="Tenant profile not found.")
    return TenantProfileResponse.model_validate(dict(profile))


@profile_router.put("", response_model=TenantProfileResponse)
async def update_profile_endpoint(payload: TenantProfileUpdate, session: SessionDependency, context: TenantContextDependency) -> TenantProfileResponse:
    require_permission(context, Permission.TENANT_ADMIN)
    values = {
        "legal_name": payload.legal_name.strip(),
        "trade_name": payload.trade_name.strip(),
        "tax_id": payload.tax_id.strip() if payload.tax_id else None,
        "email": payload.email.strip(),
        "phone": payload.phone.strip() if payload.phone else None,
    }
    if not values["legal_name"] or not values["trade_name"] or not values["email"]:
        raise HTTPException(status_code=422, detail="Required tenant profile fields must not be blank.")
    profile = await update_tenant_profile(session, context=context, values=values)
    if profile is None:
        raise HTTPException(status_code=404, detail="Tenant profile not found.")
    await session.commit()
    return TenantProfileResponse.model_validate(dict(profile))
