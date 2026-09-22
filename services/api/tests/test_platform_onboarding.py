"""Tests for HPTECH contracting-company onboarding service."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.platform.domain import PlatformContext, PlatformOperatorRole
from bcos_api.platform.onboarding.service import onboard_contracting_tenant


@pytest.mark.asyncio
async def test_platform_admin_onboards_pending_tenant_with_invited_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_create(session: object, **kwargs: object):
        del session
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "bcos_api.platform.onboarding.service.create_contracting_tenant",
        fake_create,
    )

    context = PlatformContext(
        operator_id=uuid4(),
        external_user_id="hptech-admin",
        role=PlatformOperatorRole.PLATFORM_ADMIN,
    )

    await onboard_contracting_tenant(
        cast(AsyncSession, object()),
        context=context,
        name=" La Beauté ",
        slug=" la-beaute ",
        legal_name="La Beauté Coworking Ltda",
        trade_name="La Beauté",
        tax_id=" 123 ",
        email=" contato@example.com ",
        phone=" 41999999999 ",
        owner_external_user_id=" owner-identity ",
    )

    assert captured["name"] == "La Beauté"
    assert captured["slug"] == "la-beaute"
    assert captured["tax_id"] == "123"
    assert captured["email"] == "contato@example.com"
    assert captured["owner_external_user_id"] == "owner-identity"
