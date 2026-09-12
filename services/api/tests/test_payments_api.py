from decimal import Decimal

import pytest
from pydantic import ValidationError

from bcos_api.main import create_app
from bcos_api.payments.schemas import ConfirmPixPaymentRequest


def test_payments_router_is_registered_in_public_api() -> None:
    app = create_app()

    openapi = app.openapi()
    paths = openapi["paths"]

    assert "/api/v1/payments/pix/confirm" in paths
    assert "post" in paths["/api/v1/payments/pix/confirm"]


def test_confirm_pix_payload_accepts_positive_brl_amount_shape() -> None:
    payload = ConfirmPixPaymentRequest(
        invoice_id="bbd77b5b-abec-4a04-b155-64d8e1eb10f9",
        idempotency_key="pix-homologacao-001",
        amount=Decimal("110.00"),
    )

    assert payload.amount == Decimal("110.00")
    assert payload.idempotency_key == "pix-homologacao-001"


def test_confirm_pix_payload_rejects_non_positive_amount() -> None:
    with pytest.raises(ValidationError):
        ConfirmPixPaymentRequest(
            invoice_id="bbd77b5b-abec-4a04-b155-64d8e1eb10f9",
            idempotency_key="pix-invalid",
            amount=Decimal("0.00"),
        )