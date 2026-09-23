"""Tests for authenticated product access resolution."""

from bcos_api.access.router import _tenant_destination
from bcos_api.tenancy.membership import MembershipRole


def test_owner_and_admin_resolve_to_administration() -> None:
    assert _tenant_destination(MembershipRole.OWNER) == "/administracao"
    assert _tenant_destination(MembershipRole.ADMIN) == "/administracao"


def test_reception_resolves_to_operational_workspace() -> None:
    assert _tenant_destination(MembershipRole.RECEPTION) == "/"


def test_professional_resolves_to_own_scope_portal() -> None:
    assert _tenant_destination(MembershipRole.PROFESSIONAL) == "/profissional"
