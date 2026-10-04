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
    return TenantMembership(id=row["id"], tenant_id=row["tenant_id"], external_user_id=row["external_user_id"], role=MembershipRole(row["role"]), status=MembershipStatus(row["status"]), display_name=row.get("display_name"), email=row.get("email"), access_role_id=row.get("access_role_id"))


async def list_memberships(session: AsyncSession, *, tenant_id: UUID) -> list[TenantMembership]:
    result = await session.execute(text("""SELECT m.id, m.tenant_id, m.external_user_id, m.role::text AS role, m.status::text AS status, COALESCE(m.display_name, NULLIF(to_jsonb(u)->>'name','')) AS display_name, COALESCE(m.email, NULLIF(to_jsonb(u)->>'email','')) AS email, m.access_role_id FROM tenant_memberships m LEFT JOIN neon_auth."user" u ON u.id::text=m.external_user_id WHERE m.tenant_id=:tenant_id AND m.deleted_at IS NULL ORDER BY m.created_at ASC, m.id ASC"""), {"tenant_id": tenant_id})
    return [_membership(row) for row in result.mappings().all()]


async def invite_membership(session: AsyncSession, *, tenant_id: UUID, external_user_id: str, role: MembershipRole) -> TenantMembership:
    result = await session.execute(text("""INSERT INTO tenant_memberships (tenant_id, external_user_id, role, status) VALUES (:tenant_id, :external_user_id, CAST(:role AS membership_role), 'INVITED') RETURNING id, tenant_id, external_user_id, role::text AS role, status::text AS status, display_name, email, access_role_id"""), {"tenant_id": tenant_id, "external_user_id": external_user_id.strip(), "role": role.value})
    return _membership(result.mappings().one())


async def set_membership_status(session: AsyncSession, *, tenant_id: UUID, membership_id: UUID, status: MembershipStatus) -> TenantMembership | None:
    result = await session.execute(text("""UPDATE tenant_memberships SET status=CAST(:status AS membership_status), updated_at=now() WHERE id=:membership_id AND tenant_id=:tenant_id AND deleted_at IS NULL AND role <> 'OWNER' RETURNING id, tenant_id, external_user_id, role::text AS role, status::text AS status, display_name, email, access_role_id"""), {"tenant_id": tenant_id, "membership_id": membership_id, "status": status.value})
    row=result.mappings().one_or_none()
    return None if row is None else _membership(row)


async def update_membership_details(session: AsyncSession, *, tenant_id: UUID, membership_id: UUID, display_name: str) -> TenantMembership | None:
    result = await session.execute(text("""UPDATE tenant_memberships SET display_name=:display_name, updated_at=now() WHERE id=:membership_id AND tenant_id=:tenant_id AND deleted_at IS NULL AND role <> 'OWNER' RETURNING id, tenant_id, external_user_id, role::text AS role, status::text AS status, display_name, email, access_role_id"""), {"tenant_id": tenant_id, "membership_id": membership_id, "display_name": display_name.strip()})
    row=result.mappings().one_or_none()
    return None if row is None else _membership(row)

async def remove_membership(session: AsyncSession, *, tenant_id: UUID, membership_id: UUID) -> TenantMembership | None:
    result = await session.execute(text("""UPDATE tenant_memberships SET status='INACTIVE', deleted_at=now(), updated_at=now() WHERE id=:membership_id AND tenant_id=:tenant_id AND deleted_at IS NULL AND role <> 'OWNER' RETURNING id, tenant_id, external_user_id, role::text AS role, status::text AS status, display_name, email, access_role_id"""), {"tenant_id": tenant_id, "membership_id": membership_id})
    row=result.mappings().one_or_none()
    return None if row is None else _membership(row)


async def get_membership_permission_overrides(session: AsyncSession, *, tenant_id: UUID, membership_id: UUID) -> dict[str, bool]:
    result = await session.execute(text("""SELECT permission, granted
        FROM tenant_membership_permission_overrides
        WHERE tenant_id=:tenant_id AND membership_id=:membership_id"""),
        {"tenant_id": tenant_id, "membership_id": membership_id})
    return {str(row["permission"]): bool(row["granted"]) for row in result.mappings().all()}


async def replace_membership_permission_overrides(
    session: AsyncSession, *, tenant_id: UUID, membership_id: UUID, values: dict[str, bool]
) -> bool:
    target = await session.execute(text("""SELECT role::text AS role FROM tenant_memberships
        WHERE id=:membership_id AND tenant_id=:tenant_id AND deleted_at IS NULL"""),
        {"tenant_id": tenant_id, "membership_id": membership_id})
    row = target.mappings().one_or_none()
    if row is None or row["role"] == "OWNER":
        return False
    await session.execute(text("""DELETE FROM tenant_membership_permission_overrides
        WHERE tenant_id=:tenant_id AND membership_id=:membership_id"""),
        {"tenant_id": tenant_id, "membership_id": membership_id})
    for permission, granted in values.items():
        await session.execute(text("""INSERT INTO tenant_membership_permission_overrides
            (tenant_id,membership_id,permission,granted)
            VALUES (:tenant_id,:membership_id,:permission,:granted)"""),
            {"tenant_id": tenant_id, "membership_id": membership_id, "permission": permission, "granted": granted})
    return True
