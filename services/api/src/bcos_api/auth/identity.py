"""Authenticated identity boundary for BCOS."""

from __future__ import annotations

import hmac
import logging
from dataclasses import dataclass
from typing import Protocol

import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

logger = logging.getLogger(__name__)


class AuthenticationFailed(Exception):
    """Raised when a bearer token cannot be authenticated."""


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """Identity established by a trusted authentication verifier."""

    external_user_id: str


class IdentityVerifier(Protocol):
    """Contract implemented by the trusted HPTECH Identity adapter."""

    async def verify(self, token: str) -> AuthenticatedIdentity:
        """Cryptographically verify a bearer token and return its identity."""
        ...


class UnconfiguredIdentityVerifier:
    """Fail-closed verifier used until HPTECH Identity is configured."""

    async def verify(self, token: str) -> AuthenticatedIdentity:
        """Reject authentication while no trusted verifier is configured."""

        del token

        raise AuthenticationFailed(
            "Trusted identity verification is not configured."
        )


@dataclass(frozen=True)
class HomologationIdentityVerifier:
    """Environment-gated verifier used only for local human homologation."""

    expected_token: str
    external_user_id: str

    async def verify(self, token: str) -> AuthenticatedIdentity:
        """Authenticate one explicitly configured homologation identity."""

        if (
            not self.expected_token
            or not self.external_user_id
            or not hmac.compare_digest(token, self.expected_token)
        ):
            raise AuthenticationFailed(
                "Homologation identity verification failed."
            )

        return AuthenticatedIdentity(
            external_user_id=self.external_user_id
        )


@dataclass(frozen=True)
class NeonAuthIdentityVerifier:
    """Cryptographically verify production Neon Auth JWTs."""

    issuer: str
    jwks_urls: tuple[str, ...]

    async def verify(self, token: str) -> AuthenticatedIdentity:
        """Verify signature, issuer, expiry and stable subject."""

        if not self.issuer or not self.jwks_urls:
            raise AuthenticationFailed("Neon Auth verification is not configured.")

        last_error: Exception | None = None
        claims: dict[str, object] | None = None
        for jwks_url in self.jwks_urls:
            try:
                signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(token)
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["EdDSA", "RS256", "ES256"],
                    issuer=self.issuer,
                    options={"require": ["exp", "sub", "iss"]},
                )
                break
            except (InvalidTokenError, PyJWKClientError, ValueError, RuntimeError) as exc:
                last_error = exc

        if claims is None:
            logger.warning(
                "Neon Auth JWT verification rejected after %d trusted JWKS candidate(s): %s: %s",
                len(self.jwks_urls),
                type(last_error).__name__ if last_error else "UnknownError",
                last_error or "verification failed",
            )
            raise AuthenticationFailed("Neon Auth token verification failed.") from last_error

        external_user_id = str(claims.get("sub", "")).strip()
        if not external_user_id:
            raise AuthenticationFailed("Neon Auth token subject is missing.")

        return AuthenticatedIdentity(external_user_id=external_user_id)
