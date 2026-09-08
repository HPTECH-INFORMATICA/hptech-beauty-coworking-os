from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from bcos_api.bookings.domain import Booking, BookingStatus
from bcos_api.bookings.pricing import PricingSnapshotUnavailable
from bcos_api.bookings.router import get_pricing_snapshot_producer
from bcos_api.bookings.series_domain import BookingSeries
from bcos_api.bookings.service import (
    BookingConflict,
    BookingNotFound,
    BookingSeriesNotFound,
)
from bcos_api.db.session import get_async_session
from bcos_api.main import create_app
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.membership import MembershipRole


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def make_context(tenant_id: UUID) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id,
        membership_id=uuid4(),
        external_user_id="identity:test-owner",
        role=MembershipRole.OWNER,
    )


def make_booking(
    *,
    tenant_id: UUID,
    unit_id: UUID,
    resource_id: UUID,
    professional_id: UUID,
) -> Booking:
    return Booking(
        id=uuid4(),
        tenant_id=tenant_id,
        unit_id=unit_id,
        resource_id=resource_id,
        professional_id=professional_id,
        series_id=None,
        status=BookingStatus.PENDING,
        starts_at=datetime(2026, 9, 10, 13, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 10, 14, 0, tzinfo=UTC),
        buffer_before_minutes=10,
        buffer_after_minutes=15,
        pricing_snapshot={"source": "test"},
        notes=None,
        confirmed_at=None,
        cancelled_at=None,
        completed_at=None,
    )


def create_test_app(
    *,
    session: FakeSession,
    context: TenantContext,
):
    app = create_app()

    async def fake_session_dependency():
        yield session

    async def fake_tenant_context() -> TenantContext:
        return context

    app.dependency_overrides[get_async_session] = fake_session_dependency
    app.dependency_overrides[get_tenant_context] = fake_tenant_context

    return app


def test_list_bookings_maps_http_filters_and_response(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    unit_id = uuid4()
    resource_id = uuid4()
    professional_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)

    booking = make_booking(
        tenant_id=tenant_id,
        unit_id=unit_id,
        resource_id=resource_id,
        professional_id=professional_id,
    )

    captured: dict[str, object] = {}

    async def fake_list_bookings(
        received_session,
        *,
        context,
        starts_from,
        starts_until,
        professional_id,
        resource_id,
        status,
    ):
        captured.update(
            {
                "session": received_session,
                "context": context,
                "starts_from": starts_from,
                "starts_until": starts_until,
                "professional_id": professional_id,
                "resource_id": resource_id,
                "status": status,
            }
        )
        return [booking]

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_list_bookings",
        fake_list_bookings,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.get(
        "/api/v1/bookings",
        params={
            "starts_from": "2026-09-10T12:00:00Z",
            "starts_until": "2026-09-10T18:00:00Z",
            "professional_id": str(professional_id),
            "resource_id": str(resource_id),
            "status": "PENDING",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(booking.id)
    assert response.json()[0]["status"] == "PENDING"

    assert captured["session"] is session
    assert captured["context"] is context
    assert captured["professional_id"] == professional_id
    assert captured["resource_id"] == resource_id
    assert captured["status"] is BookingStatus.PENDING
    assert captured["starts_from"] == datetime(
        2026,
        9,
        10,
        12,
        0,
        tzinfo=UTC,
    )
    assert captured["starts_until"] == datetime(
        2026,
        9,
        10,
        18,
        0,
        tzinfo=UTC,
    )

    assert session.commits == 0
    assert session.rollbacks == 0


class FakePricingSnapshotProducer:
    async def produce(self, request):
        del request
        return {"source": "test"}


def make_series(
    *,
    tenant_id: UUID,
    professional_id: UUID,
) -> BookingSeries:
    return BookingSeries(
        id=uuid4(),
        tenant_id=tenant_id,
        professional_id=professional_id,
        rrule="FREQ=DAILY;COUNT=2",
        timezone="America/Sao_Paulo",
        starts_at=datetime(2026, 9, 10, 13, 0, tzinfo=UTC),
        ends_at=None,
        cancelled_at=None,
    )


def install_pricing_override(app) -> None:
    app.dependency_overrides[get_pricing_snapshot_producer] = (
        lambda: FakePricingSnapshotProducer()
    )


def test_create_booking_returns_201_and_commits(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    unit_id = uuid4()
    resource_id = uuid4()
    professional_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    booking = make_booking(
        tenant_id=tenant_id,
        unit_id=unit_id,
        resource_id=resource_id,
        professional_id=professional_id,
    )

    captured: dict[str, object] = {}

    async def fake_create_booking(
        received_session,
        **kwargs,
    ):
        captured["session"] = received_session
        captured.update(kwargs)
        return booking

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_create_booking",
        fake_create_booking,
    )

    app = create_test_app(session=session, context=context)
    install_pricing_override(app)
    client = TestClient(app)

    response = client.post(
        "/api/v1/bookings",
        json={
            "unit_id": str(unit_id),
            "resource_id": str(resource_id),
            "professional_id": str(professional_id),
            "starts_at": "2026-09-10T13:00:00Z",
            "ends_at": "2026-09-10T14:00:00Z",
            "notes": "HTTP test",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(booking.id)
    assert captured["session"] is session
    assert captured["context"] is context
    assert captured["unit_id"] == unit_id
    assert captured["resource_id"] == resource_id
    assert captured["professional_id"] == professional_id
    assert session.commits == 1
    assert session.rollbacks == 0


def test_create_booking_conflict_returns_409_and_rolls_back(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)

    async def fake_create_booking(*args, **kwargs):
        del args, kwargs
        raise BookingConflict("Booking conflict.")

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_create_booking",
        fake_create_booking,
    )

    app = create_test_app(session=session, context=context)
    install_pricing_override(app)
    client = TestClient(app)

    response = client.post(
        "/api/v1/bookings",
        json={
            "unit_id": str(uuid4()),
            "resource_id": str(uuid4()),
            "professional_id": str(uuid4()),
            "starts_at": "2026-09-10T13:00:00Z",
            "ends_at": "2026-09-10T14:00:00Z",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"
    assert session.commits == 0
    assert session.rollbacks == 1


def test_create_booking_pricing_unavailable_returns_409(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)

    async def fake_create_booking(*args, **kwargs):
        del args, kwargs
        raise PricingSnapshotUnavailable("Pricing unavailable.")

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_create_booking",
        fake_create_booking,
    )

    app = create_test_app(session=session, context=context)
    install_pricing_override(app)
    client = TestClient(app)

    response = client.post(
        "/api/v1/bookings",
        json={
            "unit_id": str(uuid4()),
            "resource_id": str(uuid4()),
            "professional_id": str(uuid4()),
            "starts_at": "2026-09-10T13:00:00Z",
            "ends_at": "2026-09-10T14:00:00Z",
        },
    )

    assert response.status_code == 409
    assert session.commits == 0
    assert session.rollbacks == 1


def test_get_booking_returns_200(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    booking = make_booking(
        tenant_id=tenant_id,
        unit_id=uuid4(),
        resource_id=uuid4(),
        professional_id=uuid4(),
    )

    async def fake_get_booking(
        received_session,
        *,
        context,
        booking_id,
    ):
        assert received_session is session
        assert context is not None
        assert booking_id == booking.id
        return booking

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_get_booking",
        fake_get_booking,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.get(f"/api/v1/bookings/{booking.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(booking.id)
    assert session.commits == 0
    assert session.rollbacks == 0


def test_get_booking_not_found_returns_404(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    booking_id = uuid4()

    async def fake_get_booking(*args, **kwargs):
        del args, kwargs
        raise BookingNotFound("Booking not found.")

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_get_booking",
        fake_get_booking,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.get(f"/api/v1/bookings/{booking_id}")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert session.commits == 0
    assert session.rollbacks == 0


def test_confirm_booking_returns_200_and_commits(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    booking = make_booking(
        tenant_id=tenant_id,
        unit_id=uuid4(),
        resource_id=uuid4(),
        professional_id=uuid4(),
    )

    async def fake_confirm_booking(*args, **kwargs):
        del args, kwargs
        return booking

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_confirm_booking",
        fake_confirm_booking,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/confirm"
    )

    assert response.status_code == 200
    assert session.commits == 1
    assert session.rollbacks == 0


def test_confirm_booking_conflict_returns_409_and_rolls_back(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    booking_id = uuid4()

    async def fake_confirm_booking(*args, **kwargs):
        del args, kwargs
        raise BookingConflict("Occupancy conflict.")

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_confirm_booking",
        fake_confirm_booking,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/bookings/{booking_id}/confirm"
    )

    assert response.status_code == 409
    assert session.commits == 0
    assert session.rollbacks == 1


def test_cancel_booking_accepts_optional_reason_and_commits(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    booking = make_booking(
        tenant_id=tenant_id,
        unit_id=uuid4(),
        resource_id=uuid4(),
        professional_id=uuid4(),
    )
    captured: dict[str, object] = {}

    async def fake_cancel_booking(
        received_session,
        *,
        context,
        booking_id,
        reason,
    ):
        captured.update(
            {
                "session": received_session,
                "context": context,
                "booking_id": booking_id,
                "reason": reason,
            }
        )
        return booking

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_cancel_booking",
        fake_cancel_booking,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/cancel",
        json={"reason": "Cliente solicitou cancelamento."},
    )

    assert response.status_code == 200
    assert captured["session"] is session
    assert captured["context"] is context
    assert captured["booking_id"] == booking.id
    assert captured["reason"] == "Cliente solicitou cancelamento."
    assert session.commits == 1
    assert session.rollbacks == 0


def test_cancel_booking_without_body_passes_none_reason(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    booking = make_booking(
        tenant_id=tenant_id,
        unit_id=uuid4(),
        resource_id=uuid4(),
        professional_id=uuid4(),
    )
    captured: dict[str, object] = {}

    async def fake_cancel_booking(
        received_session,
        *,
        context,
        booking_id,
        reason,
    ):
        del received_session, context, booking_id
        captured["reason"] = reason
        return booking

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_cancel_booking",
        fake_cancel_booking,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/cancel"
    )

    assert response.status_code == 200
    assert captured["reason"] is None
    assert session.commits == 1
    assert session.rollbacks == 0


def test_extend_booking_maps_new_end_and_commits(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    booking = make_booking(
        tenant_id=tenant_id,
        unit_id=uuid4(),
        resource_id=uuid4(),
        professional_id=uuid4(),
    )
    captured: dict[str, object] = {}

    async def fake_extend_booking(
        received_session,
        *,
        context,
        booking_id,
        ends_at,
    ):
        captured.update(
            {
                "session": received_session,
                "context": context,
                "booking_id": booking_id,
                "ends_at": ends_at,
            }
        )
        return booking

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_extend_booking",
        fake_extend_booking,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/extend",
        json={"ends_at": "2026-09-10T15:00:00Z"},
    )

    assert response.status_code == 200
    assert captured["booking_id"] == booking.id
    assert captured["ends_at"] == datetime(
        2026,
        9,
        10,
        15,
        0,
        tzinfo=UTC,
    )
    assert session.commits == 1
    assert session.rollbacks == 0


def test_extend_booking_conflict_returns_409_and_rolls_back(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    booking_id = uuid4()

    async def fake_extend_booking(*args, **kwargs):
        del args, kwargs
        raise BookingConflict("Extension conflict.")

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_extend_booking",
        fake_extend_booking,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/bookings/{booking_id}/extend",
        json={"ends_at": "2026-09-10T15:00:00Z"},
    )

    assert response.status_code == 409
    assert session.commits == 0
    assert session.rollbacks == 1


def test_create_booking_series_returns_201_and_commits(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    unit_id = uuid4()
    resource_id = uuid4()
    professional_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    series = make_series(
        tenant_id=tenant_id,
        professional_id=professional_id,
    )
    first = make_booking(
        tenant_id=tenant_id,
        unit_id=unit_id,
        resource_id=resource_id,
        professional_id=professional_id,
    )
    second = make_booking(
        tenant_id=tenant_id,
        unit_id=unit_id,
        resource_id=resource_id,
        professional_id=professional_id,
    )

    async def fake_create_booking_series(*args, **kwargs):
        del args, kwargs
        return series, [first, second]

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_create_booking_series",
        fake_create_booking_series,
    )

    app = create_test_app(session=session, context=context)
    install_pricing_override(app)
    client = TestClient(app)

    response = client.post(
        "/api/v1/booking-series",
        json={
            "unit_id": str(unit_id),
            "resource_id": str(resource_id),
            "professional_id": str(professional_id),
            "starts_at": "2026-09-10T13:00:00Z",
            "duration_minutes": 60,
            "rrule": "FREQ=DAILY;COUNT=2",
            "timezone": "America/Sao_Paulo",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["series"]["id"] == str(series.id)
    assert len(body["bookings"]) == 2
    assert session.commits == 1
    assert session.rollbacks == 0


def test_cancel_booking_series_returns_200_and_commits(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    professional_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    series = make_series(
        tenant_id=tenant_id,
        professional_id=professional_id,
    )

    async def fake_cancel_booking_series(
        received_session,
        *,
        context,
        series_id,
    ):
        assert received_session is session
        assert context is not None
        assert series_id == series.id
        return series

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_cancel_booking_series",
        fake_cancel_booking_series,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/booking-series/{series.id}/cancel"
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(series.id)
    assert session.commits == 1
    assert session.rollbacks == 0


def test_cancel_booking_series_not_found_returns_404_and_rolls_back(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    series_id = uuid4()

    async def fake_cancel_booking_series(*args, **kwargs):
        del args, kwargs
        raise BookingSeriesNotFound("Booking series not found.")

    monkeypatch.setattr(
        "bcos_api.bookings.router.service_cancel_booking_series",
        fake_cancel_booking_series,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/booking-series/{series_id}/cancel"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert session.commits == 0
    assert session.rollbacks == 1
