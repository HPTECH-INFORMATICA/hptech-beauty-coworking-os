"""Payment domain contracts for BCOS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class PaymentMethod(StrEnum):
    PIX = "PIX"
    CASH = "CASH"
    CARD = "CARD"
    OTHER = "OTHER"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class Payment:
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    idempotency_key: str
    method: PaymentMethod
    status: PaymentStatus
    currency: str
    amount: Decimal
    reference: str | None
    metadata: dict[str, object]
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime