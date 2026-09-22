"""Authorized HPTECH platform context resolution."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.platform.domain import PlatformAccessDenied, PlatformContext
from bcos_api.platform.repository import get_platform_operator


async def resolve_platform_context(
    session: AsyncSession,
    *,
    external_user_id: str,
) -> PlatformContext:
    operator = await get_platform_operator(
        session,
        external_user_id=external_user_id,
    )
    if operator is None or not operator.is_active:
        raise PlatformAccessDenied(
            "Authenticated identity does not have active HPTECH platform access."
        )
    return PlatformContext(
        operator_id=operator.id,
        external_user_id=operator.external_user_id,
        role=operator.role,
    )
