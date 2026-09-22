"""FastAPI dependencies for HPTECH platform authority."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.auth.dependencies import get_authenticated_identity
from bcos_api.auth.identity import AuthenticatedIdentity
from bcos_api.db.session import get_async_session
from bcos_api.platform.context import resolve_platform_context
from bcos_api.platform.domain import PlatformAccessDenied, PlatformContext


async def get_platform_context(
    identity: Annotated[AuthenticatedIdentity, Depends(get_authenticated_identity)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PlatformContext:
    try:
        return await resolve_platform_context(
            session,
            external_user_id=identity.external_user_id,
        )
    except PlatformAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated identity does not have HPTECH platform access.",
        ) from exc
