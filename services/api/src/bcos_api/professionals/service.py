"""Application service for BCOS professionals."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.professionals.domain import (
    Professional,
    ProfessionalStatus,
    normalize_optional_text,
    validate_professional_name,
)
from bcos_api.professionals.repository import (
    create_professional,
    get_professional,
    list_professionals,
    update_professional,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission


class ProfessionalNotFound(Exception):
    """Raised when a professional is not visible inside the authorized tenant."""


def _normalize_professional_fields(
    *,
    external_user_id: str | None,
    name: str,
    email: str | None,
    phone: str | None,
) -> tuple[str | None, str, str | None, str | None]:
    """Normalize professional fields according to the database baseline."""

    normalized_external_user_id = normalize_optional_text(
        external_user_id,
        field_name="external_user_id",
        max_length=255,
    )
    normalized_name = validate_professional_name(name)
    normalized_email = normalize_optional_text(
        email,
        field_name="email",
        max_length=255,
    )
    normalized_phone = normalize_optional_text(
        phone,
        field_name="phone",
        max_length=40,
    )

    return (
        normalized_external_user_id,
        normalized_name,
        normalized_email,
        normalized_phone,
    )


async def list_tenant_professionals(
    session: AsyncSession,
    *,
    context: TenantContext,
) -> list[Professional]:
    """List professionals visible to an operational tenant member."""

    require_permission(context, Permission.OPERATIONS)

    return await list_professionals(
        session,
        tenant_id=context.tenant_id,
    )


async def get_tenant_professional(
    session: AsyncSession,
    *,
    context: TenantContext,
    professional_id: UUID,
) -> Professional:
    """Get one professional without allowing cross-tenant lookup."""

    require_permission(context, Permission.OPERATIONS)

    professional = await get_professional(
        session,
        tenant_id=context.tenant_id,
        professional_id=professional_id,
    )

    if professional is None:
        raise ProfessionalNotFound("Professional was not found.")

    return professional


async def create_tenant_professional(
    session: AsyncSession,
    *,
    context: TenantContext,
    external_user_id: str | None,
    name: str,
    email: str | None,
    phone: str | None,
) -> Professional:
    """Create a validated professional inside the authorized tenant."""

    require_permission(context, Permission.OPERATIONS)

    (
        normalized_external_user_id,
        normalized_name,
        normalized_email,
        normalized_phone,
    ) = _normalize_professional_fields(
        external_user_id=external_user_id,
        name=name,
        email=email,
        phone=phone,
    )

    return await create_professional(
        session,
        tenant_id=context.tenant_id,
        external_user_id=normalized_external_user_id,
        name=normalized_name,
        email=normalized_email,
        phone=normalized_phone,
    )


async def update_tenant_professional(
    session: AsyncSession,
    *,
    context: TenantContext,
    professional_id: UUID,
    external_user_id: str | None,
    name: str,
    email: str | None,
    phone: str | None,
    status: ProfessionalStatus,
) -> Professional:
    """Update a validated professional inside the authorized tenant."""

    require_permission(context, Permission.OPERATIONS)

    (
        normalized_external_user_id,
        normalized_name,
        normalized_email,
        normalized_phone,
    ) = _normalize_professional_fields(
        external_user_id=external_user_id,
        name=name,
        email=email,
        phone=phone,
    )

    professional = await update_professional(
        session,
        tenant_id=context.tenant_id,
        professional_id=professional_id,
        external_user_id=normalized_external_user_id,
        name=normalized_name,
        email=normalized_email,
        phone=normalized_phone,
        status=status,
    )

    if professional is None:
        raise ProfessionalNotFound("Professional was not found.")

    return professional
