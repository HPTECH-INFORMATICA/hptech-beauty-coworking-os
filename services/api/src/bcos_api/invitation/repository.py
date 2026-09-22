"""Authenticated membership invitation acceptance persistence."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.membership import MembershipRole, MembershipStatus, TenantMembership


async def list_pending_invitations(
    session: AsyncSession,
    *,
    external_user_id: str,
) -> list[TenantMembership]:
    result = await session.execute(
        text(
            """SELECT id, tenant_id, external_user_id,
                      role::text AS role, status::text AS status
            FROM tenant_memberships
            WHERE external_user_id = :external_user_id
              AND status = 'INVITED'
              AND deleted_at IS NULL
            ORDER BY created_at ASC, id ASC"""
        ),
        {"external_user_id": external_user_id},
    )
    return [
        TenantMembership(
            id=row["id"],
            tenant_id=row["tenant_id"],
            external_user_id=row["external_user_id"],
            role=MembershipRole(row["role"]),
            status=MembershipStatus(row["status"]),
        )
        for row in result.mappings().all()
    ]


async def accept_invited_membership(
    session: AsyncSession,
    *,
    membership_id: UUID,
    external_user_id: str,
) -> TenantMembership | None:
    result = await session.execute(
        text(
            """UPDATE tenant_memberships
            SET status = 'ACTIVE', updated_at = now()
            WHERE id = :membership_id
              AND external_user_id = :external_user_id
              AND status = 'INVITED'
              AND deleted_at IS NULL
            RETURNING id, tenant_id, external_user_id,
                      role::text AS role, status::text AS status"""
        ),
        {"membership_id": membership_id, "external_user_id": external_user_id},
    )
    row = result.mappings().one_or_none()
    if row is None:
        return None
    return TenantMembership(
        id=row["id"],
        tenant_id=row["tenant_id"],
        external_user_id=row["external_user_id"],
        role=MembershipRole(row["role"]),
        status=MembershipStatus(row["status"]),
    )
