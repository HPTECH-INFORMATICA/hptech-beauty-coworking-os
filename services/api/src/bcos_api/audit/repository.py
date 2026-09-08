"""Persistence helpers for BCOS audit events."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_audit_log(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    actor_external_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    metadata: dict[str, Any],
) -> None:
    """Persist one audit event inside the caller-owned transaction."""

    await session.execute(
        text(
            """
            INSERT INTO audit_logs (
                tenant_id,
                actor_external_user_id,
                action,
                entity_type,
                entity_id,
                metadata
            )
            VALUES (
                :tenant_id,
                :actor_external_user_id,
                :action,
                :entity_type,
                :entity_id,
                CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "actor_external_user_id": actor_external_user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": json.dumps(metadata),
        },
    )
