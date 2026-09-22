"""Persistence for atomic HPTECH tenant onboarding."""

from __future__ import annotations

from sqlalchemy import text
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
