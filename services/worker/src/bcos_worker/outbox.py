"""Internal Outbox event contract consumed by the BCOS worker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class OutboxStatus(StrEnum):
    """Statuses persisted by the transactional Outbox."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class OutboxEvent:
    """Immutable representation of one persisted Outbox event."""

    id: UUID
    tenant_id: UUID
    dedupe_key: str
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    payload: dict[str, Any]
    status: OutboxStatus
    attempts: int
    available_at: datetime
    processed_at: datetime | None
    last_error: str | None
    created_at: datetime
