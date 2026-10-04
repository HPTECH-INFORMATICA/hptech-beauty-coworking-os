"""Tests for authenticated product access resolution."""

from bcos_api.access.router import _tenant_destination
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import Permission


def test_owner_resolves_to_administration() -> None:
    assert _tenant_destination(
        MembershipRole.OWNER,
        set(),
    ) == "/administracao"


def test_cadastral_admin_permission_resolves_to_administration() -> None:
    assert _tenant_destination(
        MembershipRole.RECEPTION,
        {Permission.ADMIN_VIEW},
    ) == "/administracao"


def test_operational_permissions_resolve_to_workspace() -> None:
    assert _tenant_destination(
        MembershipRole.RECEPTION,
        {Permission.AGENDA_VIEW},
    ) == "/"


def test_professional_own_scope_resolves_to_own_scope_portal() -> None:
    assert _tenant_destination(
        MembershipRole.PROFESSIONAL,
        {Permission.PROFESSIONAL_OWN},
    ) == "/profissional"
