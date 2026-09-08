"""Tests for BCOS Usage application service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from bcos_api.bookings.domain import Booking, BookingStatus
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.usages.domain import InvalidUsage, Usage, UsageStatus
from bcos_api.usages.service import (
    UsageConflict,
    UsageNotFound,
    check_in,
    check_out,
)


def owner_context(*, tenant_id: UUID | None = None) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id or uuid4(),
        membership_id=uuid4(),
        external_user_id="identity:test-owner",
        role=MembershipRole.OWNER,
    )


def booking_for(
    *,
    tenant_id: UUID,
    booking_id: UUID,
    resource_id: UUID,
    professional_id: UUID,
    status: BookingStatus = BookingStatus.CONFIRMED,
) -> Booking:
    return Booking(
        id=booking_id,
        tenant_id=tenant_id,
        unit_id=uuid4(),
        resource_id=resource_id,
        professional_id=professional_id,
        series_id=None,
        status=status,
        starts_at=datetime(2026, 9, 10, 13, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 10, 14, 0, tzinfo=UTC),
        buffer_before_minutes=10,
        buffer_after_minutes=15,
        pricing_snapshot={"source": "test"},
        notes=None,
        confirmed_at=(
            datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
            if status is BookingStatus.CONFIRMED
            else None
        ),
        cancelled_at=None,
        completed_at=None,
    )


def usage_for(
    *,
    tenant_id: UUID,
    booking_id: UUID,
    resource_id: UUID,
    professional_id: UUID,
    status: UsageStatus = UsageStatus.CHECKED_IN,
    checked_in_at: datetime | None = None,
    checked_out_at: datetime | None = None,
) -> Usage:
    return Usage(
        id=uuid4(),
        tenant_id=tenant_id,
        booking_id=booking_id,
        resource_id=resource_id,
        professional_id=professional_id,
        status=status,
        checked_in_at=checked_in_at,
        checked_out_at=checked_out_at,
    )


@pytest.mark.asyncio
async def test_check_in_creates_usage_from_confirmed_booking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    booking_id = uuid4()
    resource_id = uuid4()
    professional_id = uuid4()
    checked_in_at = datetime(2026, 9, 10, 13, 5, tzinfo=UTC)
    session = object()

    booking = booking_for(
        tenant_id=context.tenant_id,
        booking_id=booking_id,
        resource_id=resource_id,
        professional_id=professional_id,
    )
    expected_usage = usage_for(
        tenant_id=context.tenant_id,
        booking_id=booking_id,
        resource_id=resource_id,
        professional_id=professional_id,
        checked_in_at=checked_in_at,
    )

    async def fake_get_booking(
        received_session: object,
        *,
        tenant_id: UUID,
        booking_id: UUID,
    ) -> Booking:
        assert received_session is session
        assert tenant_id == context.tenant_id
        assert booking_id == expected_booking_id
        return booking

    async def fake_get_usage_by_booking(
        received_session: object,
        *,
        tenant_id: UUID,
        booking_id: UUID,
    ) -> None:
        assert received_session is session
        assert tenant_id == context.tenant_id
        assert booking_id == expected_booking_id
        return None

    async def fake_create_checked_in_usage(
        received_session: object,
        *,
        tenant_id: UUID,
        booking_id: UUID,
        checked_in_at: datetime,
    ) -> Usage:
        assert received_session is session
        assert tenant_id == context.tenant_id
        assert booking_id == expected_booking_id
        assert checked_in_at == expected_checked_in_at
        return expected_usage

    expected_booking_id = booking_id
    expected_checked_in_at = checked_in_at

    monkeypatch.setattr(
        "bcos_api.usages.service.get_booking",
        fake_get_booking,
    )
    monkeypatch.setattr(
        "bcos_api.usages.service.get_usage_by_booking",
        fake_get_usage_by_booking,
    )
    monkeypatch.setattr(
        "bcos_api.usages.service.create_checked_in_usage",
        fake_create_checked_in_usage,
    )

    result = await check_in(
        session,  # type: ignore[arg-type]
        context=context,
        booking_id=booking_id,
        checked_in_at=checked_in_at,
    )

    assert result is expected_usage


@pytest.mark.asyncio
async def test_check_in_missing_booking_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    booking_id = uuid4()
    session = object()

    async def fake_get_booking(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "bcos_api.usages.service.get_booking",
        fake_get_booking,
    )

    with pytest.raises(UsageNotFound):
        await check_in(
            session,  # type: ignore[arg-type]
            context=context,
            booking_id=booking_id,
        )


@pytest.mark.asyncio
async def test_check_in_rejects_non_confirmed_booking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    booking_id = uuid4()
    session = object()

    booking = booking_for(
        tenant_id=context.tenant_id,
        booking_id=booking_id,
        resource_id=uuid4(),
        professional_id=uuid4(),
        status=BookingStatus.PENDING,
    )

    async def fake_get_booking(*args, **kwargs):
        return booking

    monkeypatch.setattr(
        "bcos_api.usages.service.get_booking",
        fake_get_booking,
    )

    with pytest.raises(UsageConflict):
        await check_in(
            session,  # type: ignore[arg-type]
            context=context,
            booking_id=booking_id,
        )


@pytest.mark.asyncio
async def test_check_in_rejects_existing_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    booking_id = uuid4()
    resource_id = uuid4()
    professional_id = uuid4()
    session = object()

    booking = booking_for(
        tenant_id=context.tenant_id,
        booking_id=booking_id,
        resource_id=resource_id,
        professional_id=professional_id,
    )
    existing_usage = usage_for(
        tenant_id=context.tenant_id,
        booking_id=booking_id,
        resource_id=resource_id,
        professional_id=professional_id,
        checked_in_at=datetime(2026, 9, 10, 13, 5, tzinfo=UTC),
    )

    async def fake_get_booking(*args, **kwargs):
        return booking

    async def fake_get_usage_by_booking(*args, **kwargs):
        return existing_usage

    monkeypatch.setattr(
        "bcos_api.usages.service.get_booking",
        fake_get_booking,
    )
    monkeypatch.setattr(
        "bcos_api.usages.service.get_usage_by_booking",
        fake_get_usage_by_booking,
    )

    with pytest.raises(UsageConflict):
        await check_in(
            session,  # type: ignore[arg-type]
            context=context,
            booking_id=booking_id,
        )


@pytest.mark.asyncio
async def test_check_out_completes_checked_in_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    booking_id = uuid4()
    resource_id = uuid4()
    professional_id = uuid4()
    checked_in_at = datetime(2026, 9, 10, 13, 5, tzinfo=UTC)
    checked_out_at = datetime(2026, 9, 10, 14, 10, tzinfo=UTC)
    session = object()

    usage = usage_for(
        tenant_id=context.tenant_id,
        booking_id=booking_id,
        resource_id=resource_id,
        professional_id=professional_id,
        checked_in_at=checked_in_at,
    )
    completed = Usage(
        id=usage.id,
        tenant_id=usage.tenant_id,
        booking_id=usage.booking_id,
        resource_id=usage.resource_id,
        professional_id=usage.professional_id,
        status=UsageStatus.COMPLETED,
        checked_in_at=checked_in_at,
        checked_out_at=checked_out_at,
    )

    async def fake_get_usage(
        received_session: object,
        *,
        tenant_id: UUID,
        usage_id: UUID,
    ) -> Usage:
        assert received_session is session
        assert tenant_id == context.tenant_id
        assert usage_id == usage.id
        return usage

    async def fake_complete_usage_with_outbox(
        received_session: object,
        *,
        tenant_id: UUID,
        usage_id: UUID,
        checked_out_at: datetime,
    ) -> Usage:
        assert received_session is session
        assert tenant_id == context.tenant_id
        assert usage_id == usage.id
        assert checked_out_at == expected_checked_out_at
        return completed

    expected_checked_out_at = checked_out_at

    monkeypatch.setattr(
        "bcos_api.usages.service.get_usage",
        fake_get_usage,
    )
    monkeypatch.setattr(
        "bcos_api.usages.service.complete_usage_with_outbox",
        fake_complete_usage_with_outbox,
    )

    result = await check_out(
        session,  # type: ignore[arg-type]
        context=context,
        usage_id=usage.id,
        checked_out_at=checked_out_at,
    )

    assert result is completed
    assert result.status is UsageStatus.COMPLETED


@pytest.mark.asyncio
async def test_check_out_missing_usage_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    usage_id = uuid4()
    session = object()

    async def fake_get_usage(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "bcos_api.usages.service.get_usage",
        fake_get_usage,
    )

    with pytest.raises(UsageNotFound):
        await check_out(
            session,  # type: ignore[arg-type]
            context=context,
            usage_id=usage_id,
        )


@pytest.mark.asyncio
async def test_check_out_rejects_non_checked_in_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    session = object()

    usage = usage_for(
        tenant_id=context.tenant_id,
        booking_id=uuid4(),
        resource_id=uuid4(),
        professional_id=uuid4(),
        status=UsageStatus.PENDING,
    )

    async def fake_get_usage(*args, **kwargs):
        return usage

    monkeypatch.setattr(
        "bcos_api.usages.service.get_usage",
        fake_get_usage,
    )

    with pytest.raises(UsageConflict):
        await check_out(
            session,  # type: ignore[arg-type]
            context=context,
            usage_id=usage.id,
        )


@pytest.mark.asyncio
async def test_check_out_rejects_timestamp_before_check_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    session = object()
    checked_in_at = datetime(2026, 9, 10, 13, 5, tzinfo=UTC)

    usage = usage_for(
        tenant_id=context.tenant_id,
        booking_id=uuid4(),
        resource_id=uuid4(),
        professional_id=uuid4(),
        checked_in_at=checked_in_at,
    )

    persistence_called = False

    async def fake_get_usage(*args, **kwargs):
        return usage

    async def fake_complete_usage_with_outbox(*args, **kwargs):
        nonlocal persistence_called
        persistence_called = True
        return usage

    monkeypatch.setattr(
        "bcos_api.usages.service.get_usage",
        fake_get_usage,
    )
    monkeypatch.setattr(
        "bcos_api.usages.service.complete_usage_with_outbox",
        fake_complete_usage_with_outbox,
    )

    with pytest.raises(InvalidUsage):
        await check_out(
            session,  # type: ignore[arg-type]
            context=context,
            usage_id=usage.id,
            checked_out_at=datetime(
                2026,
                9,
                10,
                13,
                4,
                tzinfo=UTC,
            ),
        )

    assert persistence_called is False


@pytest.mark.asyncio
async def test_check_out_repository_race_becomes_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    session = object()

    usage = usage_for(
        tenant_id=context.tenant_id,
        booking_id=uuid4(),
        resource_id=uuid4(),
        professional_id=uuid4(),
        checked_in_at=datetime(2026, 9, 10, 13, 5, tzinfo=UTC),
    )

    async def fake_get_usage(*args, **kwargs):
        return usage

    async def fake_complete_usage_with_outbox(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "bcos_api.usages.service.get_usage",
        fake_get_usage,
    )
    monkeypatch.setattr(
        "bcos_api.usages.service.complete_usage_with_outbox",
        fake_complete_usage_with_outbox,
    )

    with pytest.raises(UsageConflict):
        await check_out(
            session,  # type: ignore[arg-type]
            context=context,
            usage_id=usage.id,
            checked_out_at=datetime(
                2026,
                9,
                10,
                14,
                0,
                tzinfo=UTC,
            ),
        )
