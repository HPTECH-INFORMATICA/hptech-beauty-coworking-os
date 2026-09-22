"""Add platform-scoped audit evidence.

Revision ID: 0009_platform_audit
Revises: 0008_platform_authority
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009_platform_audit"
down_revision: str | None = "0008_platform_authority"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE platform_audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            actor_external_user_id VARCHAR(255),
            action VARCHAR(160) NOT NULL,
            entity_type VARCHAR(160) NOT NULL,
            entity_id UUID,
            tenant_id UUID,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT fk_platform_audit_tenant
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT,
            CONSTRAINT ck_platform_audit_action CHECK (btrim(action) <> ''),
            CONSTRAINT ck_platform_audit_entity_type CHECK (btrim(entity_type) <> ''),
            CONSTRAINT ck_platform_audit_metadata CHECK (jsonb_typeof(metadata) = 'object')
        );

        CREATE INDEX ix_platform_audit_occurred
            ON platform_audit_logs (occurred_at DESC);
        CREATE INDEX ix_platform_audit_tenant
            ON platform_audit_logs (tenant_id, occurred_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS platform_audit_logs;")
