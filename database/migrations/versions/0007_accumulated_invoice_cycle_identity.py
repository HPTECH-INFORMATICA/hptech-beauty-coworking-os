"""Add accumulated Invoice cycle identity.

Revision ID: 0007_invoice_cycle_identity
Revises: 0006_invoice_item_segmentation
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0007_invoice_cycle_identity"
down_revision: str | None = "0006_invoice_item_segmentation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Candidate key required to enforce tenant + professional consistency
    # when an Invoice references one historical Billing contract.
    op.execute(
        """
        ALTER TABLE professional_billing_contracts
        ADD CONSTRAINT uq_prof_billing_contracts_invoice_identity
        UNIQUE (id, tenant_id, professional_id);
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
            ADD COLUMN professional_billing_contract_id UUID,
            ADD COLUMN billing_cycle_start TIMESTAMPTZ,
            ADD COLUMN billing_cycle_end TIMESTAMPTZ,
            ADD COLUMN manual_closed_at TIMESTAMPTZ;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
        ADD CONSTRAINT fk_invoices_prof_billing_contract
        FOREIGN KEY (
            professional_billing_contract_id,
            tenant_id,
            professional_id
        )
        REFERENCES professional_billing_contracts (
            id,
            tenant_id,
            professional_id
        )
        ON DELETE RESTRICT;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
        ADD CONSTRAINT ck_invoices_billing_cycle_pair
        CHECK (
            (
                billing_cycle_start IS NULL
                AND billing_cycle_end IS NULL
            )
            OR
            (
                billing_cycle_start IS NOT NULL
                AND billing_cycle_end IS NOT NULL
                AND billing_cycle_start < billing_cycle_end
            )
        )
        NOT VALID;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
        ADD CONSTRAINT ck_invoices_materialization_identity
        CHECK (
            (
                source_usage_id IS NOT NULL
                AND professional_billing_contract_id IS NULL
                AND billing_cycle_start IS NULL
                AND billing_cycle_end IS NULL
                AND manual_closed_at IS NULL
            )
            OR
            (
                source_usage_id IS NULL
                AND professional_billing_contract_id IS NOT NULL
                AND (
                    (
                        billing_cycle_start IS NOT NULL
                        AND billing_cycle_end IS NOT NULL
                        AND manual_closed_at IS NULL
                    )
                    OR
                    (
                        billing_cycle_start IS NULL
                        AND billing_cycle_end IS NULL
                    )
                )
            )
        )
        NOT VALID;
        """
    )

    # WEEKLY / BIWEEKLY / MONTHLY:
    # exactly one accumulated Invoice for one historical contract + cycle.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_invoices_accumulated_cycle
        ON invoices (
            tenant_id,
            professional_billing_contract_id,
            billing_cycle_start,
            billing_cycle_end
        )
        WHERE source_usage_id IS NULL
          AND professional_billing_contract_id IS NOT NULL
          AND billing_cycle_start IS NOT NULL
          AND billing_cycle_end IS NOT NULL;
        """
    )

    # MANUAL:
    # the Invoice itself is the lifecycle instance.
    # While manual_closed_at is NULL, at most one such Invoice may be active
    # for the historical professional Billing contract.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_invoices_manual_active_contract
        ON invoices (
            tenant_id,
            professional_billing_contract_id
        )
        WHERE source_usage_id IS NULL
          AND professional_billing_contract_id IS NOT NULL
          AND billing_cycle_start IS NULL
          AND billing_cycle_end IS NULL
          AND manual_closed_at IS NULL;
        """
    )


def downgrade() -> None:
    # Once accumulated financial identity is in use, removing these columns
    # would destroy Billing evidence. Fail closed instead.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM invoices
                WHERE professional_billing_contract_id IS NOT NULL
                   OR billing_cycle_start IS NOT NULL
                   OR billing_cycle_end IS NOT NULL
                   OR manual_closed_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'cannot downgrade 0007: accumulated Invoice identity evidence exists';
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS uq_invoices_manual_active_contract;
        """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS uq_invoices_accumulated_cycle;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
        DROP CONSTRAINT IF EXISTS ck_invoices_materialization_identity;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
        DROP CONSTRAINT IF EXISTS ck_invoices_billing_cycle_pair;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
        DROP CONSTRAINT IF EXISTS fk_invoices_prof_billing_contract;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
            DROP COLUMN IF EXISTS manual_closed_at,
            DROP COLUMN IF EXISTS billing_cycle_end,
            DROP COLUMN IF EXISTS billing_cycle_start,
            DROP COLUMN IF EXISTS professional_billing_contract_id;
        """
    )

    op.execute(
        """
        ALTER TABLE professional_billing_contracts
        DROP CONSTRAINT IF EXISTS uq_prof_billing_contracts_invoice_identity;
        """
    )
