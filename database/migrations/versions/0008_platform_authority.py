"""Materialize BCOS platform authority and contracting-company profile.

Revision ID: 0008_platform_authority
Revises: 0007_invoice_cycle_identity
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008_platform_authority"
down_revision: str | None = "0007_invoice_cycle_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TYPE platform_operator_role AS ENUM ('PLATFORM_ADMIN');
        CREATE TYPE platform_operator_status AS ENUM ('ACTIVE', 'INACTIVE');

        ALTER TYPE tenant_status ADD VALUE IF NOT EXISTS 'PENDING_ACTIVATION';
        ALTER TYPE tenant_status ADD VALUE IF NOT EXISTS 'SUSPENDED';
        """
    )

    op.execute(
        """
        CREATE TABLE platform_operators (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            external_user_id VARCHAR(255) NOT NULL,
            role platform_operator_role NOT NULL DEFAULT 'PLATFORM_ADMIN',
            status platform_operator_status NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            disabled_at TIMESTAMPTZ,

            CONSTRAINT uq_platform_operators_external_user
                UNIQUE (external_user_id),

            CONSTRAINT ck_platform_operators_external_user
                CHECK (btrim(external_user_id) <> ''),

            CONSTRAINT ck_platform_operators_disabled_state
                CHECK (
                    (status = 'ACTIVE' AND disabled_at IS NULL)
                    OR status = 'INACTIVE'
                )
        );
        """
    )

    op.execute(
        """
        CREATE TABLE tenant_profiles (
            tenant_id UUID PRIMARY KEY,
            legal_name VARCHAR(200) NOT NULL,
            trade_name VARCHAR(200) NOT NULL,
            tax_id VARCHAR(32),
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(40),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT fk_tenant_profiles_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants (id)
                ON DELETE CASCADE,

            CONSTRAINT ck_tenant_profiles_legal_name
                CHECK (btrim(legal_name) <> ''),

            CONSTRAINT ck_tenant_profiles_trade_name
                CHECK (btrim(trade_name) <> ''),

            CONSTRAINT ck_tenant_profiles_email
                CHECK (btrim(email) <> ''),

            CONSTRAINT ck_tenant_profiles_tax_id
                CHECK (tax_id IS NULL OR btrim(tax_id) <> ''),

            CONSTRAINT ck_tenant_profiles_phone
                CHECK (phone IS NULL OR btrim(phone) <> '')
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_profiles;")
    op.execute("DROP TABLE IF EXISTS platform_operators;")
    op.execute("DROP TYPE IF EXISTS platform_operator_status;")
    op.execute("DROP TYPE IF EXISTS platform_operator_role;")
    # PostgreSQL enum values added to tenant_status are intentionally retained.
    # Removing enum values safely requires proving that no historical row uses
    # them; BCOS migrations fail closed rather than rewriting lifecycle evidence.
