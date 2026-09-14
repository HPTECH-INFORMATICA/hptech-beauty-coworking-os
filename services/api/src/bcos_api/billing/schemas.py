"""Public read-only schemas for BCOS Billing."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InvoiceStatus(StrEnum):
    OPEN = "OPEN"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class InvoiceItemType(StrEnum):
    BASE_LEASE = "BASE_LEASE"
    OVERTIME = "OVERTIME"
    ADJUSTMENT = "ADJUSTMENT"
    DISCOUNT = "DISCOUNT"


class InvoiceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    professional_id: UUID
    source_usage_id: UUID | None
    professional_billing_contract_id: UUID | None
    billing_cycle_start: datetime | None
    billing_cycle_end: datetime | None
    manual_closed_at: datetime | None
    status: InvoiceStatus
    currency: str
    subtotal_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime


class InvoiceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    usage_id: UUID | None
    item_type: InvoiceItemType
    description: str
    quantity: Decimal
    unit_amount: Decimal
    total_amount: Decimal
    billing_period_start: datetime | None
    billing_period_end: datetime | None
    related_invoice_item_id: UUID | None
    created_at: datetime


class InvoiceDetail(InvoiceSummary):
    items: list[InvoiceItem]
    confirmed_amount: Decimal
    remaining_amount: Decimal
