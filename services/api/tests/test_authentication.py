"""Tests for the BCOS HTTP authentication boundary."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from bcos_api.auth.dependencies import (
    get_authenticated_identity,
    get_identity_verifier,
)
from bcos_api.auth.identity import (
    AuthenticatedIdentity,
    AuthenticationFailed,
)


class TrustedTestVerifier:
    """Controlled verifier used only through FastAPI dependency overrides."""

    async def verify(self, token: str) -> AuthenticatedIdentity:
        if token != "valid-test-token":
            raise AuthenticationFailed("Invalid test token.")

        return AuthenticatedIdentity(
            external_user_id="identity-authenticated-user",
        )


class EmptyIdentityVerifier:
    """Verifier used to prove that empty identities are rejected."""

    async def verify(self, token: str) -> AuthenticatedIdentity:
        del token

        return AuthenticatedIdentity(
            external_user_id="   ",
        )


def create_test_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected")
    async def protected(
        identity: AuthenticatedIdentity = Depends(
            get_authenticated_identity
        ),
    ) -> dict[str, str]:
        return {
            "external_user_id": identity.external_user_id,
        }

    return app


def test_missing_bearer_credentials_returns_401() -> None:
    app = create_test_app()

    app.dependency_overrides[get_identity_verifier] = (
        lambda: TrustedTestVerifier()
    )

    client = TestClient(app)

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "detail": "Authentication credentials are required."
    }


def test_rejected_bearer_token_returns_401() -> None:
    app = create_test_app()

    app.dependency_overrides[get_identity_verifier] = (
        lambda: TrustedTestVerifier()
    )

    client = TestClient(app)

    response = client.get(
        "/protected",
        headers={
            "Authorization": "Bearer invalid-test-token",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "detail": "Authentication failed."
    }


def test_trusted_verifier_establishes_authenticated_identity() -> None:
    app = create_test_app()

    app.dependency_overrides[get_identity_verifier] = (
        lambda: TrustedTestVerifier()
    )

    client = TestClient(app)

    response = client.get(
        "/protected",
        headers={
            "Authorization": "Bearer valid-test-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "external_user_id": "identity-authenticated-user",
    }


def test_empty_external_identity_is_rejected() -> None:
    app = create_test_app()

    app.dependency_overrides[get_identity_verifier] = (
        lambda: EmptyIdentityVerifier()
    )

    client = TestClient(app)

    response = client.get(
        "/protected",
        headers={
            "Authorization": "Bearer valid-test-token",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "detail": "Authentication failed."
    }


def test_unconfigured_production_verifier_fails_closed() -> None:
    app = create_test_app()
    client = TestClient(app)

    response = client.get(
        "/protected",
        headers={
            "Authorization": "Bearer any-token",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "detail": "Authentication failed."
    }
