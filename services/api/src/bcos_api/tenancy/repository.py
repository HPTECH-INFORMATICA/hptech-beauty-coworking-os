"""Tenant membership persistence queries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.membership import MembershipRole, MembershipStatus, TenantMembership


async def tenant_is_active(session: AsyncSession, *, tenant_id: UUID) -> bool:
    result = await session.execute(text("""SELECT status::text FROM tenants WHERE id=:tenant_id LIMIT 1"""), {"tenant_id": tenant_id})
    return result.scalar_one_or_none() == "ACTIVE"


async def get_membership(session: AsyncSession, *, tenant_id: UUID, external_user_id: str) -> TenantMembership | None:
    result = await session.execute(text("""
        SELECT id,tenant_id,external_user_id,role::text AS role,status::text AS status,
               display_name,email,access_role_id
        FROM tenant_memberships
        WHERE tenant_id=:tenant_id AND external_user_id=:external_user_id AND deleted_at IS NULL
        LIMIT 1
    """), {"tenant_id": tenant_id, "external_user_id": external_user_id})
    row=result.mappings().one_or_none()
    if row is None:
        return None
    return TenantMembership(
        id=row["id"], tenant_id=row["tenant_id"], external_user_id=row["external_user_id"],
        role=MembershipRole(row["role"]), status=MembershipStatus(row["status"]),
        display_name=row["display_name"], email=row["email"], access_role_id=row["access_role_id"],
    )
