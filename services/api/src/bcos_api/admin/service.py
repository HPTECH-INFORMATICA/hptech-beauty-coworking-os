"""Tenant membership administration application service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.admin.domain import validate_invited_role, validate_membership_status
from bcos_api.admin.repository import invite_membership, list_memberships, set_membership_status
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole, MembershipStatus, TenantMembership
from bcos_api.tenancy.rbac import Permission, require_permission


async def list_tenant_memberships(session: AsyncSession, *, context: TenantContext) -> list[TenantMembership]:
    require_permission(context, Permission.TENANT_ADMIN)
    return await list_memberships(session, tenant_id=context.tenant_id)


async def invite_tenant_membership(session: AsyncSession, *, context: TenantContext, external_user_id: str, role: MembershipRole) -> TenantMembership:
    require_permission(context, Permission.TENANT_ADMIN)
    validate_invited_role(actor_role=context.role, invited_role=role)
    if not external_user_id.strip():
        raise ValueError("external_user_id must not be blank.")
    return await invite_membership(session, tenant_id=context.tenant_id, external_user_id=external_user_id, role=role)


async def update_tenant_membership_status(session: AsyncSession, *, context: TenantContext, membership_id: UUID, status: MembershipStatus) -> TenantMembership | None:
    require_permission(context, Permission.TENANT_ADMIN)
    validate_membership_status(status)
    return await set_membership_status(session, tenant_id=context.tenant_id, membership_id=membership_id, status=status)
