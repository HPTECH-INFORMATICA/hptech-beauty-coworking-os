"""Tenant-scoped persistence and resolution for BCOS pricing rules."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.pricing.domain import PricingRule, PricingRuleStatus


def _pricing_rule_from_row(row: dict[str, object]) -> PricingRule:
    """Map one database row to the PricingRule domain model."""

    return PricingRule(
        id=row["id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        unit_id=row["unit_id"],  # type: ignore[arg-type]
        resource_category_id=row["resource_category_id"],  # type: ignore[arg-type]
        name=row["name"],  # type: ignore[arg-type]
        status=PricingRuleStatus(row["status"]),  # type: ignore[arg-type]
        priority=row["priority"],  # type: ignore[arg-type]
        currency=row["currency"],  # type: ignore[arg-type]
        rule_definition=row["rule_definition"],  # type: ignore[arg-type]
        valid_from=row["valid_from"],  # type: ignore[arg-type]
        valid_until=row["valid_until"],  # type: ignore[arg-type]
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
        deleted_at=row["deleted_at"],  # type: ignore[arg-type]
    )


async def list_pricing_rules(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> list[PricingRule]:
    """List non-deleted pricing rules inside one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                unit_id,
                resource_category_id,
                name,
                status,
                priority,
                currency,
                rule_definition,
                valid_from,
                valid_until,
                created_at,
                updated_at,
                deleted_at
            FROM pricing_rules
            WHERE tenant_id = :tenant_id
              AND deleted_at IS NULL
            ORDER BY priority, name, id
            """
        ),
        {"tenant_id": tenant_id},
    )

    return [
        _pricing_rule_from_row(dict(row))
        for row in result.mappings().all()
    ]


async def create_pricing_rule(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID | None,
    resource_category_id: UUID | None,
    name: str,
    priority: int,
    currency: str,
    rule_definition: dict[str, Any],
    valid_from: datetime | None,
    valid_until: datetime | None,
) -> PricingRule:
    """Create one pricing rule inside the authorized tenant."""

    result = await session.execute(
        text(
            """
            INSERT INTO pricing_rules (
                tenant_id,
                unit_id,
                resource_category_id,
                name,
                priority,
                currency,
                rule_definition,
                valid_from,
                valid_until
            )
            VALUES (
                :tenant_id,
                :unit_id,
                :resource_category_id,
                :name,
                :priority,
                :currency,
                CAST(:rule_definition AS JSONB),
                :valid_from,
                :valid_until
            )
            RETURNING
                id,
                tenant_id,
                unit_id,
                resource_category_id,
                name,
                status,
                priority,
                currency,
                rule_definition,
                valid_from,
                valid_until,
                created_at,
                updated_at,
                deleted_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "unit_id": unit_id,
            "resource_category_id": resource_category_id,
            "name": name,
            "priority": priority,
            "currency": currency,
            "rule_definition": json.dumps(rule_definition),
            "valid_from": valid_from,
            "valid_until": valid_until,
        },
    )

    row = result.mappings().one()
    return _pricing_rule_from_row(dict(row))


async def resolve_pricing_rule(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
    resource_category_id: UUID,
    effective_at: datetime,
) -> PricingRule | None:
    """Resolve the most specific active pricing rule deterministically."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                unit_id,
                resource_category_id,
                name,
                status,
                priority,
                currency,
                rule_definition,
                valid_from,
                valid_until,
                created_at,
                updated_at,
                deleted_at
            FROM pricing_rules
            WHERE tenant_id = :tenant_id
              AND deleted_at IS NULL
              AND status = 'ACTIVE'
              AND (unit_id IS NULL OR unit_id = :unit_id)
              AND (
                  resource_category_id IS NULL
                  OR resource_category_id = :resource_category_id
              )
              AND (valid_from IS NULL OR valid_from <= :effective_at)
              AND (valid_until IS NULL OR :effective_at < valid_until)
            ORDER BY
                priority ASC,
                (
                    CASE WHEN unit_id IS NOT NULL THEN 1 ELSE 0 END
                    +
                    CASE
                        WHEN resource_category_id IS NOT NULL THEN 1
                        ELSE 0
                    END
                ) DESC,
                id ASC
            LIMIT 1
            """
        ),
        {
            "tenant_id": tenant_id,
            "unit_id": unit_id,
            "resource_category_id": resource_category_id,
            "effective_at": effective_at,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _pricing_rule_from_row(dict(row))
