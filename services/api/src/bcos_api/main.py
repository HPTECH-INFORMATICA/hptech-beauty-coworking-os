"""BCOS FastAPI application."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from bcos_api.availability.router import router as availability_router
from bcos_api.billing.router import router as billing_router
from bcos_api.bookings.router import router as bookings_router
from bcos_api.errors import (
    http_exception_handler,
    permission_denied_handler,
    validation_exception_handler,
)
from bcos_api.openapi import normalize_openapi_schema
from bcos_api.payments.router import router as payments_router
from bcos_api.pricing.router import router as pricing_router
from bcos_api.professional_portal.router import router as professional_portal_router
from bcos_api.professionals.router import router as professionals_router
from bcos_api.resource_categories.router import router as resource_categories_router
from bcos_api.resources.router import router as resources_router
from bcos_api.tenancy.rbac import PermissionDenied
from bcos_api.units.router import router as units_router
from bcos_api.usages.reception_router import router as reception_router
from bcos_api.usages.router import router as usages_router


class BCOSFastAPI(FastAPI):
    """FastAPI application with the frozen BCOS OpenAPI normalization."""

    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is None:
            self.openapi_schema = normalize_openapi_schema(super().openapi())
        return self.openapi_schema


def create_app() -> FastAPI:
    app = BCOSFastAPI(title="HPTECH Beauty Coworking OS API")

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PermissionDenied, permission_denied_handler)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "bcos-api"}

    app.include_router(units_router)
    app.include_router(professionals_router)
    app.include_router(resource_categories_router)
    app.include_router(resources_router)
    app.include_router(availability_router)
    app.include_router(bookings_router)
    app.include_router(usages_router)
    app.include_router(reception_router)
    app.include_router(pricing_router)
    app.include_router(billing_router)
    app.include_router(payments_router)
    app.include_router(professional_portal_router)

    return app


app = create_app()
