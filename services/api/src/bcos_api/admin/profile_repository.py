"""Tenant self-administration persistence."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.context import TenantContext


async def get_tenant_profile(session: AsyncSession, *, context: TenantContext):
    result = await session.execute(
        text("""SELECT legal_name, trade_name, tax_id, email, phone
                FROM tenant_profiles WHERE tenant_id = :tenant_id"""),
        {"tenant_id": context.tenant_id},
    )
    return result.mappings().one_or_none()


async def update_tenant_profile(session: AsyncSession, *, context: TenantContext, values: dict[str, str | None]):
    result = await session.execute(
        text("""UPDATE tenant_profiles
                SET legal_name=:legal_name, trade_name=:trade_name, tax_id=:tax_id,
                    email=:email, phone=:phone, updated_at=now()
                WHERE tenant_id=:tenant_id
                RETURNING legal_name, trade_name, tax_id, email, phone"""),
        {**values, "tenant_id": context.tenant_id},
    )
    return result.mappings().one_or_none()
