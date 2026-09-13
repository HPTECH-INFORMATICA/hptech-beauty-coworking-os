from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from bcos_worker.invoice_materializer import materialize_per_usage_invoice
from bcos_worker.invoice_repository import InvoiceIdentity
from bcos_worker.pricing_context import ReceptionHours, UsagePricingContext
from bcos_worker.pricing_rule import (
    OvertimeRule,
    PricingModality,
    PricingRuleDefinitionV1,
)
from bcos_worker.professional_billing_contract import ProfessionalBillingContract

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
USAGE_ID = UUID("00000000-0000-0000-0000-000000000002")
BOOKING_ID = UUID("00000000-0000-0000-0000-000000000003")
RESOURCE_ID = UUID("00000000-0000-0000-0000-000000000004")
PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000005")
UNIT_ID = UUID("00000000-0000-0000-0000-000000000006")
CONTRACT_ID = UUID("00000000-0000-0000-0000-000000000007")
INVOICE_ID = UUID("00000000-0000-0000-0000-000000000008")
BASE_ITEM_ID = UUID("00000000-0000-0000-0000-000000000009")
OVERTIME_ITEM_ID = UUID("00000000-0000-0000-0000-000000000010")


class _Mappings:
    def __init__(self, *, rows=None):
        self._rows = [] if rows is None else rows

    def all(self):
        return self._rows


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _MappingResult:
    def __init__(self, rows):
        self._mappings = _Mappings(rows=rows)

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
            proportional_until_minutes=29,
            full_hour_from_minutes=30,
            forgiveness_allowed=True,
        ),
        conflict_penalty=None,
    )

    contract = ProfessionalBillingContract(
        id=CONTRACT_ID,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        invoice_mode="PER_USAGE",
        valid_from=datetime(2026, 9, 1, tzinfo=UTC),
        valid_until=None,
        lifecycle_mode=None,
        lifecycle_weekday=None,
        lifecycle_biweekly_anchor=None,
        lifecycle_month_day=None,
        lifecycle_closing_time=None,
        cycle_allocation_policy=None,
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


def _invoice_identity() -> InvoiceIdentity:
    return InvoiceIdentity(
        id=INVOICE_ID,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        source_usage_id=USAGE_ID,
    )


def _base_item_row():
    return {
        "id": BASE_ITEM_ID,
        "invoice_id": INVOICE_ID,
        "tenant_id": TENANT_ID,
        "usage_id": USAGE_ID,
        "item_type": "BASE_LEASE",
        "description": "Base lease",
        "quantity": Decimal("1"),
        "unit_amount": Decimal("100.00"),
        "total_amount": Decimal("100.00"),
        "metadata": {},
    }


def _overtime_item_row():
    return {
        "id": OVERTIME_ITEM_ID,
        "invoice_id": INVOICE_ID,
        "tenant_id": TENANT_ID,
        "usage_id": USAGE_ID,
        "item_type": "OVERTIME",
        "description": "Overtime",
        "quantity": Decimal("30"),
        "unit_amount": Decimal("60.00"),
        "total_amount": Decimal("60.00"),
        "metadata": {
            "forgiveness_allowed": True,
            "reception_segments": [
                {
                    "segment": "BEFORE_RECEPTION_CLOSE",
                    "completed_minutes": 30,
                    "amount": "60.00",
                }
            ],
        },
    }


@pytest.mark.asyncio
async def test_materializes_per_usage_invoice_with_base_and_overtime(
    monkeypatch,
) -> None:
    context = _context()
    session = AsyncMock()

    async def _get_invoice(*args, **kwargs):
        return _invoice_identity()

    monkeypatch.setattr(
        "bcos_worker.invoice_materializer.get_or_create_per_usage_invoice",
        _get_invoice,
    )

    session.execute.side_effect = [
        object(),
        _MappingResult([_base_item_row()]),
        object(),
        _MappingResult([_overtime_item_row()]),
        _ScalarResult(INVOICE_ID),
    ]

    result = await materialize_per_usage_invoice(session, context)

    assert result.invoice.id == INVOICE_ID
    assert result.subtotal_amount == Decimal("160.00")
    assert result.discount_amount == Decimal("0.00")
    assert result.total_amount == Decimal("160.00")
    assert session.execute.await_count == 5

    base_insert_params = session.execute.await_args_list[0].args[1]
    assert base_insert_params["item_type"] == "BASE_LEASE"
    assert base_insert_params["total_amount"] == Decimal("100.00")

    overtime_insert_params = session.execute.await_args_list[2].args[1]
    assert overtime_insert_params["item_type"] == "OVERTIME"
    assert overtime_insert_params["quantity"] == Decimal("30")
    assert overtime_insert_params["total_amount"] == Decimal("60.00")

    totals_params = session.execute.await_args_list[4].args[1]
    assert totals_params["subtotal_amount"] == Decimal("160.00")
    assert totals_params["discount_amount"] == Decimal("0.00")
    assert totals_params["total_amount"] == Decimal("160.00")


@pytest.mark.asyncio
async def test_retry_reuses_same_financial_identity(
    monkeypatch,
) -> None:
    context = _context()
    session = AsyncMock()

    async def _get_invoice(*args, **kwargs):
        return _invoice_identity()

    monkeypatch.setattr(
        "bcos_worker.invoice_materializer.get_or_create_per_usage_invoice",
        _get_invoice,
    )

    session.execute.side_effect = [
        object(),
        _MappingResult([_base_item_row()]),
        object(),
        _MappingResult([_overtime_item_row()]),
        _ScalarResult(INVOICE_ID),
    ]

    first = await materialize_per_usage_invoice(session, context)

    session.reset_mock()

    session.execute.side_effect = [
        object(),
        _MappingResult([_base_item_row()]),
        object(),
        _MappingResult([_overtime_item_row()]),
        _ScalarResult(INVOICE_ID),
    ]

    second = await materialize_per_usage_invoice(session, context)

    assert first.invoice.id == second.invoice.id == INVOICE_ID
    assert first.total_amount == second.total_amount == Decimal("160.00")
    assert session.execute.await_count == 5


@pytest.mark.asyncio
async def test_rejects_non_per_usage_contract() -> None:
    context = _context()

    accumulated_contract = ProfessionalBillingContract(
        id=context.professional_billing_contract.id,
        tenant_id=context.professional_billing_contract.tenant_id,
        professional_id=context.professional_billing_contract.professional_id,
        invoice_mode="ACCUMULATED_OPEN_INVOICE",
        valid_from=context.professional_billing_contract.valid_from,
        valid_until=None,
        lifecycle_mode="MANUAL",
        lifecycle_weekday=None,
        lifecycle_biweekly_anchor=None,
        lifecycle_month_day=None,
        lifecycle_closing_time=None,
        cycle_allocation_policy="USAGE_COMPLETION",
    )

    context = UsagePricingContext(
        tenant_id=context.tenant_id,
        usage_id=context.usage_id,
        booking_id=context.booking_id,
        resource_id=context.resource_id,
        professional_id=context.professional_id,
        unit_id=context.unit_id,
        usage_status=context.usage_status,
        checked_in_at=context.checked_in_at,
        checked_out_at=context.checked_out_at,
        booking_starts_at=context.booking_starts_at,
        booking_ends_at=context.booking_ends_at,
        pricing_snapshot=context.pricing_snapshot,
        pricing_rule=context.pricing_rule,
        professional_billing_contract=accumulated_contract,
        unit_timezone=context.unit_timezone,
        local_checked_out_at=context.local_checked_out_at,
        reception_hours=context.reception_hours,
    )

    session = AsyncMock()

    with pytest.raises(
        RuntimeError,
        match="non-PER_USAGE",
    ):
        await materialize_per_usage_invoice(session, context)

    assert session.execute.await_count == 0
