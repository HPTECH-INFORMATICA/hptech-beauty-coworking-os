"""Application service for HPTECH contracting-company onboarding."""

from __future__ import annotations

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
    owner_external_user_id: str,
) -> ContractingTenant:
    if context.role is not PlatformOperatorRole.PLATFORM_ADMIN:
        raise InvalidTenantOnboarding("Platform administrator authority is required.")

    normalized_slug = required_text(slug, field="slug", maximum=100).lower()
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in normalized_slug):
        raise InvalidTenantOnboarding("slug may contain only lowercase letters, digits and hyphens.")

    return await create_contracting_tenant(
        session,
        name=required_text(name, field="name", maximum=160),
        slug=normalized_slug,
        legal_name=required_text(legal_name, field="legal_name", maximum=200),
        trade_name=required_text(trade_name, field="trade_name", maximum=200),
        tax_id=tax_id.strip() if tax_id and tax_id.strip() else None,
        email=required_text(email, field="email", maximum=255),
        phone=phone.strip() if phone and phone.strip() else None,
        owner_external_user_id=required_text(
            owner_external_user_id,
            field="owner_external_user_id",
            maximum=255,
        ),
    )
