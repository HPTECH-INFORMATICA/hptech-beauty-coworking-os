"""Persistence for tenant membership administration."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.membership import MembershipRole, MembershipStatus, TenantMembership


def _membership(row: object) -> TenantMembership:
    from sqlalchemy import RowMapping
    if not isinstance(row, RowMapping):
        raise TypeError("Expected RowMapping.")
    return TenantMembership(id=row["id"], tenant_id=row["tenant_id"], external_user_id=row["external_user_id"], role=MembershipRole(row["role"]), status=MembershipStatus(row["status"]))


async def list_memberships(session: AsyncSession, *, tenant_id: UUID) -> list[TenantMembership]:
    result = await session.execute(text("""SELECT id, tenant_id, external_user_id, role::text AS role, status::text AS status FROM tenant_memberships WHERE tenant_id=:tenant_id AND deleted_at IS NULL ORDER BY created_at ASC, id ASC"""), {"tenant_id": tenant_id})
    return [_membership(row) for row in result.mappings().all()]


async def invite_membership(session: AsyncSession, *, tenant_id: UUID, external_user_id: str, role: MembershipRole) -> TenantMembership:
    result = await session.execute(text("""INSERT INTO tenant_memberships (tenant_id, external_user_id, role, status) VALUES (:tenant_id, :external_user_id, CAST(:role AS membership_role), 'INVITED') RETURNING id, tenant_id, external_user_id, role::text AS role, status::text AS status"""), {"tenant_id": tenant_id, "external_user_id": external_user_id.strip(), "role": role.value})
    return _membership(result.mappings().one())


async def set_membership_status(session: AsyncSession, *, tenant_id: UUID, membership_id: UUID, status: MembershipStatus) -> TenantMembership | None:
    result = await session.execute(text("""UPDATE tenant_memberships SET status=CAST(:status AS membership_status), updated_at=now() WHERE id=:membership_id AND tenant_id=:tenant_id AND deleted_at IS NULL RETURNING id, tenant_id, external_user_id, role::text AS role, status::text AS status"""), {"tenant_id": tenant_id, "membership_id": membership_id, "status": status.value})
    row=result.mappings().one_or_none()
    return None if row is None else _membership(row)
