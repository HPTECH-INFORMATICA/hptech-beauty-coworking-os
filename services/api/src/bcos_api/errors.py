"""Central HTTP error responses for the BCOS API."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from bcos_api.tenancy.rbac import PermissionDenied


class ErrorResponse(BaseModel):
    """Frozen public API error representation."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str | None = None
    details: dict[str, Any] | None = None


_STATUS_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
}


def _error_content(
    *,
    status_code: int,
    message: str,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ErrorResponse(
        code=_STATUS_CODES.get(status_code, "HTTP_ERROR"),
        message=message,
        request_id=request_id,
        details=details,
    ).model_dump()


async def http_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert FastAPI HTTP exceptions to the frozen ErrorResponse shape."""

    assert isinstance(exc, HTTPException)

    message = exc.detail if isinstance(exc.detail, str) else "Request failed."

    return JSONResponse(
        status_code=exc.status_code,
        content=_error_content(
            status_code=exc.status_code,
            message=message,
        ),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert request validation failures to the frozen error shape."""

    assert isinstance(exc, RequestValidationError)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_content(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            message="Request validation failed.",
            details={"errors": exc.errors()},
        ),
    )


async def permission_denied_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert RBAC denials to the frozen error shape."""

    assert isinstance(exc, PermissionDenied)

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=_error_content(
            status_code=status.HTTP_403_FORBIDDEN,
            message=str(exc),
        ),
    )
