"""Add secure email-first professional access invitations.

Revision ID: 0011_professional_access_invites
Revises: 0010_admin_catalog
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0011_professional_access_invites"
down_revision: str | None = "0010_admin_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE professional_access_invitations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            professional_id UUID NOT NULL,
            email VARCHAR(255) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            invited_by_external_user_id VARCHAR(255) NOT NULL,
            accepted_by_external_user_id VARCHAR(255),
            expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days'),
            accepted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT fk_professional_access_invitation_professional
                FOREIGN KEY (professional_id, tenant_id)
                REFERENCES professionals (id, tenant_id) ON DELETE RESTRICT,
            CONSTRAINT fk_professional_access_invitation_tenant
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT,
            CONSTRAINT ck_professional_access_invitation_email CHECK (btrim(email) <> ''),
            CONSTRAINT ck_professional_access_invitation_status
                CHECK (status IN ('PENDING','ACCEPTED','REVOKED'))
        );
        CREATE UNIQUE INDEX uq_professional_access_invitation_pending
            ON professional_access_invitations (tenant_id, professional_id)
            WHERE status = 'PENDING' AND deleted_at IS NULL;
        CREATE INDEX ix_professional_access_invitation_email
            ON professional_access_invitations (lower(email), status, expires_at)
            WHERE deleted_at IS NULL;
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS professional_access_invitations;")
