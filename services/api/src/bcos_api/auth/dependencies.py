"""FastAPI authentication dependencies."""

from __future__ import annotations

import os
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from bcos_api.auth.identity import (
    AuthenticatedIdentity,
    AuthenticationFailed,
    HomologationIdentityVerifier,
    IdentityVerifier,
    NeonAuthIdentityVerifier,
    UnconfiguredIdentityVerifier,
)

bearer_scheme = HTTPBearer(
    scheme_name="bearerAuth",
    auto_error=False,
)


def _neon_issuer_origin(value: str) -> str:
    """Normalize Neon Auth configuration to the JWT issuer origin."""

    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _neon_jwks_candidates(configured_issuer: str, configured_jwks_url: str) -> tuple[str, ...]:
    """Build trusted Neon Managed Auth JWKS candidates from server configuration."""

    candidates: list[str] = []
    explicit = configured_jwks_url.strip()
    if explicit:
        candidates.append(explicit)

    parsed = urlsplit(configured_issuer.strip())
    if parsed.scheme in {"http", "https"} and parsed.netloc and parsed.path.rstrip("/"):
        managed = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}/.well-known/jwks.json"
        if managed not in candidates:
            candidates.append(managed)

    return tuple(candidates)


def get_identity_verifier() -> IdentityVerifier:
    """Return the configured trusted identity verifier."""

    provider = os.getenv("BCOS_IDENTITY_PROVIDER", "").strip().lower()
    if provider == "neon":
        configured_issuer = os.getenv("BCOS_NEON_AUTH_ISSUER", "").strip()
        issuer = _neon_issuer_origin(configured_issuer)
        configured_jwks_url = os.getenv("BCOS_NEON_AUTH_JWKS_URL", "").strip()
        jwks_urls = _neon_jwks_candidates(configured_issuer, configured_jwks_url)
        if issuer and jwks_urls:
            return NeonAuthIdentityVerifier(issuer=issuer, jwks_urls=jwks_urls)
        return UnconfiguredIdentityVerifier()

    homologation_token = os.getenv(
        "BCOS_HOMOLOGATION_BEARER_TOKEN",
        "",
    ).strip()
    homologation_external_user_id = os.getenv(
        "BCOS_HOMOLOGATION_EXTERNAL_USER_ID",
        "",
    ).strip()

    if homologation_token and homologation_external_user_id:
        return HomologationIdentityVerifier(
            expected_token=homologation_token,
            external_user_id=homologation_external_user_id,
        )

    return UnconfiguredIdentityVerifier()


async def get_authenticated_identity(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    verifier: Annotated[
        IdentityVerifier,
        Depends(get_identity_verifier),
    ],
) -> AuthenticatedIdentity:
    """Authenticate the request bearer token through the trusted verifier."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        identity = await verifier.verify(token)
    except AuthenticationFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not identity.external_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return identity
