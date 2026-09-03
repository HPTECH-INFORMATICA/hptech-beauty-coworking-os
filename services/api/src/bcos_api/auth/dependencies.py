"""FastAPI authentication dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from bcos_api.auth.identity import (
    AuthenticatedIdentity,
    AuthenticationFailed,
    IdentityVerifier,
    UnconfiguredIdentityVerifier,
)

bearer_scheme = HTTPBearer(
    scheme_name="bearerAuth",
    auto_error=False,
)


def get_identity_verifier() -> IdentityVerifier:
    """Return the configured trusted identity verifier."""

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
