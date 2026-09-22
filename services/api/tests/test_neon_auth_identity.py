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
