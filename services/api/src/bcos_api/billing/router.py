"""Read-only HTTP routes for BCOS Billing."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.billing.schemas import InvoiceDetail, InvoiceStatus, InvoiceSummary
from bcos_api.billing.service import InvoiceNotFound, get_tenant_invoice, list_tenant_invoices
from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context

router = APIRouter(prefix="/api/v1/invoices", tags=["Billing"])

SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency = Annotated[TenantContext, Depends(get_tenant_context)]


@router.get("", response_model=list[InvoiceSummary], operation_id="listInvoices")
async def list_invoices(
    session: SessionDependency,
    context: TenantContextDependency,
    professional_id: UUID | None = None,
    invoice_status: InvoiceStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[InvoiceSummary]:
    return await list_tenant_invoices(
        session,
        context=context,
        professional_id=professional_id,
        status=invoice_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceDetail,
    operation_id="getInvoice",
    responses=error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
)
async def get_invoice(
    invoice_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> InvoiceDetail:
    try:
        return await get_tenant_invoice(
            session,
            context=context,
            invoice_id=invoice_id,
        )
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
