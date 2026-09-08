"""Tests for BCOS booking-series application service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from bcos_api.bookings.domain import Booking, BookingStatus
from bcos_api.bookings.series_domain import BookingSeries
from bcos_api.bookings.service import (
    BookingSeriesConflict,
    create_booking_series,
)
from bcos_api.professionals.domain import (
    Professional,
    ProfessionalStatus,
)
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


def resource_for(
    *,
    tenant_id: UUID,
    resource_id: UUID,
    unit_id: UUID,
    category_id: UUID,
    buffer_before_minutes: int = 10,
    buffer_after_minutes: int = 15,
) -> Resource:
    return Resource(
        id=resource_id,
        tenant_id=tenant_id,
        unit_id=unit_id,
        category_id=category_id,
        name="Sala 1",
        operational_status=ResourceStatus.AVAILABLE,
        buffer_before_minutes=buffer_before_minutes,
        buffer_after_minutes=buffer_after_minutes,
        active=True,
    )


def professional_for(
    *,
    tenant_id: UUID,
    professional_id: UUID,
) -> Professional:
    return Professional(
        id=professional_id,
        tenant_id=tenant_id,
        external_user_id=None,
        name="Cristiana Valente",
        email="contato@example.com",
        phone="41999999999",
        status=ProfessionalStatus.ACTIVE,
    )


class RecordingPricingProducer:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    async def produce(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        return {
            "source": "test",
            "occurrence": len(self.requests),
        }


@pytest.mark.asyncio
async def test_create_series_validates_prices_all_occurrences_before_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    resource_id = uuid4()
    category_id = uuid4()
    professional_id = uuid4()
    start = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    pricing = RecordingPricingProducer()

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        return unit_for(
            tenant_id=tenant_id,
            unit_id=unit_id,
        )

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
            category_id=category_id,
        )

    async def fake_get_professional(
        session: object,
        *,
        tenant_id: UUID,
        professional_id: UUID,
    ) -> Professional:
        del session
        assert tenant_id == context.tenant_id
        assert professional_id == expected_professional_id
        return professional_for(
            tenant_id=tenant_id,
            professional_id=professional_id,
        )

    async def fake_conflict(
        session: object,
        *,
        tenant_id: UUID,
        resource_id: UUID,
        periods: list[tuple[datetime, datetime]],
    ) -> bool:
        del session
        assert tenant_id == context.tenant_id
        assert resource_id == expected_resource_id
        assert len(periods) == 3

        assert periods[0] == (
            start - timedelta(minutes=10),
            start + timedelta(hours=1, minutes=15),
        )
        return False

    persist_called = False

    async def fake_persist(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
        resource_id: UUID,
        professional_id: UUID,
        rrule: str,
        timezone: str,
        starts_at: datetime,
        ends_at: datetime,
        buffer_before_minutes: int,
        buffer_after_minutes: int,
        notes: str | None,
        occurrences: list[
            tuple[datetime, datetime, dict[str, Any]]
        ],
    ) -> tuple[BookingSeries, list[Booking]]:
        nonlocal persist_called
        del session

        persist_called = True

        # Critical ordering invariant:
        # every snapshot must exist before the first persistence call.
        assert len(pricing.requests) == 3
        assert len(occurrences) == 3

        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        assert resource_id == expected_resource_id
        assert professional_id == expected_professional_id
        assert rrule == "FREQ=DAILY;COUNT=3"
        assert timezone == "America/Sao_Paulo"
        assert starts_at == start
        assert ends_at == start + timedelta(days=2, hours=1)
        assert buffer_before_minutes == 10
        assert buffer_after_minutes == 15
        assert notes == "Serie de teste"

        series_id = uuid4()

        series = BookingSeries(
            id=series_id,
            tenant_id=tenant_id,
            professional_id=professional_id,
            rrule=rrule,
            timezone=timezone,
            starts_at=starts_at,
            ends_at=ends_at,
            cancelled_at=None,
        )

        bookings = [
            Booking(
                id=uuid4(),
                tenant_id=tenant_id,
                unit_id=unit_id,
                resource_id=resource_id,
                professional_id=professional_id,
                series_id=series_id,
                status=BookingStatus.PENDING,
                starts_at=occurrence_start,
                ends_at=occurrence_end,
                buffer_before_minutes=buffer_before_minutes,
                buffer_after_minutes=buffer_after_minutes,
                pricing_snapshot=snapshot,
                notes=notes,
                confirmed_at=None,
                cancelled_at=None,
                completed_at=None,
            )
            for occurrence_start, occurrence_end, snapshot in occurrences
        ]

        return series, bookings

    expected_unit_id = unit_id
    expected_resource_id = resource_id
    expected_professional_id = professional_id

    monkeypatch.setattr(
        "bcos_api.bookings.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.get_resource",
        fake_get_resource,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.get_professional",
        fake_get_professional,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.has_active_occupancy_conflict",
        fake_conflict,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.persist_create_booking_series",
        fake_persist,
    )

    series, bookings = await create_booking_series(
        object(),  # type: ignore[arg-type]
        context=context,
        unit_id=unit_id,
        resource_id=resource_id,
        professional_id=professional_id,
        starts_at=start,
        duration_minutes=60,
        rrule="FREQ=DAILY;COUNT=3",
        timezone="America/Sao_Paulo",
        notes="Serie de teste",
        pricing_snapshot_producer=pricing,
    )

    assert persist_called is True
    assert series.tenant_id == context.tenant_id
    assert len(bookings) == 3
    assert all(
        booking.status is BookingStatus.PENDING
        for booking in bookings
    )


@pytest.mark.asyncio
async def test_series_conflict_stops_before_pricing_and_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    resource_id = uuid4()
    category_id = uuid4()
    professional_id = uuid4()
    pricing = RecordingPricingProducer()

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        return unit_for(
            tenant_id=tenant_id,
            unit_id=unit_id,
        )

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
            category_id=category_id,
        )

    async def fake_get_professional(
        session: object,
        *,
        tenant_id: UUID,
        professional_id: UUID,
    ) -> Professional:
        del session
        return professional_for(
            tenant_id=tenant_id,
            professional_id=professional_id,
        )

    async def fake_conflict(
        *args: object,
        **kwargs: object,
    ) -> bool:
        return True

    persist_called = False

    async def fake_persist(
        *args: object,
        **kwargs: object,
    ) -> tuple[BookingSeries, list[Booking]]:
        nonlocal persist_called
        persist_called = True
        raise AssertionError("Persistence must not be called.")

    monkeypatch.setattr(
        "bcos_api.bookings.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.get_resource",
        fake_get_resource,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.get_professional",
        fake_get_professional,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.has_active_occupancy_conflict",
        fake_conflict,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.persist_create_booking_series",
        fake_persist,
    )

    with pytest.raises(BookingSeriesConflict):
        await create_booking_series(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=unit_id,
            resource_id=resource_id,
            professional_id=professional_id,
            starts_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
            duration_minutes=60,
            rrule="FREQ=DAILY;COUNT=2",
            timezone="America/Sao_Paulo",
            notes=None,
            pricing_snapshot_producer=pricing,
        )

    assert pricing.requests == []
    assert persist_called is False


@pytest.mark.asyncio
async def test_professional_role_is_denied_before_series_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = professional_context()
    relation_called = False
    persist_called = False

    async def fake_get_unit(
        *args: object,
        **kwargs: object,
    ) -> None:
        nonlocal relation_called
        relation_called = True
        return None

    async def fake_persist(
        *args: object,
        **kwargs: object,
    ) -> tuple[BookingSeries, list[Booking]]:
        nonlocal persist_called
        persist_called = True
        raise AssertionError("Persistence must not be called.")

    monkeypatch.setattr(
        "bcos_api.bookings.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.persist_create_booking_series",
        fake_persist,
    )

    with pytest.raises(PermissionDenied):
        await create_booking_series(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
            resource_id=uuid4(),
            professional_id=uuid4(),
            starts_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
            duration_minutes=60,
            rrule="FREQ=DAILY;COUNT=2",
            timezone="America/Sao_Paulo",
            notes=None,
            pricing_snapshot_producer=RecordingPricingProducer(),
        )

    assert relation_called is False
    assert persist_called is False


@pytest.mark.asyncio
async def test_series_pricing_failure_stops_before_any_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    resource_id = uuid4()
    category_id = uuid4()
    professional_id = uuid4()
    pricing_calls = 0
    persist_called = False

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        return unit_for(
            tenant_id=tenant_id,
            unit_id=unit_id,
        )

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
            category_id=category_id,
        )

    async def fake_get_professional(
        session: object,
        *,
        tenant_id: UUID,
        professional_id: UUID,
    ) -> Professional:
        del session
        return professional_for(
            tenant_id=tenant_id,
            professional_id=professional_id,
        )

    async def fake_conflict(
        *args: object,
        **kwargs: object,
    ) -> bool:
        return False

    class FailingPricingProducer:
        async def produce(self, request: Any) -> dict[str, Any]:
            nonlocal pricing_calls
            del request

            pricing_calls += 1

            if pricing_calls == 2:
                return {}

            return {
                "source": "test",
                "occurrence": pricing_calls,
            }

    async def fake_persist(
        *args: object,
        **kwargs: object,
    ) -> tuple[BookingSeries, list[Booking]]:
        nonlocal persist_called
        persist_called = True
        raise AssertionError("Persistence must not be called.")

    monkeypatch.setattr(
        "bcos_api.bookings.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.get_resource",
        fake_get_resource,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.get_professional",
        fake_get_professional,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.has_active_occupancy_conflict",
        fake_conflict,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.persist_create_booking_series",
        fake_persist,
    )

    from bcos_api.bookings.series_domain import InvalidBookingSeries

    with pytest.raises(
        InvalidBookingSeries,
        match="Pricing snapshot must be a non-empty object",
    ):
        await create_booking_series(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=unit_id,
            resource_id=resource_id,
            professional_id=professional_id,
            starts_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
            duration_minutes=60,
            rrule="FREQ=DAILY;COUNT=3",
            timezone="America/Sao_Paulo",
            notes=None,
            pricing_snapshot_producer=FailingPricingProducer(),
        )

    assert pricing_calls == 2
    assert persist_called is False


@pytest.mark.asyncio
async def test_cancel_series_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bcos_api.bookings.service import cancel_booking_series

    context = owner_context()
    series_id = uuid4()
    starts_at = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    cancelled_at = datetime(2026, 9, 5, 18, 0, tzinfo=UTC)

    existing = BookingSeries(
        id=series_id,
        tenant_id=context.tenant_id,
        professional_id=uuid4(),
        rrule="FREQ=DAILY;COUNT=3",
        timezone="America/Sao_Paulo",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(days=2, hours=1),
        cancelled_at=None,
    )
    cancelled = BookingSeries(
        id=existing.id,
        tenant_id=existing.tenant_id,
        professional_id=existing.professional_id,
        rrule=existing.rrule,
        timezone=existing.timezone,
        starts_at=existing.starts_at,
        ends_at=existing.ends_at,
        cancelled_at=cancelled_at,
    )

    persist_called = False

    async def fake_get_series(
        *args: object,
        **kwargs: object,
    ) -> BookingSeries:
        return existing

    async def fake_cancel_series(
        *args: object,
        **kwargs: object,
    ) -> BookingSeries:
        nonlocal persist_called
        persist_called = True
        return cancelled

    monkeypatch.setattr(
        "bcos_api.bookings.service.repository_get_booking_series",
        fake_get_series,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.persist_cancel_booking_series",
        fake_cancel_series,
    )

    result = await cancel_booking_series(
        object(),  # type: ignore[arg-type]
        context=context,
        series_id=series_id,
    )

    assert persist_called is True
    assert result == cancelled
    assert result.cancelled_at == cancelled_at


@pytest.mark.asyncio
async def test_cancel_series_not_found_stops_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bcos_api.bookings.service import (
        BookingSeriesNotFound,
        cancel_booking_series,
    )

    context = owner_context()
    persist_called = False

    async def fake_get_series(
        *args: object,
        **kwargs: object,
    ) -> None:
        return None

    async def fake_cancel_series(
        *args: object,
        **kwargs: object,
    ) -> BookingSeries:
        nonlocal persist_called
        persist_called = True
        raise AssertionError("Persistence must not be called.")

    monkeypatch.setattr(
        "bcos_api.bookings.service.repository_get_booking_series",
        fake_get_series,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.persist_cancel_booking_series",
        fake_cancel_series,
    )

    with pytest.raises(
        BookingSeriesNotFound,
        match="Booking series not found",
    ):
        await cancel_booking_series(
            object(),  # type: ignore[arg-type]
            context=context,
            series_id=uuid4(),
        )

    assert persist_called is False


@pytest.mark.asyncio
async def test_cancel_series_already_cancelled_stops_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bcos_api.bookings.service import (
        BookingSeriesConflict,
        cancel_booking_series,
    )

    context = owner_context()
    series_id = uuid4()
    starts_at = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)

    existing = BookingSeries(
        id=series_id,
        tenant_id=context.tenant_id,
        professional_id=uuid4(),
        rrule="FREQ=DAILY;COUNT=3",
        timezone="America/Sao_Paulo",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(days=2, hours=1),
        cancelled_at=datetime(2026, 9, 5, 18, 0, tzinfo=UTC),
    )
    persist_called = False

    async def fake_get_series(
        *args: object,
        **kwargs: object,
    ) -> BookingSeries:
        return existing

    async def fake_cancel_series(
        *args: object,
        **kwargs: object,
    ) -> BookingSeries:
        nonlocal persist_called
        persist_called = True
        raise AssertionError("Persistence must not be called.")

    monkeypatch.setattr(
        "bcos_api.bookings.service.repository_get_booking_series",
        fake_get_series,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.persist_cancel_booking_series",
        fake_cancel_series,
    )

    with pytest.raises(
        BookingSeriesConflict,
        match="already cancelled",
    ):
        await cancel_booking_series(
            object(),  # type: ignore[arg-type]
            context=context,
            series_id=series_id,
        )

    assert persist_called is False


@pytest.mark.asyncio
async def test_cancel_series_repository_failure_becomes_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bcos_api.bookings.service import (
        BookingSeriesConflict,
        cancel_booking_series,
    )

    context = owner_context()
    series_id = uuid4()
    starts_at = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)

    existing = BookingSeries(
        id=series_id,
        tenant_id=context.tenant_id,
        professional_id=uuid4(),
        rrule="FREQ=DAILY;COUNT=3",
        timezone="America/Sao_Paulo",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(days=2, hours=1),
        cancelled_at=None,
    )

    async def fake_get_series(
        *args: object,
        **kwargs: object,
    ) -> BookingSeries:
        return existing

    async def fake_cancel_series(
        *args: object,
        **kwargs: object,
    ) -> None:
        return None

    monkeypatch.setattr(
        "bcos_api.bookings.service.repository_get_booking_series",
        fake_get_series,
    )
    monkeypatch.setattr(
        "bcos_api.bookings.service.persist_cancel_booking_series",
        fake_cancel_series,
    )

    with pytest.raises(
        BookingSeriesConflict,
        match="could not be cancelled",
    ):
        await cancel_booking_series(
            object(),  # type: ignore[arg-type]
            context=context,
            series_id=series_id,
        )
