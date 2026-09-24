"""FastAPI authentication dependencies."""

from __future__ import annotations

import os
from urllib.parse import urlsplit
from typing import Annotated

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


def get_identity_verifier() -> IdentityVerifier:
    """Return the configured trusted identity verifier."""

    provider = os.getenv("BCOS_IDENTITY_PROVIDER", "").strip().lower()
    if provider == "neon":
        configured_issuer = os.getenv("BCOS_NEON_AUTH_ISSUER", "").strip()
        issuer = _neon_issuer_origin(configured_issuer)
        jwks_url = os.getenv("BCOS_NEON_AUTH_JWKS_URL", "").strip()
        if issuer and jwks_url:
            return NeonAuthIdentityVerifier(issuer=issuer, jwks_url=jwks_url)
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
