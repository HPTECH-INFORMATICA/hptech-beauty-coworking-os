"""Tests for production Neon Auth identity verification."""

import pytest
from jwt.exceptions import InvalidTokenError

from bcos_api.auth.identity import AuthenticationFailed, NeonAuthIdentityVerifier


@pytest.mark.asyncio
async def test_neon_verifier_fails_closed_when_unconfigured() -> None:
    verifier = NeonAuthIdentityVerifier(issuer="", jwks_url="")
    with pytest.raises(AuthenticationFailed, match="not configured"):
        await verifier.verify("token")


@pytest.mark.asyncio
async def test_neon_verifier_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeJWKClient:
        def __init__(self, url: str) -> None:
            assert url == "https://auth.example/jwks"

        def get_signing_key_from_jwt(self, token: str) -> object:
            del token
            raise InvalidTokenError("invalid")

    monkeypatch.setattr("bcos_api.auth.identity.PyJWKClient", FakeJWKClient)
    verifier = NeonAuthIdentityVerifier(
        issuer="https://auth.example",
        jwks_url="https://auth.example/jwks",
    )
    with pytest.raises(AuthenticationFailed, match="verification failed"):
        await verifier.verify("bad-token")


@pytest.mark.asyncio
async def test_neon_verifier_allows_current_managed_auth_eddsa_algorithm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSigningKey:
        key = object()

    class FakeJWKClient:
        def __init__(self, url: str) -> None:
            assert url == "https://auth.example/jwks"

        def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
            assert token == "managed-auth-token"
            return FakeSigningKey()

    def fake_decode(token: str, key: object, **kwargs: object) -> dict[str, str]:
        assert token == "managed-auth-token"
        assert key is FakeSigningKey.key
        assert "EdDSA" in kwargs["algorithms"]  # type: ignore[operator]
        assert kwargs["issuer"] == "https://auth.example"
        return {"sub": "user-123", "iss": "https://auth.example"}

    monkeypatch.setattr("bcos_api.auth.identity.PyJWKClient", FakeJWKClient)
    monkeypatch.setattr("bcos_api.auth.identity.jwt.decode", fake_decode)
    verifier = NeonAuthIdentityVerifier(
        issuer="https://auth.example",
        jwks_url="https://auth.example/jwks",
    )

    identity = await verifier.verify("managed-auth-token")

    assert identity.external_user_id == "user-123"
