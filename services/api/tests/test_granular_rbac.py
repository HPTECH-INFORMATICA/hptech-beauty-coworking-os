from uuid import uuid4

from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import Permission, has_permission


def context(role: MembershipRole, permissions=None) -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(), membership_id=uuid4(), external_user_id="auth-user",
        role=role, permissions=permissions,
    )


def test_role_defaults_are_backward_compatible() -> None:
    reception = context(MembershipRole.RECEPTION)
    assert has_permission(reception, Permission.AGENDA_VIEW)
    assert has_permission(reception, Permission.CHECKIN_MANAGE)
    assert not has_permission(reception, Permission.FINANCE_VIEW)


def test_effective_permissions_override_role_defaults() -> None:
    restricted = context(MembershipRole.ADMIN, frozenset({Permission.DASHBOARD_VIEW}))
    assert has_permission(restricted, Permission.DASHBOARD_VIEW)
    assert not has_permission(restricted, Permission.USER_ADMIN)
    assert not has_permission(restricted, Permission.FINANCE_MANAGE)


def test_professional_scope_stays_isolated() -> None:
    professional = context(MembershipRole.PROFESSIONAL)
    assert has_permission(professional, Permission.PROFESSIONAL_OWN)
    assert not has_permission(professional, Permission.ADMIN_CONFIG)
    assert not has_permission(professional, Permission.AGENDA_VIEW)
