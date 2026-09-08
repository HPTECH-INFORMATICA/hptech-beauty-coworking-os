"""Tests for BCOS tenant context authorization."""

from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.context import (
    TenantAccessDenied,
    resolve_tenant_context,
)
from bcos_api.tenancy.membership import (
    MembershipRole,
    MembershipStatus,
    TenantMembership,
)


@pytest.mark.asyncio
async def test_active_membership_resolves_tenant_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()
    membership_id = uuid4()
    external_user_id = "identity-active"

    async def fake_get_membership(
        session: object,
        *,
        tenant_id: UUID,
        external_user_id: str,
    ) -> TenantMembership:
        del session

        return TenantMembership(
            id=membership_id,
            tenant_id=tenant_id,
            external_user_id=external_user_id,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )

    monkeypatch.setattr(
        "bcos_api.tenancy.context.get_membership",
        fake_get_membership,
    )

    context = await resolve_tenant_context(
        cast(AsyncSession, object()),
        tenant_id=tenant_id,
        external_user_id=external_user_id,
    )

    assert context.tenant_id == tenant_id
    assert context.membership_id == membership_id
    assert context.external_user_id == external_user_id
    assert context.role is MembershipRole.OWNER


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        MembershipStatus.INVITED,
        MembershipStatus.INACTIVE,
    ],
)
async def test_non_active_membership_is_denied(
    monkeypatch: pytest.MonkeyPatch,
    status: MembershipStatus,
) -> None:
    tenant_id = uuid4()

    async def fake_get_membership(
        session: object,
        *,
        tenant_id: UUID,
        external_user_id: str,
    ) -> TenantMembership:
        del session

        return TenantMembership(
            id=uuid4(),
            tenant_id=tenant_id,
            external_user_id=external_user_id,
            role=MembershipRole.PROFESSIONAL,
            status=status,
        )

    monkeypatch.setattr(
        "bcos_api.tenancy.context.get_membership",
        fake_get_membership,
    )

    with pytest.raises(TenantAccessDenied):
        await resolve_tenant_context(
            cast(AsyncSession, object()),
            tenant_id=tenant_id,
            external_user_id="identity-not-active",
        )


@pytest.mark.asyncio
async def test_missing_membership_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()

    async def fake_get_membership(
        session: object,
        *,
        tenant_id: UUID,
        external_user_id: str,
    ) -> None:
        del session
        del tenant_id
        del external_user_id

        return None

    monkeypatch.setattr(
        "bcos_api.tenancy.context.get_membership",
        fake_get_membership,
    )

    with pytest.raises(TenantAccessDenied):
        await resolve_tenant_context(
            cast(AsyncSession, object()),
            tenant_id=tenant_id,
            external_user_id="identity-missing",
        )


@pytest.mark.asyncio
async def test_cross_tenant_membership_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_tenant_id = uuid4()
    authorized_tenant_id = uuid4()
    external_user_id = "identity-cross-tenant"

    async def fake_get_membership(
        session: object,
        *,
        tenant_id: UUID,
        external_user_id: str,
    ) -> TenantMembership | None:
        del session

        if (
            tenant_id == authorized_tenant_id
            and external_user_id == "identity-cross-tenant"
        ):
            return TenantMembership(
                id=uuid4(),
                tenant_id=authorized_tenant_id,
                external_user_id=external_user_id,
                role=MembershipRole.OWNER,
                status=MembershipStatus.ACTIVE,
            )

        return None

    monkeypatch.setattr(
        "bcos_api.tenancy.context.get_membership",
        fake_get_membership,
    )

    with pytest.raises(TenantAccessDenied):
        await resolve_tenant_context(
            cast(AsyncSession, object()),
            tenant_id=requested_tenant_id,
            external_user_id=external_user_id,
        )
