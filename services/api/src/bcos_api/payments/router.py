"""HTTP routes for BCOS Payments."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.payments.domain import Payment as DomainPayment
from bcos_api.payments.schemas import (
    ConfirmPixPaymentRequest,
    PaymentResult,
)
from bcos_api.payments.schemas import (
    Payment as PaymentResponse,
)
from bcos_api.payments.schemas import (
    PaymentMethod as PublicPaymentMethod,
)
from bcos_api.payments.schemas import (
    PaymentStatus as PublicPaymentStatus,
)
from bcos_api.payments.service import (
    PaymentConflict,
    PaymentIdempotencyConflict,
    PaymentNotFound,
)
from bcos_api.payments.service import (
    confirm_pix_payment as service_confirm_pix_payment,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context

router = APIRouter(prefix="/api/v1", tags=["Payments"])

SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]


def _payment_to_response(payment: DomainPayment) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        invoice_id=payment.invoice_id,
        idempotency_key=payment.idempotency_key,
        method=PublicPaymentMethod(payment.method.value),
        status=PublicPaymentStatus(payment.status.value),
        currency=payment.currency,
        amount=payment.amount,
        reference=payment.reference,
        metadata=payment.metadata,
        paid_at=payment.paid_at,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


@router.post(
    "/payments/pix/confirm",
    operation_id="confirmPixPayment",
    response_model=PaymentResult,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def confirm_pix_payment(
    payload: ConfirmPixPaymentRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> PaymentResult:
    """Register a PIX payment already confirmed by the Coworking."""

    try:
        (
            payment,
            invoice_status,
            invoice_total_amount,
            confirmed_amount,
            remaining_amount,
        ) = await service_confirm_pix_payment(
            session,
            context=context,
            invoice_id=payload.invoice_id,
            idempotency_key=payload.idempotency_key,
            amount=payload.amount,
            reference=payload.reference,
            metadata=payload.metadata,
            paid_at=payload.paid_at,
        )
        await session.commit()
    except PaymentNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        PaymentConflict,
        PaymentIdempotencyConflict,
        IntegrityError,
    ) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception:
        await session.rollback()
        raise

    return PaymentResult(
        payment=_payment_to_response(payment),
        invoice_status=invoice_status,
        invoice_total_amount=invoice_total_amount,
        confirmed_amount=confirmed_amount,
        remaining_amount=remaining_amount,
    )