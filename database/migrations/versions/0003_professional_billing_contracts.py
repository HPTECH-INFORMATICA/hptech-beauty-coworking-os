"""Add historical professional billing contracts.

Revision ID: 0003_prof_billing_contracts
Revises: 0002_outbox_processing_started
Create Date: 2026-09-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_prof_billing_contracts"
down_revision: str | None = "0002_outbox_processing_started"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TYPE invoice_materialization_mode AS ENUM (
            'PER_USAGE',
            'ACCUMULATED_OPEN_INVOICE'
        );
        """
    )

    op.execute(
        """
        CREATE TABLE professional_billing_contracts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            professional_id UUID NOT NULL,
            invoice_mode invoice_materialization_mode NOT NULL,
            valid_from TIMESTAMPTZ NOT NULL,
            valid_until TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_professional_billing_contracts_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT fk_professional_billing_contracts_professional
                FOREIGN KEY (professional_id, tenant_id)
                REFERENCES professionals (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_professional_billing_contracts_validity
                CHECK (
                    valid_until IS NULL
                    OR valid_until > valid_from
                )
        );
        """
    )

    op.execute(
        """
        ALTER TABLE professional_billing_contracts
        ADD CONSTRAINT ex_professional_billing_contracts_no_overlap
        EXCLUDE USING gist (
            tenant_id WITH =,
            professional_id WITH =,
            tstzrange(valid_from, valid_until, '[)') WITH &&
        );
        """
    )

    op.execute(
        """
        CREATE INDEX ix_professional_billing_contracts_lookup
        ON professional_billing_contracts (
            tenant_id,
            professional_id,
            valid_from
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE professional_billing_contracts;
        """
    )

    op.execute(
        """
        DROP TYPE invoice_materialization_mode;
        """
    )
