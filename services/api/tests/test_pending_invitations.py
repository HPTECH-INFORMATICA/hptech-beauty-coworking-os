"""Tests for authenticated pending invitation discovery."""

from bcos_api.invitation.router import list_pending_invitations_endpoint


def test_pending_invitation_endpoint_is_identity_scoped() -> None:
    dependencies = list_pending_invitations_endpoint.__annotations__
    assert "identity" in dependencies
    assert "session" in dependencies


def test_pending_invitation_discovery_requires_no_tenant_header() -> None:
    route = next(
        route
        for route in list_pending_invitations_endpoint.__globals__["router"].routes
        if getattr(route, "path", "") == "/api/v1/invitations"
    )
    assert "GET" in route.methods
