from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

import bcos_worker.accumulated_invoice_materializer as materializer
from bcos_worker.financial_effects import FinancialEffect, FinancialEffectType
from bcos_worker.invoice_repository import (
    AccumulatedInvoiceIdentity,
    InvoiceMaterializationError,
)
from bcos_worker.pricing_context import ReceptionHours, UsagePricingContext
from bcos_worker.pricing_rule import OvertimeRule, PricingModality, PricingRuleDefinitionV1
from bcos_worker.professional_billing_contract import ProfessionalBillingContract

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
USAGE_ID = UUID("00000000-0000-0000-0000-000000000002")
BOOKING_ID = UUID("00000000-0000-0000-0000-000000000003")
RESOURCE_ID = UUID("00000000-0000-0000-0000-000000000004")
PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000005")
UNIT_ID = UUID("00000000-0000-0000-0000-000000000006")
CONTRACT_ID = UUID("00000000-0000-0000-0000-000000000007")
PRE_INVOICE_ID = UUID("00000000-0000-0000-0000-000000000008")
POST_INVOICE_ID = UUID("00000000-0000-0000-0000-000000000009")
SEGMENT_ITEM_ID = UUID("00000000-0000-0000-0000-000000000010")


class _Mappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _MappingResult:
    def __init__(self, rows):
        self._mappings = _Mappings(rows)

    def mappings(self):
        return self._mappings


def _context() -> UsagePricingContext:
    zone = ZoneInfo("America/Sao_Paulo")
    booking_starts_at = datetime(2026, 9, 11, 19, 30, tzinfo=UTC)
    booking_ends_at = datetime(2026, 9, 11, 20, 30, tzinfo=UTC)
    checked_out_at = datetime(2026, 9, 11, 21, 20, tzinfo=UTC)

    pricing_rule = PricingRuleDefinitionV1(
        schema_version=1,
        modality=PricingModality.HOURLY,
        base_price_amount=Decimal("100.00"),
        overtime=OvertimeRule(
            hourly_price_amount=Decimal("60.00"),
            proportional_until_minutes=60,
            full_hour_from_minutes=61,
            forgiveness_allowed=True,
        ),
        conflict_penalty=None,
    )
    contract = ProfessionalBillingContract(
        id=CONTRACT_ID,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        invoice_mode="ACCUMULATED_OPEN_INVOICE",
        valid_from=datetime(2026, 9, 1, tzinfo=UTC),
        valid_until=None,
        lifecycle_mode="WEEKLY",
        lifecycle_weekday=4,
        lifecycle_biweekly_anchor=None,
        lifecycle_month_day=None,
        lifecycle_closing_time=time(17, 45),
        cycle_allocation_policy="FIXED_CUTOFF_SPLIT",
    )

    return UsagePricingContext(
        tenant_id=TENANT_ID,
        usage_id=USAGE_ID,
        booking_id=BOOKING_ID,
        resource_id=RESOURCE_ID,
        professional_id=PROFESSIONAL_ID,
        unit_id=UNIT_ID,
        usage_status="COMPLETED",
        checked_in_at=booking_starts_at,
        checked_out_at=checked_out_at,
        booking_starts_at=booking_starts_at,
        booking_ends_at=booking_ends_at,
        pricing_snapshot={},
        pricing_rule=pricing_rule,
        professional_billing_contract=contract,
        unit_timezone="America/Sao_Paulo",
        local_checked_out_at=checked_out_at.astimezone(zone),
        reception_hours=ReceptionHours(
            day_of_week=4,
            opens_at=time(8, 0),
            closes_at=time(18, 0),
            is_closed=False,
        ),
    )


def _invoice(*, invoice_id: UUID, cycle_start: datetime, cycle_end: datetime):
    return AccumulatedInvoiceIdentity(
        id=invoice_id,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        professional_billing_contract_id=CONTRACT_ID,
        billing_cycle_start=cycle_start,
        billing_cycle_end=cycle_end,
        manual_closed_at=None,
        status="OPEN",
    )


@pytest.mark.asyncio
async def test_fixed_cutoff_materializer_routes_two_segments_and_keeps_base_whole(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context()
    session = AsyncMock()
    cutoff = datetime(2026, 9, 11, 20, 45, tzinfo=UTC)
    pre_invoice = _invoice(
        invoice_id=PRE_INVOICE_ID,
        cycle_start=datetime(2026, 9, 4, 20, 45, tzinfo=UTC),
        cycle_end=cutoff,
    )
    post_invoice = _invoice(
        invoice_id=POST_INVOICE_ID,
        cycle_start=cutoff,
        cycle_end=datetime(2026, 9, 18, 20, 45, tzinfo=UTC),
    )

    async def _get_invoice(*args, **kwargs):
        cycle = kwargs["cycle"]
        return pre_invoice if cycle.end == cutoff else post_invoice

    base_calls: list[tuple[UUID, FinancialEffect]] = []
    segment_calls: list[tuple[UUID, FinancialEffect]] = []
    totals_calls: list[UUID] = []

    async def _base(*args, **kwargs):
        base_calls.append((kwargs["invoice_id"], kwargs["effect"]))

    async def _segment(*args, **kwargs):
        segment_calls.append((kwargs["invoice_id"], kwargs["effect"]))

    async def _totals(*args, **kwargs):
        invoice = kwargs["invoice"]
        totals_calls.append(invoice.id)
        if invoice.id == POST_INVOICE_ID:
            return Decimal("115.00"), Decimal("0.00"), Decimal("115.00")
        return Decimal("15.00"), Decimal("0.00"), Decimal("15.00")

    monkeypatch.setattr(materializer, "get_or_create_accumulated_invoice", _get_invoice)
    monkeypatch.setattr(materializer, "_ensure_nonsegmented_invoice_item", _base)
    monkeypatch.setattr(materializer, "_ensure_segmented_invoice_item", _segment)
    monkeypatch.setattr(materializer, "_recalculate_invoice_totals", _totals)

    result = await materializer.materialize_accumulated_invoice(session, context)

    assert result.invoice.id == POST_INVOICE_ID
    assert result.total_amount == Decimal("115.00")

    assert len(base_calls) == 1
    base_invoice_id, base_effect = base_calls[0]
    assert base_invoice_id == POST_INVOICE_ID
    assert base_effect.item_type is FinancialEffectType.BASE_LEASE
    assert base_effect.total_amount == Decimal("100.00")
    assert base_effect.billing_period_start is None
    assert base_effect.billing_period_end is None

    assert [(invoice_id, effect.quantity, effect.total_amount) for invoice_id, effect in segment_calls] == [
        (PRE_INVOICE_ID, Decimal("15"), Decimal("15.00")),
        (POST_INVOICE_ID, Decimal("15"), Decimal("15.00")),
    ]
    assert segment_calls[0][1].billing_period_start == datetime(
        2026, 9, 11, 20, 30, tzinfo=UTC
    )
    assert segment_calls[0][1].billing_period_end == cutoff
    assert segment_calls[1][1].billing_period_start == cutoff
    assert segment_calls[1][1].billing_period_end == datetime(
        2026, 9, 11, 21, 0, tzinfo=UTC
    )
    assert set(totals_calls) == {PRE_INVOICE_ID, POST_INVOICE_ID}


@pytest.mark.asyncio
async def test_segmented_item_retry_reuses_compatible_evidence() -> None:
    session = AsyncMock()
    period_start = datetime(2026, 9, 11, 20, 30, tzinfo=UTC)
    period_end = datetime(2026, 9, 11, 20, 45, tzinfo=UTC)
    effect = FinancialEffect(
        item_type=FinancialEffectType.OVERTIME,
        description="Overtime",
        quantity=Decimal("15"),
        unit_amount=Decimal("60.00"),
        total_amount=Decimal("15.00"),
        reception_segment="BEFORE_RECEPTION_CLOSE",
        billing_period_start=period_start,
        billing_period_end=period_end,
    )
    metadata = {
        "forgiveness_allowed": True,
        "reception_segments": [
            {
                "segment": "BEFORE_RECEPTION_CLOSE",
                "completed_minutes": 15,
                "amount": "15.00",
            }
        ],
    }
    row = {
        "id": SEGMENT_ITEM_ID,
        "invoice_id": PRE_INVOICE_ID,
        "tenant_id": TENANT_ID,
        "usage_id": USAGE_ID,
        "item_type": "OVERTIME",
        "description": "Overtime",
        "quantity": Decimal("15"),
        "unit_amount": Decimal("60.00"),
        "total_amount": Decimal("15.00"),
        "metadata": metadata,
        "billing_period_start": period_start,
        "billing_period_end": period_end,
    }
    session.execute.side_effect = [object(), _MappingResult([row]), object(), _MappingResult([row])]

    for _ in range(2):
        await materializer._ensure_segmented_invoice_item(
            session,
            invoice_id=PRE_INVOICE_ID,
            tenant_id=TENANT_ID,
            usage_id=USAGE_ID,
            effect=effect,
            metadata=metadata,
        )

    assert session.execute.await_count == 4


@pytest.mark.asyncio
async def test_segmented_item_incompatible_evidence_fails_closed() -> None:
    session = AsyncMock()
    period_start = datetime(2026, 9, 11, 20, 30, tzinfo=UTC)
    period_end = datetime(2026, 9, 11, 20, 45, tzinfo=UTC)
    effect = FinancialEffect(
        item_type=FinancialEffectType.OVERTIME,
        description="Overtime",
        quantity=Decimal("15"),
        unit_amount=Decimal("60.00"),
        total_amount=Decimal("15.00"),
        reception_segment="BEFORE_RECEPTION_CLOSE",
        billing_period_start=period_start,
        billing_period_end=period_end,
    )
    metadata = {
        "forgiveness_allowed": True,
        "reception_segments": [
            {
                "segment": "BEFORE_RECEPTION_CLOSE",
                "completed_minutes": 15,
                "amount": "15.00",
            }
        ],
    }
    incompatible_row = {
        "id": SEGMENT_ITEM_ID,
        "invoice_id": PRE_INVOICE_ID,
        "tenant_id": TENANT_ID,
        "usage_id": USAGE_ID,
        "item_type": "OVERTIME",
        "description": "Overtime",
        "quantity": Decimal("15"),
        "unit_amount": Decimal("60.00"),
        "total_amount": Decimal("14.99"),
        "metadata": metadata,
        "billing_period_start": period_start,
        "billing_period_end": period_end,
    }
    session.execute.side_effect = [object(), _MappingResult([incompatible_row])]

    with pytest.raises(
        InvoiceMaterializationError,
        match="total differs from expected value",
    ):
        await materializer._ensure_segmented_invoice_item(
            session,
            invoice_id=PRE_INVOICE_ID,
            tenant_id=TENANT_ID,
            usage_id=USAGE_ID,
            effect=effect,
            metadata=metadata,
        )
