"""Persistence for HPTECH platform audit evidence."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_platform_audit_log(
    session: AsyncSession,
    *,
    actor_external_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    tenant_id: UUID | None,
    metadata: dict[str, Any],
) -> None:
    await session.execute(
        text(
            """INSERT INTO platform_audit_logs
            (actor_external_user_id, action, entity_type, entity_id, tenant_id, metadata)
            VALUES (:actor, :action, :entity_type, :entity_id, :tenant_id, CAST(:metadata AS jsonb))"""
        ),
        {"actor": actor_external_user_id, "action": action, "entity_type": entity_type, "entity_id": entity_id, "tenant_id": tenant_id, "metadata": json.dumps(metadata)},
    )
