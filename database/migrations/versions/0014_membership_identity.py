"""Add tenant-managed membership identity labels.

Revision ID: 0014_membership_identity
Revises: 0013_tenant_prof_docs
"""
from collections.abc import Sequence
from alembic import op

revision: str = "0014_membership_identity"
down_revision: str | None = "0013_tenant_prof_docs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE tenant_memberships
          ADD COLUMN display_name VARCHAR(160),
          ADD COLUMN email VARCHAR(255);
        CREATE INDEX ix_tenant_memberships_tenant_email
          ON tenant_memberships (tenant_id, lower(email))
          WHERE deleted_at IS NULL AND email IS NOT NULL;
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_tenant_memberships_tenant_email;
        ALTER TABLE tenant_memberships
          DROP COLUMN IF EXISTS email,
          DROP COLUMN IF EXISTS display_name;
    """)
