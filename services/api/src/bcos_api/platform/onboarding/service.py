"""Application service for HPTECH contracting-company onboarding."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.platform.domain import PlatformContext, PlatformOperatorRole
from bcos_api.platform.onboarding.domain import (
    ContractingTenant,
    InvalidTenantOnboarding,
    required_text,
)
from bcos_api.platform.onboarding.repository import create_contracting_tenant


async def onboard_contracting_tenant(
    session: AsyncSession,
    *,
    context: PlatformContext,
    name: str,
    slug: str,
    legal_name: str,
    trade_name: str,
    tax_id: str | None,
    email: str,
    phone: str | None,
    owner_external_user_id: str | None = None,
    owner_email: str | None = None,
) -> ContractingTenant:
    if context.role is not PlatformOperatorRole.PLATFORM_ADMIN:
        raise InvalidTenantOnboarding("Platform administrator authority is required.")

    normalized_slug = required_text(slug, field="slug", maximum=100).lower()
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in normalized_slug):
        raise InvalidTenantOnboarding("slug may contain only lowercase letters, digits and hyphens.")

    resolved_owner_external_user_id = owner_external_user_id.strip() if owner_external_user_id else ""
    if owner_email:
        normalized_owner_email = required_text(owner_email, field="owner_email", maximum=255).lower()
        result = await session.execute(
            text('SELECT id FROM neon_auth."user" WHERE lower(email) = :email LIMIT 1'),
            {"email": normalized_owner_email},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise InvalidTenantOnboarding(
                "O proprietário ainda não possui uma identidade Neon Auth. "
                "Crie a conta de acesso com este e-mail antes de concluir o onboarding."
            )
        resolved_owner_external_user_id = str(row["id"]).strip()
    return await create_contracting_tenant(
        session,
        name=required_text(name, field="name", maximum=160),
        slug=normalized_slug,
        legal_name=required_text(legal_name, field="legal_name", maximum=200),
        trade_name=required_text(trade_name, field="trade_name", maximum=200),
        tax_id=tax_id.strip() if tax_id and tax_id.strip() else None,
        email=required_text(email, field="email", maximum=255),
        phone=phone.strip() if phone and phone.strip() else None,
        owner_external_user_id=(
            required_text(
                resolved_owner_external_user_id,
                field="owner_external_user_id",
                maximum=255,
            )
            if resolved_owner_external_user_id
            else None
        ),
    )
