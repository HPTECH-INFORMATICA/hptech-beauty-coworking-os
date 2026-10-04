"""Tenant-managed access roles and role permission matrix.

Revision ID: 0016_tenant_access_roles
Revises: 0015_member_permissions
"""
from collections.abc import Sequence
from alembic import op

revision: str = "0016_tenant_access_roles"
down_revision: str | None = "0015_member_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE tenant_access_roles (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id UUID NOT NULL,
          name VARCHAR(120) NOT NULL,
          description VARCHAR(500),
          active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          deleted_at TIMESTAMPTZ,
          CONSTRAINT fk_tenant_access_role_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT
        );
        CREATE UNIQUE INDEX uq_tenant_access_role_name
          ON tenant_access_roles (tenant_id, lower(name))
          WHERE deleted_at IS NULL;
        CREATE UNIQUE INDEX uq_tenant_access_role_id_tenant
          ON tenant_access_roles (id, tenant_id);

        CREATE TABLE tenant_access_role_permissions (
          role_id UUID NOT NULL,
          tenant_id UUID NOT NULL,
          permission VARCHAR(96) NOT NULL,
          granted BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (role_id, permission),
          CONSTRAINT fk_tenant_role_permission_role
            FOREIGN KEY (role_id, tenant_id)
            REFERENCES tenant_access_roles(id, tenant_id) ON DELETE CASCADE,
          CONSTRAINT fk_tenant_role_permission_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT
        );
        CREATE INDEX ix_tenant_role_permission_tenant
          ON tenant_access_role_permissions (tenant_id, role_id);

        ALTER TABLE tenant_memberships ADD COLUMN access_role_id UUID;
        ALTER TABLE tenant_memberships ADD CONSTRAINT fk_membership_access_role
          FOREIGN KEY (access_role_id, tenant_id)
          REFERENCES tenant_access_roles(id, tenant_id) ON DELETE RESTRICT;

        ALTER TABLE tenant_user_invitations ADD COLUMN access_role_id UUID;
        ALTER TABLE tenant_user_invitations ADD CONSTRAINT fk_invitation_access_role
          FOREIGN KEY (access_role_id, tenant_id)
          REFERENCES tenant_access_roles(id, tenant_id) ON DELETE RESTRICT;
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE tenant_user_invitations DROP CONSTRAINT IF EXISTS fk_invitation_access_role;
        ALTER TABLE tenant_user_invitations DROP COLUMN IF EXISTS access_role_id;
        ALTER TABLE tenant_memberships DROP CONSTRAINT IF EXISTS fk_membership_access_role;
        ALTER TABLE tenant_memberships DROP COLUMN IF EXISTS access_role_id;
        DROP TABLE IF EXISTS tenant_access_role_permissions;
        DROP TABLE IF EXISTS tenant_access_roles;
    """)
