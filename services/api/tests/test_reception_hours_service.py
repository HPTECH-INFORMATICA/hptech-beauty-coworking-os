"""Permanent M2 tests for the BCOS Reception Hours application service."""

from __future__ import annotations

from datetime import UTC, datetime, time
from uuid import UUID, uuid4

import pytest

from bcos_api.reception_hours.domain import (
    InvalidReceptionHours,
    ReceptionHours,
)
from bcos_api.reception_hours.service import (
    InvalidReceptionHoursSet,
    ReceptionHoursInput,
    ReceptionHoursUnitNotFound,
    get_unit_reception_hours,
    replace_unit_reception_hours,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.units.domain import Unit


def owner_context(*, tenant_id: UUID | None = None) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id or uuid4(),
        membership_id=uuid4(),
        external_user_id="identity-owner",
        role=MembershipRole.OWNER,
    )


def unit_for(*, tenant_id: UUID, unit_id: UUID) -> Unit:
    now = datetime.now(UTC)

    return Unit(
        id=unit_id,
        tenant_id=tenant_id,
        name="Batel",
        timezone="America/Sao_Paulo",
        active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_reception_hours_is_scoped_to_context_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    expected_unit_id = unit_id

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        return unit_for(tenant_id=tenant_id, unit_id=unit_id)

    async def fake_list_reception_hours(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> list[ReceptionHours]:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        return []

    monkeypatch.setattr(
        "bcos_api.reception_hours.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.reception_hours.service.list_reception_hours",
        fake_list_reception_hours,
    )

    result = await get_unit_reception_hours(
        object(),  # type: ignore[arg-type]
        context=context,
        unit_id=unit_id,
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_reception_hours_rejects_unit_outside_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()

    async def fake_get_unit(
        session: object,
        **kwargs: object,
    ) -> None:
        del session
        assert kwargs["tenant_id"] == context.tenant_id
        return None

    monkeypatch.setattr(
        "bcos_api.reception_hours.service.get_unit",
        fake_get_unit,
    )

    with pytest.raises(ReceptionHoursUnitNotFound):
        await get_unit_reception_hours(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entries",
    [
        [],
        [
            ReceptionHoursInput(
                day_of_week=day,
                opens_at=time(8, 0),
                closes_at=time(18, 0),
                is_closed=False,
            )
            for day in range(8)
        ],
    ],
)
async def test_replace_rejects_invalid_collection_size(
    monkeypatch: pytest.MonkeyPatch,
    entries: list[ReceptionHoursInput],
) -> None:
    repository_called = False

    async def fake_replace(*args: object, **kwargs: object) -> list[ReceptionHours]:
        nonlocal repository_called
        repository_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.reception_hours.service.replace_reception_hours",
        fake_replace,
    )

    with pytest.raises(InvalidReceptionHoursSet):
        await replace_unit_reception_hours(
            object(),  # type: ignore[arg-type]
            context=owner_context(),
            unit_id=uuid4(),
            entries=entries,
        )

    assert repository_called is False


@pytest.mark.asyncio
async def test_replace_rejects_duplicate_weekdays_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_called = False
    entries = [
        ReceptionHoursInput(0, time(8, 0), time(18, 0), False),
        ReceptionHoursInput(0, time(9, 0), time(17, 0), False),
    ]

    async def fake_replace(*args: object, **kwargs: object) -> list[ReceptionHours]:
        nonlocal repository_called
        repository_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.reception_hours.service.replace_reception_hours",
        fake_replace,
    )

    with pytest.raises(InvalidReceptionHoursSet):
        await replace_unit_reception_hours(
            object(),  # type: ignore[arg-type]
            context=owner_context(),
            unit_id=uuid4(),
            entries=entries,
        )

    assert repository_called is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entry",
    [
        ReceptionHoursInput(7, time(8, 0), time(18, 0), False),
        ReceptionHoursInput(0, None, None, False),
        ReceptionHoursInput(0, time(8, 0), time(18, 0), True),
        ReceptionHoursInput(0, time(18, 0), time(8, 0), False),
    ],
)
async def test_replace_rejects_invalid_day_or_time_semantics(
    monkeypatch: pytest.MonkeyPatch,
    entry: ReceptionHoursInput,
) -> None:
    repository_called = False

    async def fake_replace(*args: object, **kwargs: object) -> list[ReceptionHours]:
        nonlocal repository_called
        repository_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.reception_hours.service.replace_reception_hours",
        fake_replace,
    )

    with pytest.raises(InvalidReceptionHours):
        await replace_unit_reception_hours(
            object(),  # type: ignore[arg-type]
            context=owner_context(),
            unit_id=uuid4(),
            entries=[entry],
        )

    assert repository_called is False


@pytest.mark.asyncio
async def test_replace_uses_authorized_tenant_and_validated_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    expected_unit_id = unit_id
    captured_entries: list[
        tuple[int, time | None, time | None, bool]
    ] = []

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        return unit_for(tenant_id=tenant_id, unit_id=unit_id)

    async def fake_replace(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
        entries: list[tuple[int, time | None, time | None, bool]],
    ) -> list[ReceptionHours]:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        captured_entries.extend(entries)

        return [
            ReceptionHours(
                id=uuid4(),
                tenant_id=tenant_id,
                unit_id=unit_id,
                day_of_week=day_of_week,
                opens_at=opens_at,
                closes_at=closes_at,
                is_closed=is_closed,
            )
            for day_of_week, opens_at, closes_at, is_closed in entries
        ]

    monkeypatch.setattr(
        "bcos_api.reception_hours.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.reception_hours.service.replace_reception_hours",
        fake_replace,
    )

    result = await replace_unit_reception_hours(
        object(),  # type: ignore[arg-type]
        context=context,
        unit_id=unit_id,
        entries=[
            ReceptionHoursInput(
                day_of_week=0,
                opens_at=time(8, 0),
                closes_at=time(18, 0),
                is_closed=False,
            ),
            ReceptionHoursInput(
                day_of_week=6,
                opens_at=None,
                closes_at=None,
                is_closed=True,
            ),
        ],
    )

    assert captured_entries == [
        (0, time(8, 0), time(18, 0), False),
        (6, None, None, True),
    ]
    assert len(result) == 2
    assert result[0].tenant_id == context.tenant_id
    assert result[0].unit_id == unit_id
    assert result[0].day_of_week == 0
    assert result[0].is_closed is False
    assert result[1].day_of_week == 6
    assert result[1].is_closed is True


@pytest.mark.asyncio
async def test_replace_rejects_unit_outside_tenant_before_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    replacement_called = False

    async def fake_get_unit(
        session: object,
        **kwargs: object,
    ) -> None:
        del session
        assert kwargs["tenant_id"] == context.tenant_id
        return None

    async def fake_replace(*args: object, **kwargs: object) -> list[ReceptionHours]:
        nonlocal replacement_called
        replacement_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.reception_hours.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.reception_hours.service.replace_reception_hours",
        fake_replace,
    )

    with pytest.raises(ReceptionHoursUnitNotFound):
        await replace_unit_reception_hours(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
            entries=[
                ReceptionHoursInput(
                    day_of_week=0,
                    opens_at=time(8, 0),
                    closes_at=time(18, 0),
                    is_closed=False,
                )
            ],
        )

    assert replacement_called is False
