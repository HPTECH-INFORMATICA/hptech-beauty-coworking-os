"""Server-side role-based access control for BCOS."""

from __future__ import annotations

from enum import StrEnum

from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole


class Permission(StrEnum):
    """BCOS authorization capabilities.

    Legacy aggregate capabilities remain while routes migrate to granular gates.
    """
    TENANT_ADMIN = "TENANT_ADMIN"
    OPERATIONS = "OPERATIONS"
    PROFESSIONAL_OWN = "PROFESSIONAL_OWN"
    DASHBOARD_VIEW = "DASHBOARD_VIEW"
    AGENDA_VIEW = "AGENDA_VIEW"
    AGENDA_MANAGE = "AGENDA_MANAGE"
    AVAILABILITY_VIEW = "AVAILABILITY_VIEW"
    CHECKIN_MANAGE = "CHECKIN_MANAGE"
    FINANCE_VIEW = "FINANCE_VIEW"
    FINANCE_MANAGE = "FINANCE_MANAGE"
    ADMIN_CONFIG = "ADMIN_CONFIG"
    USER_ADMIN = "USER_ADMIN"


class PermissionDenied(Exception):
    """Raised when a tenant context lacks a required permission."""


ROLE_PERMISSIONS: dict[MembershipRole, frozenset[Permission]] = {
    MembershipRole.OWNER: frozenset(Permission),
    MembershipRole.ADMIN: frozenset({
        Permission.TENANT_ADMIN, Permission.OPERATIONS,
        Permission.DASHBOARD_VIEW, Permission.AGENDA_VIEW, Permission.AGENDA_MANAGE,
        Permission.AVAILABILITY_VIEW, Permission.CHECKIN_MANAGE,
        Permission.FINANCE_VIEW, Permission.FINANCE_MANAGE,
        Permission.ADMIN_CONFIG, Permission.USER_ADMIN,
    }),
    MembershipRole.RECEPTION: frozenset({
        Permission.OPERATIONS, Permission.DASHBOARD_VIEW, Permission.AGENDA_VIEW,
        Permission.AGENDA_MANAGE, Permission.AVAILABILITY_VIEW, Permission.CHECKIN_MANAGE,
    }),
    MembershipRole.PROFESSIONAL: frozenset({Permission.PROFESSIONAL_OWN}),
}


def has_permission(context: TenantContext, permission: Permission) -> bool:
    """Return whether the authorized tenant context has a permission."""
    return permission in context.permissions


def require_permission(context: TenantContext, permission: Permission) -> None:
    """Require one permission for the authorized tenant context."""
    if not has_permission(context, permission):
        raise PermissionDenied("Authenticated identity does not have permission to perform this operation.")
