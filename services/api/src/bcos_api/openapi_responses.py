"""Reusable OpenAPI response declarations for the frozen BCOS error contract."""

from __future__ import annotations

from typing import Any

from bcos_api.errors import ErrorResponse


def error_responses(
    *status_codes: int,
) -> dict[int | str, dict[str, Any]]:
    """Build FastAPI response declarations using the frozen ErrorResponse model."""

    return {
        status_code: {"model": ErrorResponse}
        for status_code in status_codes
    }
