"""Authenticated identity boundary for BCOS."""

from __future__ import annotations

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
