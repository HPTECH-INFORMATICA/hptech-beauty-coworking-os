"""invoice item segmentation and billing allocation policy

Revision ID: 0006_invoice_item_segmentation
Revises: 0005_billing_lifecycle
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006_invoice_item_segmentation"
down_revision: str | None = "0005_billing_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


allocation_policy_enum = postgresql.ENUM(
    "USAGE_COMPLETION",
    "FIXED_CUTOFF_SPLIT",
    name="billing_cycle_allocation_policy",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    allocation_policy_enum.create(bind, checkfirst=False)

    op.add_column(
        "professional_billing_contracts",
        sa.Column(
            "cycle_allocation_policy",
            allocation_policy_enum,
            nullable=True,
        ),
    )

    op.execute(
        """
        ALTER TABLE professional_billing_contracts
        ADD CONSTRAINT ck_professional_billing_contracts_allocation_policy
        CHECK (
            (
                invoice_mode = 'PER_USAGE'
                AND cycle_allocation_policy IS NULL
            )
            OR
            (
                invoice_mode = 'ACCUMULATED_OPEN_INVOICE'
                AND cycle_allocation_policy IS NOT NULL
            )
        ) NOT VALID
        """
    )

    op.add_column(
        "invoice_items",
        sa.Column(
            "billing_period_start",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "invoice_items",
        sa.Column(
            "billing_period_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "invoice_items",
        sa.Column(
            "related_invoice_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_invoice_items_billing_period_pair",
        "invoice_items",
        """
        (
            billing_period_start IS NULL
            AND billing_period_end IS NULL
        )
        OR
        (
            billing_period_start IS NOT NULL
            AND billing_period_end IS NOT NULL
            AND billing_period_start < billing_period_end
        )
        """,
    )

    op.create_check_constraint(
        "ck_invoice_items_related_discount_only",
        "invoice_items",
        """
        related_invoice_item_id IS NULL
        OR item_type = 'DISCOUNT'
        """,
    )

    op.create_check_constraint(
        "ck_invoice_items_related_not_self",
        "invoice_items",
        """
        related_invoice_item_id IS NULL
        OR related_invoice_item_id <> id
        """,
    )

    op.create_unique_constraint(
        "uq_invoice_items_tenant_invoice_id_id",
        "invoice_items",
        ["tenant_id", "invoice_id", "id"],
    )

    op.create_foreign_key(
        "fk_invoice_items_related_same_invoice",
        "invoice_items",
        "invoice_items",
        ["tenant_id", "invoice_id", "related_invoice_item_id"],
        ["tenant_id", "invoice_id", "id"],
    )

    op.create_index(
        "uq_invoice_items_specific_discount",
        "invoice_items",
        ["tenant_id", "related_invoice_item_id"],
        unique=True,
        postgresql_where=sa.text("related_invoice_item_id IS NOT NULL"),
    )

    op.create_index(
        "uq_invoice_items_usage_type_nonsegmented",
        "invoice_items",
        ["tenant_id", "usage_id", "item_type"],
        unique=True,
        postgresql_where=sa.text(
            """
            usage_id IS NOT NULL
            AND billing_period_start IS NULL
            AND billing_period_end IS NULL
            """
        ),
    )

    op.create_index(
        "uq_invoice_items_usage_type_segmented",
        "invoice_items",
        [
            "tenant_id",
            "usage_id",
            "item_type",
            "billing_period_start",
            "billing_period_end",
        ],
        unique=True,
        postgresql_where=sa.text(
            """
            usage_id IS NOT NULL
            AND billing_period_start IS NOT NULL
            AND billing_period_end IS NOT NULL
            """
        ),
    )

    op.drop_constraint(
        "uq_invoice_items_usage_type",
        "invoice_items",
        type_="unique",
    )


def downgrade() -> None:
    bind = op.get_bind()

    migration_evidence_exists = bind.execute(
        sa.text(
            """
            SELECT
                EXISTS (
                    SELECT 1
                    FROM invoice_items
                    WHERE billing_period_start IS NOT NULL
                       OR billing_period_end IS NOT NULL
                       OR related_invoice_item_id IS NOT NULL
                )
                OR EXISTS (
                    SELECT 1
                    FROM professional_billing_contracts
                    WHERE cycle_allocation_policy IS NOT NULL
                )
            """
        )
    ).scalar_one()

    if migration_evidence_exists:
        raise RuntimeError(
            "Cannot downgrade 0006_invoice_item_segmentation: "
            "0006 billing evidence exists."
        )

    op.create_unique_constraint(
        "uq_invoice_items_usage_type",
        "invoice_items",
        ["tenant_id", "usage_id", "item_type"],
    )

    op.drop_index(
        "uq_invoice_items_usage_type_segmented",
        table_name="invoice_items",
    )
    op.drop_index(
        "uq_invoice_items_usage_type_nonsegmented",
        table_name="invoice_items",
    )
    op.drop_index(
        "uq_invoice_items_specific_discount",
        table_name="invoice_items",
    )

    op.drop_constraint(
        "fk_invoice_items_related_same_invoice",
        "invoice_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_invoice_items_tenant_invoice_id_id",
        "invoice_items",
        type_="unique",
    )

    op.drop_constraint(
        "ck_invoice_items_related_not_self",
        "invoice_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_invoice_items_related_discount_only",
        "invoice_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_invoice_items_billing_period_pair",
        "invoice_items",
        type_="check",
    )

    op.drop_column("invoice_items", "related_invoice_item_id")
    op.drop_column("invoice_items", "billing_period_end")
    op.drop_column("invoice_items", "billing_period_start")

    op.drop_constraint(
        "ck_professional_billing_contracts_allocation_policy",
        "professional_billing_contracts",
        type_="check",
    )
    op.drop_column(
        "professional_billing_contracts",
        "cycle_allocation_policy",
    )

    allocation_policy_enum.drop(bind, checkfirst=False)
