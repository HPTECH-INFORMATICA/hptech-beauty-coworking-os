"""Permanent M2 tests for the BCOS Unit application service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.units.domain import InvalidUnit, Unit
from bcos_api.units.service import (
    UnitNotFound,
    create_tenant_unit,
    get_tenant_unit,
    list_tenant_units,
    update_tenant_unit,
)


def owner_context(*, tenant_id: UUID | None = None) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id or uuid4(),
        membership_id=uuid4(),
        external_user_id="identity-owner",
        role=MembershipRole.OWNER,
    )


def unit_for(
    *,
    tenant_id: UUID,
    unit_id: UUID | None = None,
    name: str = "Batel",
    timezone: str = "America/Sao_Paulo",
    active: bool = True,
) -> Unit:
    now = datetime.now(UTC)

    return Unit(
        id=unit_id or uuid4(),
        tenant_id=tenant_id,
        name=name,
        timezone=timezone,
        active=active,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_list_units_uses_only_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    expected = [unit_for(tenant_id=context.tenant_id)]
    captured_tenant_id: UUID | None = None

    async def fake_list_units(
        session: object,
        *,
        tenant_id: UUID,
    ) -> list[Unit]:
        nonlocal captured_tenant_id
        del session

        captured_tenant_id = tenant_id
        return expected

    monkeypatch.setattr(
        "bcos_api.units.service.list_units",
        fake_list_units,
    )

    result = await list_tenant_units(
        object(),  # type: ignore[arg-type]
        context=context,
    )

    assert result == expected
    assert captured_tenant_id == context.tenant_id


@pytest.mark.asyncio
async def test_get_unit_cannot_fall_back_to_another_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    requested_unit_id = uuid4()
    other_tenant_id = uuid4()

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit | None:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == requested_unit_id

        cross_tenant_unit = unit_for(
            tenant_id=other_tenant_id,
            unit_id=requested_unit_id,
        )

        if cross_tenant_unit.tenant_id != tenant_id:
            return None

        return cross_tenant_unit

    monkeypatch.setattr(
        "bcos_api.units.service.get_unit",
        fake_get_unit,
    )

    with pytest.raises(UnitNotFound):
        await get_tenant_unit(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=requested_unit_id,
        )


@pytest.mark.asyncio
async def test_create_unit_uses_context_tenant_and_normalized_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    created_unit_id = uuid4()

    async def fake_create_unit(
        session: object,
        *,
        tenant_id: UUID,
        name: str,
        timezone: str,
        active: bool,
    ) -> Unit:
        del session

        assert tenant_id == context.tenant_id
        assert name == "Batel"
        assert timezone == "America/Sao_Paulo"
        assert active is False

        return unit_for(
            tenant_id=tenant_id,
            unit_id=created_unit_id,
            name=name,
            timezone=timezone,
            active=active,
        )

    monkeypatch.setattr(
        "bcos_api.units.service.create_unit",
        fake_create_unit,
    )

    result = await create_tenant_unit(
        object(),  # type: ignore[arg-type]
        context=context,
        name="  Batel  ",
        timezone="  America/Sao_Paulo  ",
        active=False,
    )

    assert result.id == created_unit_id
    assert result.tenant_id == context.tenant_id
    assert result.name == "Batel"
    assert result.timezone == "America/Sao_Paulo"
    assert result.active is False


@pytest.mark.asyncio
async def test_create_unit_rejects_invalid_iana_timezone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    repository_called = False

    async def fake_create_unit(*args: object, **kwargs: object) -> Unit:
        nonlocal repository_called
        repository_called = True
        raise AssertionError("Repository must not be called.")

    monkeypatch.setattr(
        "bcos_api.units.service.create_unit",
        fake_create_unit,
    )

    with pytest.raises(InvalidUnit):
        await create_tenant_unit(
            object(),  # type: ignore[arg-type]
            context=context,
            name="Batel",
            timezone="Invalid/BCOS-Timezone",
            active=True,
        )

    assert repository_called is False


@pytest.mark.asyncio
async def test_update_unit_is_scoped_to_context_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()

    async def fake_update_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
        name: str,
        timezone: str,
        active: bool,
    ) -> Unit:
        del session

        assert tenant_id == context.tenant_id
        assert name == "Centro Civico"
        assert timezone == "America/Sao_Paulo"
        assert active is True

        return unit_for(
            tenant_id=tenant_id,
            unit_id=unit_id,
            name=name,
            timezone=timezone,
            active=active,
        )

    monkeypatch.setattr(
        "bcos_api.units.service.update_unit",
        fake_update_unit,
    )

    result = await update_tenant_unit(
        object(),  # type: ignore[arg-type]
        context=context,
        unit_id=unit_id,
        name="  Centro Civico  ",
        timezone="America/Sao_Paulo",
        active=True,
    )

    assert result.id == unit_id
    assert result.tenant_id == context.tenant_id


@pytest.mark.asyncio
async def test_update_missing_unit_raises_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()

    async def fake_update_unit(
        session: object,
        **kwargs: object,
    ) -> None:
        del session
        del kwargs
        return None

    monkeypatch.setattr(
        "bcos_api.units.service.update_unit",
        fake_update_unit,
    )

    with pytest.raises(UnitNotFound):
        await update_tenant_unit(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
            name="Batel",
            timezone="America/Sao_Paulo",
            active=True,
        )
