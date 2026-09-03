"""Server-side role-based access control for BCOS."""

from __future__ import annotations

from enum import StrEnum

from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole


class Permission(StrEnum):
    """Core BCOS authorization capabilities."""

    TENANT_ADMIN = "TENANT_ADMIN"
    OPERATIONS = "OPERATIONS"
    PROFESSIONAL_OWN = "PROFESSIONAL_OWN"


class PermissionDenied(Exception):
    """Raised when a tenant context lacks a required permission."""


ROLE_PERMISSIONS: dict[MembershipRole, frozenset[Permission]] = {
    MembershipRole.OWNER: frozenset(
        {
            Permission.TENANT_ADMIN,
            Permission.OPERATIONS,
        }
    ),
    MembershipRole.ADMIN: frozenset(
        {
            Permission.TENANT_ADMIN,
            Permission.OPERATIONS,
        }
    ),
    MembershipRole.RECEPTION: frozenset(
        {
            Permission.OPERATIONS,
        }
    ),
    MembershipRole.PROFESSIONAL: frozenset(
        {
            Permission.PROFESSIONAL_OWN,
        }
    ),
}


def has_permission(
    context: TenantContext,
    permission: Permission,
) -> bool:
    """Return whether the authorized tenant context has a permission."""

    return permission in ROLE_PERMISSIONS[context.role]


def require_permission(
    context: TenantContext,
    permission: Permission,
) -> None:
    """Require one permission for the authorized tenant context."""

    if not has_permission(context, permission):
        raise PermissionDenied(
            "Authenticated identity does not have permission "
            "to perform this operation."
        )
