"""Tenant administration HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.admin.domain import InvalidMembershipAdministration, validate_invited_role
from bcos_api.admin.profile_repository import get_tenant_profile, update_tenant_profile
from bcos_api.admin.profile_schemas import TenantProfileResponse, TenantProfileUpdate
from bcos_api.admin.repository import (
    get_membership_permission_overrides,
    replace_membership_permission_overrides,
)
from bcos_api.admin.schemas import (
    MembershipDetailsUpdate,
    MembershipInvitationCreate,
    MembershipPermissionsUpdate,
    MembershipResponse,
    MembershipStatusUpdate,
    TeamInvitationResponse,
)
from bcos_api.admin.service import (
    list_tenant_memberships,
    remove_tenant_membership,
    update_tenant_membership_details,
    update_tenant_membership_status,
)
from bcos_api.audit.repository import create_audit_log
from bcos_api.db.session import get_async_session
from bcos_api.notifications.email import send_team_access_invitation
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import ROLE_PERMISSIONS, Permission, require_permission

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
    require_permission(context, Permission.USER_ADMIN)
    validate_invited_role(actor_role=context.role, invited_role=payload.role)
    access_role = await session.execute(text("""SELECT id,name FROM tenant_access_roles
        WHERE id=:role_id AND tenant_id=:tenant_id AND active=TRUE AND deleted_at IS NULL"""),
        {"role_id": payload.access_role_id, "tenant_id": context.tenant_id})
    access_role_row = access_role.mappings().one_or_none()
    if access_role_row is None:
        raise HTTPException(status_code=422, detail="Selecione um papel cadastrado e ativo.")
    email=payload.email.strip().lower()
    name=payload.display_name.strip()
    if not name or "@" not in email:
        raise HTTPException(status_code=422, detail="Nome e e-mail válidos são obrigatórios.")
    await session.execute(text("""UPDATE tenant_user_invitations SET status='REVOKED', updated_at=now() WHERE tenant_id=:tenant_id AND lower(email)=:email AND status='PENDING' AND deleted_at IS NULL"""), {"tenant_id":context.tenant_id,"email":email})
    result=await session.execute(text("""INSERT INTO tenant_user_invitations (tenant_id,display_name,email,role,access_role_id,invited_by_external_user_id) VALUES (:tenant_id,:display_name,:email,CAST(:role AS membership_role),:access_role_id,:actor) RETURNING id,tenant_id,display_name,email,role::text AS role,status,expires_at"""), {"tenant_id":context.tenant_id,"display_name":name,"email":email,"role":payload.role.value,"access_role_id":payload.access_role_id,"actor":context.external_user_id})
    row=dict(result.mappings().one())
    tenant_result=await session.execute(text("SELECT name FROM tenants WHERE id=:tenant_id"), {"tenant_id":context.tenant_id})
    tenant_name=str(tenant_result.scalar_one())
    role_label={"ADMIN":"Administrador","RECEPTION":"Recepção","PROFESSIONAL":"Profissional"}[payload.role.value]
    try:
        send_team_access_invitation(to_email=email, display_name=name, tenant_name=tenant_name, role_label=role_label)
    except RuntimeError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail="TEAM_INVITATION_EMAIL_FAILED") from exc
    await create_audit_log(session, tenant_id=context.tenant_id, actor_external_user_id=context.external_user_id, action="TENANT_USER_INVITED", entity_type="tenant_user_invitation", entity_id=row["id"], metadata={"display_name":name,"email":email,"access_role_id":str(payload.access_role_id),"access_role_name":access_role_row["name"],"delivery":"EMAIL"})
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
        item=await update_tenant_membership_details(session, context=context, membership_id=membership_id, display_name=payload.display_name, role=payload.role)
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


@router.get("/{membership_id}/permissions")
async def get_membership_permissions_endpoint(
    membership_id: UUID, session: SessionDependency, context: TenantContextDependency
) -> dict[str, object]:
    require_permission(context, Permission.USER_ADMIN)
    membership_result = await session.execute(text("""SELECT role::text AS role, access_role_id FROM tenant_memberships
        WHERE id=:membership_id AND tenant_id=:tenant_id AND deleted_at IS NULL"""),
        {"membership_id": membership_id, "tenant_id": context.tenant_id})
    row = membership_result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Membership not found.")
    role = MembershipRole(row["role"])
    if role is MembershipRole.OWNER:
        effective = set(ROLE_PERMISSIONS[role])
    elif row["access_role_id"] is not None:
        role_permissions = await session.execute(text("""SELECT permission FROM tenant_access_role_permissions
            WHERE tenant_id=:tenant_id AND role_id=:role_id AND granted=TRUE"""),
            {"tenant_id": context.tenant_id, "role_id": row["access_role_id"]})
        effective = {Permission(item["permission"]) for item in role_permissions.mappings().all()}
    else:
        effective = set(ROLE_PERMISSIONS[role])
    overrides = await get_membership_permission_overrides(session, tenant_id=context.tenant_id, membership_id=membership_id)
    for name, granted in overrides.items():
        permission = Permission(name)
        effective.add(permission) if granted else effective.discard(permission)
    return {"permissions": sorted(p.value for p in effective)}


@router.put("/{membership_id}/permissions")
async def update_membership_permissions_endpoint(
    membership_id: UUID, payload: MembershipPermissionsUpdate,
    session: SessionDependency, context: TenantContextDependency
) -> dict[str, object]:
    require_permission(context, Permission.USER_ADMIN)
    membership_result = await session.execute(text("""SELECT role::text AS role, access_role_id FROM tenant_memberships
        WHERE id=:membership_id AND tenant_id=:tenant_id AND deleted_at IS NULL"""),
        {"membership_id": membership_id, "tenant_id": context.tenant_id})
    row = membership_result.mappings().one_or_none()
    if row is None or row["role"] == "OWNER":
        raise HTTPException(status_code=404, detail="Membership not found or protected.")
    role = MembershipRole(row["role"])
    requested = set(payload.permissions)
    # Aggregate legacy permissions are internal. Customer-defined role permissions
    # are the baseline; per-user differences are stored only as overrides.
    editable = {p for p in Permission if p not in {Permission.TENANT_ADMIN, Permission.OPERATIONS}}
    requested &= editable
    if row["access_role_id"] is not None:
        role_permissions = await session.execute(text("""SELECT permission FROM tenant_access_role_permissions
            WHERE tenant_id=:tenant_id AND role_id=:role_id AND granted=TRUE"""),
            {"tenant_id": context.tenant_id, "role_id": row["access_role_id"]})
        defaults = {Permission(item["permission"]) for item in role_permissions.mappings().all()} & editable
    else:
        defaults = set(ROLE_PERMISSIONS[role]) & editable
    overrides = {p.value: (p in requested) for p in editable if (p in requested) != (p in defaults)}
    if not await replace_membership_permission_overrides(
        session, tenant_id=context.tenant_id, membership_id=membership_id, values=overrides
    ):
        await session.rollback()
        raise HTTPException(status_code=404, detail="Membership not found or protected.")
    await create_audit_log(session, tenant_id=context.tenant_id,
        actor_external_user_id=context.external_user_id, action="TENANT_MEMBERSHIP_PERMISSIONS_CHANGED",
        entity_type="tenant_membership", entity_id=membership_id,
        metadata={"permissions": sorted(p.value for p in requested)})
    await session.commit()
    return {"permissions": sorted(p.value for p in requested)}


@profile_router.get("", response_model=TenantProfileResponse)
async def get_profile_endpoint(session: SessionDependency, context: TenantContextDependency) -> TenantProfileResponse:
    require_permission(context, Permission.ADMIN_CONFIG)
    profile = await get_tenant_profile(session, context=context)
    if profile is None:
        raise HTTPException(status_code=404, detail="Tenant profile not found.")
    return TenantProfileResponse.model_validate(dict(profile))


@profile_router.put("", response_model=TenantProfileResponse)
async def update_profile_endpoint(payload: TenantProfileUpdate, session: SessionDependency, context: TenantContextDependency) -> TenantProfileResponse:
    require_permission(context, Permission.ADMIN_CONFIG)
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
