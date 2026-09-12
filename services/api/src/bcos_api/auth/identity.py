"""Authenticated identity boundary for BCOS."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Protocol


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
