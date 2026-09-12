"""Public API schemas for BCOS Payments."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class ConfirmPixPaymentRequest(BaseModel):
    """Register one PIX payment already confirmed by the Coworking."""

    model_config = ConfigDict(extra="forbid")

    invoice_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reference: str | None = Field(default=None, max_length=255)
    paid_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Payment(BaseModel):
    """Public representation of one payment."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    invoice_id: UUID
    idempotency_key: str
    method: PaymentMethod
    status: PaymentStatus
    currency: str
    amount: Decimal
    reference: str | None
    metadata: dict[str, Any]
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentResult(BaseModel):
    """Payment plus resulting invoice financial state."""

    model_config = ConfigDict(extra="forbid")

    payment: Payment
    invoice_status: str
    invoice_total_amount: Decimal
    confirmed_amount: Decimal
    remaining_amount: Decimal