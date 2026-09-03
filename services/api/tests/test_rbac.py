"""Tests for BCOS server-side RBAC."""

from __future__ import annotations

from uuid import uuid4

import pytest

from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import (
    Permission,
    PermissionDenied,
    has_permission,
    require_permission,
)


def make_context(role: MembershipRole) -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        membership_id=uuid4(),
        external_user_id=f"identity-{role.value.lower()}",
        role=role,
    )


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (MembershipRole.OWNER, Permission.TENANT_ADMIN),
        (MembershipRole.OWNER, Permission.OPERATIONS),
        (MembershipRole.ADMIN, Permission.TENANT_ADMIN),
        (MembershipRole.ADMIN, Permission.OPERATIONS),
        (MembershipRole.RECEPTION, Permission.OPERATIONS),
        (MembershipRole.PROFESSIONAL, Permission.PROFESSIONAL_OWN),
    ],
)
def test_allowed_permissions(
    role: MembershipRole,
    permission: Permission,
) -> None:
    context = make_context(role)

    assert has_permission(context, permission) is True

    require_permission(context, permission)


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (MembershipRole.RECEPTION, Permission.TENANT_ADMIN),
        (MembershipRole.RECEPTION, Permission.PROFESSIONAL_OWN),
        (MembershipRole.PROFESSIONAL, Permission.TENANT_ADMIN),
        (MembershipRole.PROFESSIONAL, Permission.OPERATIONS),
        (MembershipRole.OWNER, Permission.PROFESSIONAL_OWN),
        (MembershipRole.ADMIN, Permission.PROFESSIONAL_OWN),
    ],
)
def test_denied_permissions(
    role: MembershipRole,
    permission: Permission,
) -> None:
    context = make_context(role)

    assert has_permission(context, permission) is False

    with pytest.raises(PermissionDenied):
        require_permission(context, permission)
