"""HTTP regression tests for the BCOS Availability router."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from bcos_api.availability.domain import (
    Availability,
    InvalidAvailabilityInterval,
)
from bcos_api.availability.router import get_availability
from bcos_api.availability.service import (
    AvailabilityCategoryNotFound,
    AvailabilityResourceNotFound,
    AvailabilityUnitNotFound,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole


def owner_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        membership_id=uuid4(),
        external_user_id="identity-owner",
        role=MembershipRole.OWNER,
    )


@pytest.mark.asyncio
async def test_get_availability_returns_frozen_public_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    resource_id = uuid4()
    category_id = uuid4()
    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(hours=1)

    async def fake_get_tenant_availability(
        *args: object,
        **kwargs: object,
    ) -> list[Availability]:
        assert kwargs["context"] == context
        assert kwargs["unit_id"] == unit_id
        assert kwargs["starts_at"] == starts_at
        assert kwargs["ends_at"] == ends_at
        assert kwargs["resource_id"] == resource_id
        assert kwargs["category_id"] == category_id

        return [
            Availability(
                resource_id=resource_id,
                available=False,
                reason="MANUAL_BLOCK",
            )
        ]

    monkeypatch.setattr(
        "bcos_api.availability.router.get_tenant_availability",
        fake_get_tenant_availability,
    )

    response = await get_availability(
        session=object(),  # type: ignore[arg-type]
        context=context,
        unit_id=unit_id,
        starts_at=starts_at,
        ends_at=ends_at,
        resource_id=resource_id,
        category_id=category_id,
    )

    assert response.starts_at == starts_at
    assert response.ends_at == ends_at
    assert len(response.resources) == 1
    assert response.resources[0].resource_id == resource_id
    assert response.resources[0].available is False
    assert response.resources[0].reason == "MANUAL_BLOCK"

    assert response.model_dump().keys() == {
        "starts_at",
        "ends_at",
        "resources",
    }
    assert response.resources[0].model_dump().keys() == {
        "resource_id",
        "available",
        "reason",
    }


@pytest.mark.asyncio
async def test_get_availability_preserves_available_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    resource_id = uuid4()
    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(hours=1)

    async def fake_get_tenant_availability(
        *args: object,
        **kwargs: object,
    ) -> list[Availability]:
        return [
            Availability(
                resource_id=resource_id,
                available=True,
                reason=None,
            )
        ]

    monkeypatch.setattr(
        "bcos_api.availability.router.get_tenant_availability",
        fake_get_tenant_availability,
    )

    response = await get_availability(
        session=object(),  # type: ignore[arg-type]
        context=context,
        unit_id=uuid4(),
        starts_at=starts_at,
        ends_at=ends_at,
    )

    assert response.resources == [
        response.resources[0]
    ]
    assert response.resources[0].resource_id == resource_id
    assert response.resources[0].available is True
    assert response.resources[0].reason is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception_type", "message"),
    [
        (
            InvalidAvailabilityInterval,
            "starts_at must be earlier than ends_at.",
        ),
        (
            AvailabilityUnitNotFound,
            "Unit was not found.",
        ),
        (
            AvailabilityResourceNotFound,
            "Resource was not found for the requested unit.",
        ),
        (
            AvailabilityCategoryNotFound,
            "Resource category was not found.",
        ),
    ],
)
async def test_get_availability_maps_domain_errors_to_422(
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[Exception],
    message: str,
) -> None:
    async def fake_get_tenant_availability(
        *args: object,
        **kwargs: object,
    ) -> list[Availability]:
        raise exception_type(message)

    monkeypatch.setattr(
        "bcos_api.availability.router.get_tenant_availability",
        fake_get_tenant_availability,
    )

    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)

    with pytest.raises(HTTPException) as exc_info:
        await get_availability(
            session=object(),  # type: ignore[arg-type]
            context=owner_context(),
            unit_id=uuid4(),
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == message
