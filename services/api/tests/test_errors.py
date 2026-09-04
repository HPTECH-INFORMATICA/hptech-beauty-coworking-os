"""Regression tests for the frozen BCOS HTTP error contract."""

from __future__ import annotations

import json

import pytest
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError

from bcos_api.errors import (
    http_exception_handler,
    permission_denied_handler,
    validation_exception_handler,
)
from bcos_api.tenancy.rbac import PermissionDenied


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
        }
    )


def _body(response: object) -> dict[str, object]:
    body = getattr(response, "body")
    assert isinstance(body, bytes)
    parsed = json.loads(body)
    assert isinstance(parsed, dict)
    return parsed


@pytest.mark.asyncio
async def test_http_exception_uses_frozen_error_response() -> None:
    response = await http_exception_handler(
        _request(),
        HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required.",
            headers={"WWW-Authenticate": "Bearer"},
        ),
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"
    assert _body(response) == {
        "code": "UNAUTHORIZED",
        "message": "Authentication credentials are required.",
        "request_id": None,
        "details": None,
    }


@pytest.mark.asyncio
async def test_permission_denied_uses_frozen_error_response() -> None:
    response = await permission_denied_handler(
        _request(),
        PermissionDenied("Identity does not have the required permission."),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert _body(response) == {
        "code": "FORBIDDEN",
        "message": "Identity does not have the required permission.",
        "request_id": None,
        "details": None,
    }


@pytest.mark.asyncio
async def test_request_validation_uses_frozen_error_response() -> None:
    response = await validation_exception_handler(
        _request(),
        RequestValidationError(
            [
                {
                    "type": "missing",
                    "loc": ("header", "X-Tenant-Id"),
                    "msg": "Field required",
                    "input": None,
                }
            ]
        ),
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    body = _body(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Request validation failed."
    assert body["request_id"] is None

    details = body["details"]
    assert isinstance(details, dict)
    errors = details["errors"]
    assert isinstance(errors, list)
    assert errors[0]["loc"] == ["header", "X-Tenant-Id"]
