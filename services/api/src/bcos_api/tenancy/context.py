"""Authorized tenant context resolution."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.repository import get_membership, tenant_is_active


class TenantAccessDenied(Exception):
    """Raised when an identity cannot operate within the requested tenant."""


@dataclass(frozen=True)
class TenantContext:
    """Authorized tenant context for one authenticated identity."""

    tenant_id: UUID
    membership_id: UUID
    external_user_id: str
    role: MembershipRole
    permissions: frozenset[object] | None = None


async def resolve_tenant_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    external_user_id: str,
) -> TenantContext:
    """Resolve and authorize an identity within one BCOS tenant."""

    if not await tenant_is_active(session, tenant_id=tenant_id):
        raise TenantAccessDenied("Requested tenant is not active.")

    membership = await get_membership(
        session,
        tenant_id=tenant_id,
        external_user_id=external_user_id,
    )

    if membership is None or not membership.is_active:
        raise TenantAccessDenied(
            "Authenticated identity does not have active access "
            "to the requested tenant."
        )

    # Import here to avoid a module cycle: RBAC depends on TenantContext.
    from bcos_api.tenancy.rbac import ROLE_PERMISSIONS, Permission

    # OWNER is the immutable authority. Every other user may receive a
    # customer-defined role. Legacy role permissions are used only for records
    # that have not yet been migrated/assigned by the tenant.
    if membership.role is MembershipRole.OWNER:
        effective = set(ROLE_PERMISSIONS[MembershipRole.OWNER])
    elif membership.access_role_id is not None:
        role_permissions = await session.execute(
            text("""SELECT permission
                    FROM tenant_access_role_permissions
                    WHERE tenant_id=:tenant_id AND role_id=:role_id AND granted=TRUE"""),
            {"tenant_id": membership.tenant_id, "role_id": membership.access_role_id},
        )
        effective = {Permission(row["permission"]) for row in role_permissions.mappings().all()}
    else:
        effective = set(ROLE_PERMISSIONS[membership.role])

    overrides = await session.execute(
        text("""SELECT permission, granted
                FROM tenant_membership_permission_overrides
                WHERE tenant_id=:tenant_id AND membership_id=:membership_id"""),
        {"tenant_id": membership.tenant_id, "membership_id": membership.id},
    )
    for row in overrides.mappings().all():
        permission = Permission(row["permission"])
        if row["granted"]:
            effective.add(permission)
        else:
            effective.discard(permission)

    # OWNER authority is immutable from tenant-side permission overrides.
    if membership.role is MembershipRole.OWNER:
        effective = set(ROLE_PERMISSIONS[MembershipRole.OWNER])

    return TenantContext(
        tenant_id=membership.tenant_id,
        membership_id=membership.id,
        external_user_id=membership.external_user_id,
        role=membership.role,
        permissions=frozenset(effective),
    )
