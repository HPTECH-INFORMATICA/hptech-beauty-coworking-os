"""FastAPI tenant authorization dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.auth.dependencies import get_authenticated_identity
from bcos_api.auth.identity import AuthenticatedIdentity
from bcos_api.db.session import get_async_session
from bcos_api.tenancy.context import (
    TenantAccessDenied,
    TenantContext,
    resolve_tenant_context,
)


async def get_tenant_context(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(get_authenticated_identity),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_async_session),
    ],
    x_tenant_id: Annotated[
        str,
        Header(alias="X-Tenant-Id"),
    ],
) -> TenantContext:
    """Resolve the authenticated identity inside the requested tenant."""

    try:
        tenant_id = UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="X-Tenant-Id must be a valid UUID.",
        ) from exc

    try:
        return await resolve_tenant_context(
            session,
            tenant_id=tenant_id,
            external_user_id=identity.external_user_id,
        )
    except TenantAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated identity does not have access "
            "to the requested tenant.",
        ) from exc
