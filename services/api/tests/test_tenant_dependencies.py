"""Tests for the BCOS HTTP tenant authorization boundary."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from bcos_api.auth.dependencies import get_identity_verifier
from bcos_api.auth.identity import AuthenticatedIdentity
from bcos_api.db.session import get_async_session
from bcos_api.tenancy.context import (
    TenantAccessDenied,
    TenantContext,
)
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.membership import MembershipRole


class TrustedTestVerifier:
    """Controlled identity verifier used only by these tests."""

    async def verify(self, token: str) -> AuthenticatedIdentity:
        return AuthenticatedIdentity(
            external_user_id=f"identity:{token}",
        )


class FakeSession:
    """Session placeholder supplied through FastAPI dependency override."""


def create_test_app() -> FastAPI:
    app = FastAPI()

    @app.get("/tenant-protected")
    async def tenant_protected(
        context: TenantContext = Depends(get_tenant_context),
    ) -> dict[str, str]:
        return {
            "tenant_id": str(context.tenant_id),
            "external_user_id": context.external_user_id,
            "role": context.role.value,
        }

    return app


async def fake_session_dependency():
    yield FakeSession()


def test_authenticated_identity_resolves_requested_tenant(
    monkeypatch,
) -> None:
    tenant_id = uuid4()

    async def fake_resolve_tenant_context(
        session,
        *,
        tenant_id: UUID,
        external_user_id: str,
    ) -> TenantContext:
        del session

        return TenantContext(
            tenant_id=tenant_id,
            membership_id=uuid4(),
            external_user_id=external_user_id,
            role=MembershipRole.PROFESSIONAL,
        )

    monkeypatch.setattr(
        "bcos_api.tenancy.dependencies.resolve_tenant_context",
        fake_resolve_tenant_context,
    )

    app = create_test_app()
    app.dependency_overrides[get_identity_verifier] = (
        lambda: TrustedTestVerifier()
    )
    app.dependency_overrides[get_async_session] = fake_session_dependency

    client = TestClient(app)

    response = client.get(
        "/tenant-protected",
        headers={
            "Authorization": "Bearer valid-user",
            "X-Tenant-Id": str(tenant_id),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "tenant_id": str(tenant_id),
        "external_user_id": "identity:valid-user",
        "role": "PROFESSIONAL",
    }


def test_missing_tenant_header_is_rejected() -> None:
    app = create_test_app()
    app.dependency_overrides[get_identity_verifier] = (
        lambda: TrustedTestVerifier()
    )
    app.dependency_overrides[get_async_session] = fake_session_dependency

    client = TestClient(app)

    response = client.get(
        "/tenant-protected",
        headers={
            "Authorization": "Bearer valid-user",
        },
    )

    assert response.status_code == 422


def test_invalid_tenant_uuid_is_rejected() -> None:
    app = create_test_app()
    app.dependency_overrides[get_identity_verifier] = (
        lambda: TrustedTestVerifier()
    )
    app.dependency_overrides[get_async_session] = fake_session_dependency

    client = TestClient(app)

    response = client.get(
        "/tenant-protected",
        headers={
            "Authorization": "Bearer valid-user",
            "X-Tenant-Id": "not-a-uuid",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "X-Tenant-Id must be a valid UUID."
    }


def test_identity_without_tenant_access_is_rejected(
    monkeypatch,
) -> None:
    tenant_id = uuid4()

    async def deny_tenant_context(
        session,
        *,
        tenant_id: UUID,
        external_user_id: str,
    ) -> TenantContext:
        del session
        del tenant_id
        del external_user_id

        raise TenantAccessDenied("Denied.")

    monkeypatch.setattr(
        "bcos_api.tenancy.dependencies.resolve_tenant_context",
        deny_tenant_context,
    )

    app = create_test_app()
    app.dependency_overrides[get_identity_verifier] = (
        lambda: TrustedTestVerifier()
    )
    app.dependency_overrides[get_async_session] = fake_session_dependency

    client = TestClient(app)

    response = client.get(
        "/tenant-protected",
        headers={
            "Authorization": "Bearer valid-user",
            "X-Tenant-Id": str(tenant_id),
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": (
            "Authenticated identity does not have access "
            "to the requested tenant."
        )
    }


def test_cross_tenant_request_is_denied(
    monkeypatch,
) -> None:
    authorized_tenant_id = uuid4()
    other_tenant_id = uuid4()

    async def tenant_isolation(
        session,
        *,
        tenant_id: UUID,
        external_user_id: str,
    ) -> TenantContext:
        del session

        if tenant_id != authorized_tenant_id:
            raise TenantAccessDenied("Cross-tenant access denied.")

        return TenantContext(
            tenant_id=tenant_id,
            membership_id=uuid4(),
            external_user_id=external_user_id,
            role=MembershipRole.PROFESSIONAL,
        )

    monkeypatch.setattr(
        "bcos_api.tenancy.dependencies.resolve_tenant_context",
        tenant_isolation,
    )

    app = create_test_app()
    app.dependency_overrides[get_identity_verifier] = (
        lambda: TrustedTestVerifier()
    )
    app.dependency_overrides[get_async_session] = fake_session_dependency

    client = TestClient(app)

    response = client.get(
        "/tenant-protected",
        headers={
            "Authorization": "Bearer valid-user",
            "X-Tenant-Id": str(other_tenant_id),
        },
    )

    assert response.status_code == 403
