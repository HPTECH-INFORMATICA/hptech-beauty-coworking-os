"""Persistence for atomic HPTECH tenant onboarding."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.platform.onboarding.domain import ContractingTenant, TenantCommercialStatus


async def create_contracting_tenant(
    session: AsyncSession,
    *,
    name: str,
    slug: str,
    legal_name: str,
    trade_name: str,
    tax_id: str | None,
    email: str,
    phone: str | None,
    owner_external_user_id: str,
) -> ContractingTenant:
    tenant_result = await session.execute(
        text(
            """
            INSERT INTO tenants (name, slug, status)
            VALUES (:name, :slug, 'PENDING_ACTIVATION')
            RETURNING id, name, slug, status::text AS status, created_at
            """
        ),
        {"name": name, "slug": slug},
    )
    tenant = tenant_result.mappings().one()

    await session.execute(
        text(
            """
            INSERT INTO tenant_profiles (
                tenant_id, legal_name, trade_name, tax_id, email, phone
            )
            VALUES (
                :tenant_id, :legal_name, :trade_name, :tax_id, :email, :phone
            )
            """
        ),
        {
            "tenant_id": tenant["id"],
            "legal_name": legal_name,
            "trade_name": trade_name,
            "tax_id": tax_id,
            "email": email,
            "phone": phone,
        },
    )

    await session.execute(
        text(
            """
            INSERT INTO tenant_memberships (
                tenant_id, external_user_id, role, status
            )
            VALUES (:tenant_id, :external_user_id, 'OWNER', 'INVITED')
            """
        ),
        {
            "tenant_id": tenant["id"],
            "external_user_id": owner_external_user_id,
        },
    )

    return ContractingTenant(
        id=tenant["id"],
        name=tenant["name"],
        slug=tenant["slug"],
        status=TenantCommercialStatus(tenant["status"]),
        legal_name=legal_name,
        trade_name=trade_name,
        tax_id=tax_id,
        email=email,
        phone=phone,
        owner_external_user_id=owner_external_user_id,
        created_at=tenant["created_at"],
    )


def _contracting_tenant_from_row(mapping: RowMapping) -> ContractingTenant:
    return ContractingTenant(
        id=mapping["id"],
        name=mapping["name"],
        slug=mapping["slug"],
        status=TenantCommercialStatus(mapping["status"]),
        legal_name=mapping["legal_name"],
        trade_name=mapping["trade_name"],
        tax_id=mapping["tax_id"],
        email=mapping["email"],
        phone=mapping["phone"],
        owner_external_user_id=mapping["owner_external_user_id"],
        created_at=mapping["created_at"],
    )


async def list_contracting_tenants(session: AsyncSession) -> list[ContractingTenant]:
    result = await session.execute(
        text(
            """
            SELECT
                t.id,
                t.name,
                t.slug,
                t.status::text AS status,
                p.legal_name,
                p.trade_name,
                p.tax_id,
                p.email,
                p.phone,
                owner.external_user_id AS owner_external_user_id,
                t.created_at
            FROM tenants AS t
            JOIN tenant_profiles AS p ON p.tenant_id = t.id
            JOIN LATERAL (
                SELECT tm.external_user_id
                FROM tenant_memberships AS tm
                WHERE tm.tenant_id = t.id
                  AND tm.role = 'OWNER'
                ORDER BY tm.created_at ASC
                LIMIT 1
            ) AS owner ON TRUE
            ORDER BY t.created_at DESC, t.id DESC
            """
        )
    )
    return [_contracting_tenant_from_row(row) for row in result.mappings().all()]


async def get_contracting_tenant(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> ContractingTenant | None:
    result = await session.execute(
        text(
            """
            SELECT
                t.id,
                t.name,
                t.slug,
                t.status::text AS status,
                p.legal_name,
                p.trade_name,
                p.tax_id,
                p.email,
                p.phone,
                owner.external_user_id AS owner_external_user_id,
                t.created_at
            FROM tenants AS t
            JOIN tenant_profiles AS p ON p.tenant_id = t.id
            JOIN LATERAL (
                SELECT tm.external_user_id
                FROM tenant_memberships AS tm
                WHERE tm.tenant_id = t.id
                  AND tm.role = 'OWNER'
                ORDER BY tm.created_at ASC
                LIMIT 1
            ) AS owner ON TRUE
            WHERE t.id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().one_or_none()
    return None if row is None else _contracting_tenant_from_row(row)


async def update_contracting_tenant_status(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    status: TenantCommercialStatus,
) -> ContractingTenant | None:
    updated = await session.execute(
        text(
            """
            UPDATE tenants
            SET status = CAST(:status AS tenant_status),
                updated_at = now()
            WHERE id = :tenant_id
            RETURNING id
            """
        ),
        {"tenant_id": tenant_id, "status": status.value},
    )
    if updated.scalar_one_or_none() is None:
        return None
    return await get_contracting_tenant(session, tenant_id=tenant_id)


async def create_owner_invitation(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    external_user_id: str,
) -> UUID | None:
    tenant_exists = await session.execute(
        text("SELECT id FROM tenants WHERE id = :tenant_id"),
        {"tenant_id": tenant_id},
    )
    if tenant_exists.scalar_one_or_none() is None:
        return None

    result = await session.execute(
        text(
            """
            INSERT INTO tenant_memberships (
                tenant_id, external_user_id, role, status
            )
            VALUES (:tenant_id, :external_user_id, 'OWNER', 'INVITED')
            RETURNING id
            """
        ),
        {"tenant_id": tenant_id, "external_user_id": external_user_id},
    )
    return result.scalar_one()
