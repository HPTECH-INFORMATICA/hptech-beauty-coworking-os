"""Tests for HPTECH platform authority isolation."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.platform.context import resolve_platform_context
from bcos_api.platform.domain import (
    PlatformAccessDenied,
    PlatformOperator,
    PlatformOperatorRole,
    PlatformOperatorStatus,
)


@pytest.mark.asyncio
async def test_active_platform_admin_resolves_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator_id = uuid4()

    async def fake_get_operator(
        session: object,
        *,
        external_user_id: str,
    ) -> PlatformOperator:
        del session
        return PlatformOperator(
            id=operator_id,
            external_user_id=external_user_id,
            role=PlatformOperatorRole.PLATFORM_ADMIN,
            status=PlatformOperatorStatus.ACTIVE,
        )

    monkeypatch.setattr(
        "bcos_api.platform.context.get_platform_operator",
        fake_get_operator,
    )

    context = await resolve_platform_context(
        cast(AsyncSession, object()),
        external_user_id="hptech-admin",
    )

    assert context.operator_id == operator_id
    assert context.external_user_id == "hptech-admin"
    assert context.role is PlatformOperatorRole.PLATFORM_ADMIN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operator",
    [
        None,
        PlatformOperator(
            id=uuid4(),
            external_user_id="disabled-admin",
            role=PlatformOperatorRole.PLATFORM_ADMIN,
            status=PlatformOperatorStatus.INACTIVE,
        ),
    ],
)
async def test_missing_or_inactive_platform_operator_is_denied(
    monkeypatch: pytest.MonkeyPatch,
    operator: PlatformOperator | None,
) -> None:
    async def fake_get_operator(
        session: object,
        *,
        external_user_id: str,
    ) -> PlatformOperator | None:
        del session, external_user_id
        return operator

    monkeypatch.setattr(
        "bcos_api.platform.context.get_platform_operator",
        fake_get_operator,
    )

    with pytest.raises(PlatformAccessDenied):
        await resolve_platform_context(
            cast(AsyncSession, object()),
            external_user_id="identity",
        )
