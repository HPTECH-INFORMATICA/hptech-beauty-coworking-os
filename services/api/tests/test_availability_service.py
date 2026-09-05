"""Permanent M3 tests for the BCOS Availability application service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from bcos_api.availability.domain import (
    Availability,
    InvalidAvailabilityInterval,
)
from bcos_api.availability.service import (
    AvailabilityCategoryNotFound,
    AvailabilityResourceNotFound,
    AvailabilityUnitNotFound,
    get_tenant_availability,
)
from bcos_api.resource_categories.domain import ResourceCategory
from bcos_api.resources.domain import Resource, ResourceStatus
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import PermissionDenied
from bcos_api.units.domain import Unit


def owner_context(*, tenant_id: UUID | None = None) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id or uuid4(),
        membership_id=uuid4(),
        external_user_id="identity-owner",
        role=MembershipRole.OWNER,
    )


def professional_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        membership_id=uuid4(),
        external_user_id="identity-professional",
        role=MembershipRole.PROFESSIONAL,
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


def category_for(
    *,
    tenant_id: UUID,
    category_id: UUID,
) -> ResourceCategory:
    return ResourceCategory(
        id=category_id,
        tenant_id=tenant_id,
        name="Sala de Estetica",
        active=True,
    )


def resource_for(
    *,
    tenant_id: UUID,
    resource_id: UUID,
    unit_id: UUID,
    category_id: UUID,
) -> Resource:
    return Resource(
        id=resource_id,
        tenant_id=tenant_id,
        unit_id=unit_id,
        category_id=category_id,
        name="Sala 1",
        operational_status=ResourceStatus.AVAILABLE,
        buffer_before_minutes=10,
        buffer_after_minutes=15,
        active=True,
    )


@pytest.mark.asyncio
async def test_availability_uses_authorized_tenant_and_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    resource_id = uuid4()
    category_id = uuid4()
    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(hours=1)
    expected = [
        Availability(
            resource_id=resource_id,
            available=False,
            reason="BOOKING",
        )
    ]

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

    async def fake_get_resource(
        session: object,
        *,
        tenant_id: UUID,
        resource_id: UUID,
    ) -> Resource:
        del session
        assert tenant_id == context.tenant_id
        assert resource_id == expected_resource_id
        return resource_for(
            tenant_id=tenant_id,
            resource_id=resource_id,
            unit_id=expected_unit_id,
            category_id=expected_category_id,
        )

    async def fake_get_category(
        session: object,
        *,
        tenant_id: UUID,
        category_id: UUID,
    ) -> ResourceCategory:
        del session
        assert tenant_id == context.tenant_id
        assert category_id == expected_category_id
        return category_for(
            tenant_id=tenant_id,
            category_id=category_id,
        )

    async def fake_list_availability(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        resource_id: UUID | None,
        category_id: UUID | None,
    ) -> list[Availability]:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        assert starts_at == expected_starts_at
        assert ends_at == expected_ends_at
        assert resource_id == expected_resource_id
        assert category_id == expected_category_id
        return expected

    expected_unit_id = unit_id
    expected_resource_id = resource_id
    expected_category_id = category_id
    expected_starts_at = starts_at
    expected_ends_at = ends_at

    monkeypatch.setattr(
        "bcos_api.availability.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.get_resource",
        fake_get_resource,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.list_resource_availability",
        fake_list_availability,
    )

    result = await get_tenant_availability(
        object(),  # type: ignore[arg-type]
        context=context,
        unit_id=unit_id,
        starts_at=starts_at,
        ends_at=ends_at,
        resource_id=resource_id,
        category_id=category_id,
    )

    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("starts_at", "ends_at"),
    [
        (
            datetime(2026, 9, 5, 12, 0),
            datetime(2026, 9, 5, 13, 0, tzinfo=UTC),
        ),
        (
            datetime(2026, 9, 5, 12, 0, tzinfo=UTC),
            datetime(2026, 9, 5, 13, 0),
        ),
        (
            datetime(2026, 9, 5, 12, 0, tzinfo=UTC),
            datetime(2026, 9, 5, 12, 0, tzinfo=UTC),
        ),
        (
            datetime(2026, 9, 5, 13, 0, tzinfo=UTC),
            datetime(2026, 9, 5, 12, 0, tzinfo=UTC),
        ),
    ],
)
async def test_invalid_interval_is_rejected_before_repository_access(
    monkeypatch: pytest.MonkeyPatch,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    context = owner_context()
    unit_lookup_called = False

    async def fake_get_unit(*args: object, **kwargs: object) -> None:
        nonlocal unit_lookup_called
        unit_lookup_called = True
        return None

    monkeypatch.setattr(
        "bcos_api.availability.service.get_unit",
        fake_get_unit,
    )

    with pytest.raises(InvalidAvailabilityInterval):
        await get_tenant_availability(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
            starts_at=starts_at,
            ends_at=ends_at,
        )

    assert unit_lookup_called is False


@pytest.mark.asyncio
async def test_missing_unit_stops_availability_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    availability_called = False

    async def fake_get_unit(*args: object, **kwargs: object) -> None:
        return None

    async def fake_list(*args: object, **kwargs: object) -> list[Availability]:
        nonlocal availability_called
        availability_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.availability.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.list_resource_availability",
        fake_list,
    )

    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)

    with pytest.raises(AvailabilityUnitNotFound):
        await get_tenant_availability(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
        )

    assert availability_called is False


@pytest.mark.asyncio
async def test_resource_must_belong_to_requested_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    requested_unit_id = uuid4()
    resource_id = uuid4()
    category_id = uuid4()
    availability_called = False

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        return unit_for(tenant_id=tenant_id, unit_id=unit_id)

    async def fake_get_resource(
        session: object,
        *,
        tenant_id: UUID,
        resource_id: UUID,
    ) -> Resource:
        del session
        return resource_for(
            tenant_id=tenant_id,
            resource_id=resource_id,
            unit_id=uuid4(),
            category_id=category_id,
        )

    async def fake_list(*args: object, **kwargs: object) -> list[Availability]:
        nonlocal availability_called
        availability_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.availability.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.get_resource",
        fake_get_resource,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.list_resource_availability",
        fake_list,
    )

    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)

    with pytest.raises(AvailabilityResourceNotFound):
        await get_tenant_availability(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=requested_unit_id,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            resource_id=resource_id,
        )

    assert availability_called is False


@pytest.mark.asyncio
async def test_resource_must_match_requested_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    resource_id = uuid4()
    resource_category_id = uuid4()
    requested_category_id = uuid4()
    category_lookup_called = False
    availability_called = False

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        return unit_for(tenant_id=tenant_id, unit_id=unit_id)

    async def fake_get_resource(
        session: object,
        *,
        tenant_id: UUID,
        resource_id: UUID,
    ) -> Resource:
        del session
        return resource_for(
            tenant_id=tenant_id,
            resource_id=resource_id,
            unit_id=unit_id,
            category_id=resource_category_id,
        )

    async def fake_get_category(
        *args: object,
        **kwargs: object,
    ) -> ResourceCategory | None:
        nonlocal category_lookup_called
        category_lookup_called = True
        return None

    async def fake_list(*args: object, **kwargs: object) -> list[Availability]:
        nonlocal availability_called
        availability_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.availability.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.get_resource",
        fake_get_resource,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.list_resource_availability",
        fake_list,
    )

    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)

    with pytest.raises(AvailabilityResourceNotFound):
        await get_tenant_availability(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=unit_id,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            resource_id=resource_id,
            category_id=requested_category_id,
        )

    assert category_lookup_called is False
    assert availability_called is False


@pytest.mark.asyncio
async def test_missing_category_stops_availability_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    availability_called = False

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        return unit_for(tenant_id=tenant_id, unit_id=unit_id)

    async def fake_get_category(*args: object, **kwargs: object) -> None:
        return None

    async def fake_list(*args: object, **kwargs: object) -> list[Availability]:
        nonlocal availability_called
        availability_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.availability.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.availability.service.list_resource_availability",
        fake_list,
    )

    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)

    with pytest.raises(AvailabilityCategoryNotFound):
        await get_tenant_availability(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=unit_id,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            category_id=uuid4(),
        )

    assert availability_called is False


@pytest.mark.asyncio
async def test_professional_role_is_denied_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = professional_context()
    unit_lookup_called = False

    async def fake_get_unit(*args: object, **kwargs: object) -> None:
        nonlocal unit_lookup_called
        unit_lookup_called = True
        return None

    monkeypatch.setattr(
        "bcos_api.availability.service.get_unit",
        fake_get_unit,
    )

    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)

    with pytest.raises(PermissionDenied):
        await get_tenant_availability(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
        )

    assert unit_lookup_called is False
