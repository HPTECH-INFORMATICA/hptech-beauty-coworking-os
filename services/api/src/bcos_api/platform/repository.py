"""Persistence for HPTECH platform operators."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.platform.domain import (
    PlatformOperator,
    PlatformOperatorRole,
    PlatformOperatorStatus,
)


async def get_platform_operator(
    session: AsyncSession,
    *,
    external_user_id: str,
) -> PlatformOperator | None:
    result = await session.execute(
        text(
            """
            SELECT id, external_user_id, role::text AS role, status::text AS status
            FROM platform_operators
            WHERE external_user_id = :external_user_id
            LIMIT 1
            """
        ),
        {"external_user_id": external_user_id},
    )
    row = result.mappings().one_or_none()
    if row is None:
        return None
    return PlatformOperator(
        id=row["id"],
        external_user_id=row["external_user_id"],
        role=PlatformOperatorRole(row["role"]),
        status=PlatformOperatorStatus(row["status"]),
    )
