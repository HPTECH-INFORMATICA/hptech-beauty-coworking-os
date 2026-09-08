from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from bcos_api.db.session import get_async_session
from bcos_api.main import create_app
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.usages.domain import Usage, UsageStatus
from bcos_api.usages.service import UsageConflict, UsageNotFound


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


def make_usage(
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


def test_check_in_returns_201_and_commits(monkeypatch) -> None:
    tenant_id = uuid4()
    booking_id = uuid4()
    resource_id = uuid4()
    professional_id = uuid4()
    checked_in_at = datetime(2026, 9, 10, 13, 5, tzinfo=UTC)

    session = FakeSession()
    context = make_context(tenant_id)
    usage = make_usage(
        tenant_id=tenant_id,
        booking_id=booking_id,
        resource_id=resource_id,
        professional_id=professional_id,
        checked_in_at=checked_in_at,
    )

    captured: dict[str, object] = {}

    async def fake_check_in(
        received_session,
        *,
        context,
        booking_id,
        checked_in_at,
    ):
        captured.update(
            {
                "session": received_session,
                "context": context,
                "booking_id": booking_id,
                "checked_in_at": checked_in_at,
            }
        )
        return usage

    monkeypatch.setattr(
        "bcos_api.usages.router.service_check_in",
        fake_check_in,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        "/api/v1/usages/check-in",
        json={
            "booking_id": str(booking_id),
            "checked_in_at": "2026-09-10T13:05:00Z",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(usage.id),
        "booking_id": str(booking_id),
        "resource_id": str(resource_id),
        "professional_id": str(professional_id),
        "status": "CHECKED_IN",
        "checked_in_at": "2026-09-10T13:05:00Z",
        "checked_out_at": None,
    }

    assert captured["session"] is session
    assert captured["context"] is context
    assert captured["booking_id"] == booking_id
    assert captured["checked_in_at"] == checked_in_at
    assert session.commits == 1
    assert session.rollbacks == 0


def test_check_in_not_found_returns_404_and_rolls_back(monkeypatch) -> None:
    tenant_id = uuid4()
    booking_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)

    async def fake_check_in(*args, **kwargs):
        raise UsageNotFound("Booking does not exist in the tenant.")

    monkeypatch.setattr(
        "bcos_api.usages.router.service_check_in",
        fake_check_in,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        "/api/v1/usages/check-in",
        json={"booking_id": str(booking_id)},
    )

    assert response.status_code == 404
    assert session.commits == 0
    assert session.rollbacks == 1


def test_check_in_conflict_returns_409_and_rolls_back(monkeypatch) -> None:
    tenant_id = uuid4()
    booking_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)

    async def fake_check_in(*args, **kwargs):
        raise UsageConflict("Booking already has a Usage.")

    monkeypatch.setattr(
        "bcos_api.usages.router.service_check_in",
        fake_check_in,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        "/api/v1/usages/check-in",
        json={"booking_id": str(booking_id)},
    )

    assert response.status_code == 409
    assert session.commits == 0
    assert session.rollbacks == 1


def test_check_out_accepts_optional_body_and_commits(monkeypatch) -> None:
    tenant_id = uuid4()
    booking_id = uuid4()
    resource_id = uuid4()
    professional_id = uuid4()
    usage_id = uuid4()
    checked_in_at = datetime(2026, 9, 10, 13, 5, tzinfo=UTC)
    checked_out_at = datetime(2026, 9, 10, 14, 10, tzinfo=UTC)

    session = FakeSession()
    context = make_context(tenant_id)

    usage = Usage(
        id=usage_id,
        tenant_id=tenant_id,
        booking_id=booking_id,
        resource_id=resource_id,
        professional_id=professional_id,
        status=UsageStatus.COMPLETED,
        checked_in_at=checked_in_at,
        checked_out_at=checked_out_at,
    )

    captured: dict[str, object] = {}

    async def fake_check_out(
        received_session,
        *,
        context,
        usage_id,
        checked_out_at,
    ):
        captured.update(
            {
                "session": received_session,
                "context": context,
                "usage_id": usage_id,
                "checked_out_at": checked_out_at,
            }
        )
        return usage

    monkeypatch.setattr(
        "bcos_api.usages.router.service_check_out",
        fake_check_out,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/usages/{usage_id}/check-out",
        json={"checked_out_at": "2026-09-10T14:10:00Z"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(usage_id)
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["checked_out_at"] == "2026-09-10T14:10:00Z"

    assert captured["session"] is session
    assert captured["context"] is context
    assert captured["usage_id"] == usage_id
    assert captured["checked_out_at"] == checked_out_at
    assert session.commits == 1
    assert session.rollbacks == 0


def test_check_out_without_body_passes_none_timestamp(monkeypatch) -> None:
    tenant_id = uuid4()
    booking_id = uuid4()
    resource_id = uuid4()
    professional_id = uuid4()
    usage_id = uuid4()
    checked_in_at = datetime(2026, 9, 10, 13, 5, tzinfo=UTC)
    checked_out_at = datetime(2026, 9, 10, 14, 0, tzinfo=UTC)

    session = FakeSession()
    context = make_context(tenant_id)

    usage = Usage(
        id=usage_id,
        tenant_id=tenant_id,
        booking_id=booking_id,
        resource_id=resource_id,
        professional_id=professional_id,
        status=UsageStatus.COMPLETED,
        checked_in_at=checked_in_at,
        checked_out_at=checked_out_at,
    )

    captured: dict[str, object] = {}

    async def fake_check_out(
        received_session,
        *,
        context,
        usage_id,
        checked_out_at,
    ):
        captured["checked_out_at"] = checked_out_at
        return usage

    monkeypatch.setattr(
        "bcos_api.usages.router.service_check_out",
        fake_check_out,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/usages/{usage_id}/check-out",
    )

    assert response.status_code == 200
    assert captured["checked_out_at"] is None
    assert session.commits == 1
    assert session.rollbacks == 0


def test_check_out_not_found_returns_404_and_rolls_back(monkeypatch) -> None:
    tenant_id = uuid4()
    usage_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)

    async def fake_check_out(*args, **kwargs):
        raise UsageNotFound("Usage does not exist in the tenant.")

    monkeypatch.setattr(
        "bcos_api.usages.router.service_check_out",
        fake_check_out,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/usages/{usage_id}/check-out",
    )

    assert response.status_code == 404
    assert session.commits == 0
    assert session.rollbacks == 1


def test_check_out_conflict_returns_409_and_rolls_back(monkeypatch) -> None:
    tenant_id = uuid4()
    usage_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)

    async def fake_check_out(*args, **kwargs):
        raise UsageConflict("Usage must be CHECKED_IN before check-out.")

    monkeypatch.setattr(
        "bcos_api.usages.router.service_check_out",
        fake_check_out,
    )

    app = create_test_app(session=session, context=context)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/usages/{usage_id}/check-out",
    )

    assert response.status_code == 409
    assert session.commits == 0
    assert session.rollbacks == 1
