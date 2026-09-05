"""Tenant-scoped persistence for BCOS availability."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.availability.domain import Availability


async def list_resource_availability(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    resource_id: UUID | None = None,
    category_id: UUID | None = None,
) -> list[Availability]:
    """Calculate preventive availability for tenant-scoped resources."""

    result = await session.execute(
        text(
            """
            SELECT
                r.id AS resource_id,
                NOT EXISTS (
                    SELECT 1
                    FROM resource_occupancies ro
                    WHERE ro.tenant_id = r.tenant_id
                      AND ro.resource_id = r.id
                      AND ro.status = 'ACTIVE'
                      AND ro.period && tstzrange(
                          :starts_at,
                          :ends_at,
                          '[)'
                      )
                ) AS available,
                (
                    SELECT ro.source_type::text
                    FROM resource_occupancies ro
                    WHERE ro.tenant_id = r.tenant_id
                      AND ro.resource_id = r.id
                      AND ro.status = 'ACTIVE'
                      AND ro.period && tstzrange(
                          :starts_at,
                          :ends_at,
                          '[)'
                      )
                    ORDER BY lower(ro.period), ro.id
                    LIMIT 1
                ) AS reason
            FROM resources r
            WHERE r.tenant_id = :tenant_id
              AND r.unit_id = :unit_id
              AND r.deleted_at IS NULL
              AND r.active = true
              AND (:resource_id IS NULL OR r.id = :resource_id)
              AND (:category_id IS NULL OR r.category_id = :category_id)
            ORDER BY r.name, r.id
            """
        ),
        {
            "tenant_id": tenant_id,
            "unit_id": unit_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "resource_id": resource_id,
            "category_id": category_id,
        },
    )

    return [
        Availability(
            resource_id=row["resource_id"],
            available=row["available"],
            reason=row["reason"],
        )
        for row in result.mappings().all()
    ]
