"""Add tenant user identity labels and email-first invitations.

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

        CREATE TABLE tenant_user_invitations (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id UUID NOT NULL,
          display_name VARCHAR(160) NOT NULL,
          email VARCHAR(255) NOT NULL,
          role membership_role NOT NULL,
          status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
          invited_by_external_user_id VARCHAR(255) NOT NULL,
          expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days'),
          accepted_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          deleted_at TIMESTAMPTZ,
          CONSTRAINT fk_tenant_user_invitations_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT,
          CONSTRAINT ck_tenant_user_invitations_role CHECK (role <> 'OWNER'),
          CONSTRAINT ck_tenant_user_invitations_status CHECK (status IN ('PENDING','ACCEPTED','REVOKED','EXPIRED'))
        );
        CREATE UNIQUE INDEX uq_tenant_user_invitation_pending
          ON tenant_user_invitations (tenant_id, lower(email))
          WHERE status='PENDING' AND deleted_at IS NULL;
    """)

def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS tenant_user_invitations;
        DROP INDEX IF EXISTS ix_tenant_memberships_tenant_email;
        ALTER TABLE tenant_memberships
          DROP COLUMN IF EXISTS email,
          DROP COLUMN IF EXISTS display_name;
    """)
