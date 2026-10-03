"""Add granular tenant membership permission overrides.

Revision ID: 0015_member_permissions
Revises: 0014_membership_identity
"""
from collections.abc import Sequence
from alembic import op

revision: str = "0015_member_permissions"
down_revision: str | None = "0014_membership_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE tenant_membership_permission_overrides (
          membership_id UUID NOT NULL,
          tenant_id UUID NOT NULL,
          permission VARCHAR(64) NOT NULL,
          granted BOOLEAN NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (membership_id, permission),
          CONSTRAINT fk_member_permission_membership
            FOREIGN KEY (membership_id) REFERENCES tenant_memberships(id) ON DELETE CASCADE,
          CONSTRAINT fk_member_permission_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT,
          CONSTRAINT ck_member_permission_name CHECK (permission IN (
            'DASHBOARD_VIEW','AGENDA_VIEW','AGENDA_MANAGE','AVAILABILITY_VIEW',
            'CHECKIN_MANAGE','FINANCE_VIEW','FINANCE_MANAGE','ADMIN_CONFIG',
            'USER_ADMIN','PROFESSIONAL_OWN'
          ))
        );
        CREATE INDEX ix_member_permission_tenant
          ON tenant_membership_permission_overrides (tenant_id, membership_id);
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_membership_permission_overrides;")
