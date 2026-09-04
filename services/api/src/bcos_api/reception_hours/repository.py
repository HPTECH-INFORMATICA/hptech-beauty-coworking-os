"""Tenant-scoped persistence for unit reception hours."""

from __future__ import annotations

from datetime import time
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.reception_hours.domain import ReceptionHours


def _reception_hours_from_row(
    row: dict[str, object],
) -> ReceptionHours:
    """Map one database row to the ReceptionHours domain model."""

    return ReceptionHours(
        id=row["id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        unit_id=row["unit_id"],  # type: ignore[arg-type]
        day_of_week=row["day_of_week"],  # type: ignore[arg-type]
        opens_at=row["opens_at"],  # type: ignore[arg-type]
        closes_at=row["closes_at"],  # type: ignore[arg-type]
        is_closed=row["is_closed"],  # type: ignore[arg-type]
    )


async def list_reception_hours(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
) -> list[ReceptionHours]:
    """List reception hours for one unit inside one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                unit_id,
                day_of_week,
                opens_at,
                closes_at,
                is_closed
            FROM unit_reception_hours
            WHERE tenant_id = :tenant_id
              AND unit_id = :unit_id
            ORDER BY day_of_week
            """
        ),
        {
            "tenant_id": tenant_id,
            "unit_id": unit_id,
        },
    )

    return [
        _reception_hours_from_row(dict(row))
        for row in result.mappings().all()
    ]


async def replace_reception_hours(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
    entries: list[tuple[int, time | None, time | None, bool]],
) -> list[ReceptionHours]:
    """Replace the complete reception-hours set for one unit."""

    await session.execute(
        text(
            """
            DELETE FROM unit_reception_hours
            WHERE tenant_id = :tenant_id
              AND unit_id = :unit_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "unit_id": unit_id,
        },
    )

    for day_of_week, opens_at, closes_at, is_closed in entries:
        await session.execute(
            text(
                """
                INSERT INTO unit_reception_hours (
                    tenant_id,
                    unit_id,
                    day_of_week,
                    opens_at,
                    closes_at,
                    is_closed
                )
                VALUES (
                    :tenant_id,
                    :unit_id,
                    :day_of_week,
                    :opens_at,
                    :closes_at,
                    :is_closed
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "unit_id": unit_id,
                "day_of_week": day_of_week,
                "opens_at": opens_at,
                "closes_at": closes_at,
                "is_closed": is_closed,
            },
        )

    return await list_reception_hours(
        session,
        tenant_id=tenant_id,
        unit_id=unit_id,
    )
