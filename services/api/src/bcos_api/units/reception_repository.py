"""Reception-hours tenant administration persistence."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.context import TenantContext


async def list_reception_hours(session: AsyncSession, *, context: TenantContext, unit_id):
    result = await session.execute(
        text("""SELECT day_of_week, opens_at, closes_at, is_closed
                FROM unit_reception_hours
                WHERE tenant_id=:tenant_id AND unit_id=:unit_id
                ORDER BY day_of_week"""),
        {"tenant_id": context.tenant_id, "unit_id": unit_id},
    )
    return result.mappings().all()


async def replace_reception_hours(session: AsyncSession, *, context: TenantContext, unit_id, hours):
    for item in hours:
        await session.execute(
            text("""INSERT INTO unit_reception_hours
                    (tenant_id, unit_id, day_of_week, opens_at, closes_at, is_closed)
                    VALUES (:tenant_id, :unit_id, :day_of_week, :opens_at, :closes_at, :is_closed)
                    ON CONFLICT (tenant_id, unit_id, day_of_week)
                    DO UPDATE SET opens_at=EXCLUDED.opens_at, closes_at=EXCLUDED.closes_at,
                                  is_closed=EXCLUDED.is_closed, updated_at=now()"""),
            {"tenant_id": context.tenant_id, "unit_id": unit_id, **item},
        )
    return await list_reception_hours(session, context=context, unit_id=unit_id)
