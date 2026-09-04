from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from bcos_api.professionals.router import router as professionals_router
from bcos_api.resource_categories.router import router as resource_categories_router
from bcos_api.resources.router import router as resources_router
from bcos_api.tenancy.rbac import PermissionDenied
from bcos_api.units.router import router as units_router


def create_app() -> FastAPI:
    app = FastAPI(title="HPTECH Beauty Coworking OS API")

    @app.exception_handler(PermissionDenied)
    async def permission_denied_handler(
        request: Request,
        exc: PermissionDenied,
    ) -> JSONResponse:
        """Translate server-side RBAC denial into HTTP 403."""

        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": str(exc),
            },
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "bcos-api",
        }

    app.include_router(units_router)
    app.include_router(professionals_router)
    app.include_router(resource_categories_router)
    app.include_router(resources_router)

    return app


app = create_app()
