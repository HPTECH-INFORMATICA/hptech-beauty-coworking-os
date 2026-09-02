"""Establish the initial HPTECH Beauty Coworking OS database schema.

Revision ID: 0001_initial_bcos_schema
Revises:
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial_bcos_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL capabilities required by the BCOS database invariants.
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        """
    )

    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS btree_gist;
        """
    )

    # Domain enums.
    op.execute(
        """
        CREATE TYPE tenant_status AS ENUM (
            'ACTIVE',
            'INACTIVE'
        );

        CREATE TYPE membership_role AS ENUM (
            'OWNER',
            'ADMIN',
            'RECEPTION',
            'PROFESSIONAL'
        );

        CREATE TYPE membership_status AS ENUM (
            'INVITED',
            'ACTIVE',
            'INACTIVE'
        );

        CREATE TYPE professional_status AS ENUM (
            'ACTIVE',
            'INACTIVE'
        );

        CREATE TYPE resource_status AS ENUM (
            'AVAILABLE',
            'OCCUPIED',
            'CLEANING',
            'MAINTENANCE',
            'BLOCKED'
        );

        CREATE TYPE booking_status AS ENUM (
            'PENDING',
            'CONFIRMED',
            'COMPLETED',
            'CANCELLED',
            'NO_SHOW'
        );

        CREATE TYPE occupancy_source_type AS ENUM (
            'BOOKING',
            'USAGE',
            'MANUAL_BLOCK',
            'CLEANING',
            'MAINTENANCE'
        );

        CREATE TYPE occupancy_status AS ENUM (
            'ACTIVE',
            'RELEASED'
        );

        CREATE TYPE usage_status AS ENUM (
            'PENDING',
            'CHECKED_IN',
            'COMPLETED',
            'CANCELLED'
        );

        CREATE TYPE pricing_rule_status AS ENUM (
            'ACTIVE',
            'INACTIVE'
        );

        CREATE TYPE invoice_status AS ENUM (
            'OPEN',
            'PARTIALLY_PAID',
            'PAID',
            'CANCELLED'
        );

        CREATE TYPE invoice_item_type AS ENUM (
            'BASE_LEASE',
            'OVERTIME',
            'ADJUSTMENT',
            'DISCOUNT'
        );

        CREATE TYPE payment_status AS ENUM (
            'PENDING',
            'CONFIRMED',
            'CANCELLED',
            'FAILED'
        );

        CREATE TYPE payment_method AS ENUM (
            'PIX',
            'CASH',
            'CARD',
            'OTHER'
        );

        CREATE TYPE outbox_status AS ENUM (
            'PENDING',
            'PROCESSING',
            'PROCESSED',
            'FAILED'
        );
        """
    )

    # ------------------------------------------------------------------
    # TENANTS
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(160) NOT NULL,
            slug VARCHAR(100) NOT NULL,
            status tenant_status NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_tenants_slug UNIQUE (slug)
        );
        """
    )

    # ------------------------------------------------------------------
    # UNITS
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE units (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            name VARCHAR(160) NOT NULL,
            timezone VARCHAR(100) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,

            CONSTRAINT uq_units_id_tenant UNIQUE (id, tenant_id),

            CONSTRAINT fk_units_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants (id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_units_timezone_not_blank
                CHECK (btrim(timezone) <> '')
        );
        """
    )

    op.execute(
        """
        CREATE TABLE unit_reception_hours (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id UUID NOT NULL,
        unit_id UUID NOT NULL,
        day_of_week SMALLINT NOT NULL,
        opens_at TIME,
        closes_at TIME,
        is_closed BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

        CONSTRAINT uq_unit_reception_hours_id_tenant
            UNIQUE (id, tenant_id),

        CONSTRAINT uq_unit_reception_hours_unit_day
            UNIQUE (tenant_id, unit_id, day_of_week),

        CONSTRAINT fk_unit_reception_hours_unit
            FOREIGN KEY (unit_id, tenant_id)
            REFERENCES units (id, tenant_id)
            ON DELETE CASCADE,

        CONSTRAINT ck_unit_reception_hours_day
            CHECK (day_of_week BETWEEN 0 AND 6),

        CONSTRAINT ck_unit_reception_hours_window
            CHECK (
                (is_closed = TRUE AND opens_at IS NULL AND closes_at IS NULL)
                OR
                (
                    is_closed = FALSE
                    AND opens_at IS NOT NULL
                    AND closes_at IS NOT NULL
                    AND opens_at < closes_at
                )
            )
    );
    """
    )

    # ------------------------------------------------------------------
    # TENANT MEMBERSHIP / RBAC IDENTITY BINDING
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE tenant_memberships (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            external_user_id VARCHAR(255) NOT NULL,
            role membership_role NOT NULL,
            status membership_status NOT NULL DEFAULT 'INVITED',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,

            CONSTRAINT uq_tenant_memberships_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT uq_tenant_memberships_user
                UNIQUE (tenant_id, external_user_id),

            CONSTRAINT fk_tenant_memberships_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants (id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_tenant_memberships_external_user
                CHECK (btrim(external_user_id) <> '')
        );
        """
    )

    # ------------------------------------------------------------------
    # PROFESSIONALS
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE professionals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            external_user_id VARCHAR(255),
            name VARCHAR(160) NOT NULL,
            email VARCHAR(255),
            phone VARCHAR(40),
            status professional_status NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,

            CONSTRAINT uq_professionals_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT uq_professionals_external_user
                UNIQUE (tenant_id, external_user_id),

            CONSTRAINT fk_professionals_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants (id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_professionals_name
                CHECK (btrim(name) <> '')
        );
        """
    )

    # ------------------------------------------------------------------
    # RESOURCE CATALOG
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE resource_categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            name VARCHAR(120) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,

            CONSTRAINT uq_resource_categories_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT uq_resource_categories_name
                UNIQUE (tenant_id, name),

            CONSTRAINT fk_resource_categories_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants (id)
                ON DELETE RESTRICT
        );
        """
    )

    op.execute(
        """
        CREATE TABLE resources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            unit_id UUID NOT NULL,
            category_id UUID NOT NULL,
            name VARCHAR(160) NOT NULL,
            operational_status resource_status NOT NULL DEFAULT 'AVAILABLE',
            buffer_before_minutes INTEGER NOT NULL DEFAULT 0,
            buffer_after_minutes INTEGER NOT NULL DEFAULT 0,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,

            CONSTRAINT uq_resources_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT uq_resources_unit_name
                UNIQUE (tenant_id, unit_id, name),

            CONSTRAINT fk_resources_unit
                FOREIGN KEY (unit_id, tenant_id)
                REFERENCES units (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT fk_resources_category
                FOREIGN KEY (category_id, tenant_id)
                REFERENCES resource_categories (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_resources_buffer_before
                CHECK (buffer_before_minutes >= 0),

            CONSTRAINT ck_resources_buffer_after
                CHECK (buffer_after_minutes >= 0)
        );
        """
    )

    # ------------------------------------------------------------------
    # BOOKING SERIES
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE booking_series (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            professional_id UUID NOT NULL,
            rrule TEXT NOT NULL,
            timezone VARCHAR(100) NOT NULL,
            starts_at TIMESTAMPTZ NOT NULL,
            ends_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            cancelled_at TIMESTAMPTZ,

            CONSTRAINT uq_booking_series_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT fk_booking_series_professional
                FOREIGN KEY (professional_id, tenant_id)
                REFERENCES professionals (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_booking_series_rrule
                CHECK (btrim(rrule) <> ''),

            CONSTRAINT ck_booking_series_timezone
                CHECK (btrim(timezone) <> ''),

            CONSTRAINT ck_booking_series_dates
                CHECK (ends_at IS NULL OR ends_at > starts_at)
        );
        """
    )

    # ------------------------------------------------------------------
    # BOOKINGS
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE bookings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            unit_id UUID NOT NULL,
            resource_id UUID NOT NULL,
            professional_id UUID NOT NULL,
            series_id UUID,
            status booking_status NOT NULL DEFAULT 'PENDING',
            starts_at TIMESTAMPTZ NOT NULL,
            ends_at TIMESTAMPTZ NOT NULL,
            buffer_before_minutes INTEGER NOT NULL DEFAULT 0,
            buffer_after_minutes INTEGER NOT NULL DEFAULT 0,
            pricing_snapshot JSONB NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            confirmed_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,

            CONSTRAINT uq_bookings_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT fk_bookings_unit
                FOREIGN KEY (unit_id, tenant_id)
                REFERENCES units (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT fk_bookings_resource
                FOREIGN KEY (resource_id, tenant_id)
                REFERENCES resources (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT fk_bookings_professional
                FOREIGN KEY (professional_id, tenant_id)
                REFERENCES professionals (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT fk_bookings_series
                FOREIGN KEY (series_id, tenant_id)
                REFERENCES booking_series (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_bookings_period
                CHECK (ends_at > starts_at),

            CONSTRAINT ck_bookings_buffer_before
                CHECK (buffer_before_minutes >= 0),

            CONSTRAINT ck_bookings_buffer_after
                CHECK (buffer_after_minutes >= 0),

            CONSTRAINT ck_bookings_pricing_snapshot
                CHECK (jsonb_typeof(pricing_snapshot) = 'object')
        );
        """
    )

    # ------------------------------------------------------------------
    # RESOURCE OCCUPANCY
    #
    # Canonical source of physical unavailability.
    # The exclusion constraint is the final concurrency authority.
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE resource_occupancies (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            resource_id UUID NOT NULL,
            period TSTZRANGE NOT NULL,
            source_type occupancy_source_type NOT NULL,
            source_id UUID NOT NULL,
            status occupancy_status NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            released_at TIMESTAMPTZ,

            CONSTRAINT uq_resource_occupancies_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT uq_resource_occupancies_source
                UNIQUE (tenant_id, source_type, source_id),

            CONSTRAINT fk_resource_occupancies_resource
                FOREIGN KEY (resource_id, tenant_id)
                REFERENCES resources (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_resource_occupancies_period
                CHECK (
                    NOT isempty(period)
                    AND lower(period) IS NOT NULL
                    AND upper(period) IS NOT NULL
                    AND lower(period) < upper(period)
                    AND lower_inc(period)
                    AND NOT upper_inc(period)
                ),

            CONSTRAINT ck_resource_occupancies_release
                CHECK (
                    (status = 'ACTIVE' AND released_at IS NULL)
                    OR
                    (status = 'RELEASED' AND released_at IS NOT NULL)
                )
        );
        """
    )

    op.execute(
        """
        ALTER TABLE resource_occupancies
        ADD CONSTRAINT ex_resource_occupancies_no_overlap
        EXCLUDE USING gist (
            tenant_id WITH =,
            resource_id WITH =,
            period WITH &&
        )
        WHERE (status = 'ACTIVE');
        """
    )

    # ------------------------------------------------------------------
    # USAGE
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE usages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            booking_id UUID NOT NULL,
            resource_id UUID NOT NULL,
            professional_id UUID NOT NULL,
            status usage_status NOT NULL DEFAULT 'PENDING',
            checked_in_at TIMESTAMPTZ,
            checked_out_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_usages_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT uq_usages_booking
                UNIQUE (tenant_id, booking_id),

            CONSTRAINT fk_usages_booking
                FOREIGN KEY (booking_id, tenant_id)
                REFERENCES bookings (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT fk_usages_resource
                FOREIGN KEY (resource_id, tenant_id)
                REFERENCES resources (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT fk_usages_professional
                FOREIGN KEY (professional_id, tenant_id)
                REFERENCES professionals (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_usages_checkout
                CHECK (
                    checked_out_at IS NULL
                    OR (
                        checked_in_at IS NOT NULL
                        AND checked_out_at >= checked_in_at
                    )
                ),

            CONSTRAINT ck_usages_completed
                CHECK (
                    status <> 'COMPLETED'
                    OR (
                        checked_in_at IS NOT NULL
                        AND checked_out_at IS NOT NULL
                    )
                )
        );
        """
    )

    # ------------------------------------------------------------------
    # PRICING
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE pricing_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            unit_id UUID,
            resource_category_id UUID,
            name VARCHAR(160) NOT NULL,
            status pricing_rule_status NOT NULL DEFAULT 'ACTIVE',
            priority INTEGER NOT NULL DEFAULT 100,
            currency CHAR(3) NOT NULL DEFAULT 'BRL',
            rule_definition JSONB NOT NULL,
            valid_from TIMESTAMPTZ,
            valid_until TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,

            CONSTRAINT uq_pricing_rules_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT fk_pricing_rules_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants (id)
                ON DELETE RESTRICT,

            CONSTRAINT fk_pricing_rules_unit
                FOREIGN KEY (unit_id, tenant_id)
                REFERENCES units (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT fk_pricing_rules_category
                FOREIGN KEY (resource_category_id, tenant_id)
                REFERENCES resource_categories (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_pricing_rules_priority
                CHECK (priority >= 0),

            CONSTRAINT ck_pricing_rules_currency
                CHECK (currency = 'BRL'),

            CONSTRAINT ck_pricing_rules_definition
                CHECK (jsonb_typeof(rule_definition) = 'object'),

            CONSTRAINT ck_pricing_rules_validity
                CHECK (
                    valid_until IS NULL
                    OR valid_from IS NULL
                    OR valid_until > valid_from
                )
        );
        """
    )

    # ------------------------------------------------------------------
    # BILLING
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE invoices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            professional_id UUID NOT NULL,
            status invoice_status NOT NULL DEFAULT 'OPEN',
            currency CHAR(3) NOT NULL DEFAULT 'BRL',
            subtotal_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
            discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
            total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
            issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            due_at TIMESTAMPTZ,
            paid_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_invoices_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT fk_invoices_professional
                FOREIGN KEY (professional_id, tenant_id)
                REFERENCES professionals (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_invoices_currency
                CHECK (currency = 'BRL'),

            CONSTRAINT ck_invoices_subtotal
                CHECK (subtotal_amount >= 0),

            CONSTRAINT ck_invoices_discount
                CHECK (discount_amount >= 0),

            CONSTRAINT ck_invoices_total
                CHECK (total_amount >= 0)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE invoice_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            invoice_id UUID NOT NULL,
            usage_id UUID,
            item_type invoice_item_type NOT NULL,
            description VARCHAR(255) NOT NULL,
            quantity NUMERIC(12, 4) NOT NULL DEFAULT 1,
            unit_amount NUMERIC(12, 2) NOT NULL,
            total_amount NUMERIC(12, 2) NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_invoice_items_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT uq_invoice_items_usage_type
                UNIQUE (tenant_id, usage_id, item_type),

            CONSTRAINT fk_invoice_items_invoice
                FOREIGN KEY (invoice_id, tenant_id)
                REFERENCES invoices (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT fk_invoice_items_usage
                FOREIGN KEY (usage_id, tenant_id)
                REFERENCES usages (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_invoice_items_quantity
                CHECK (quantity > 0),

            CONSTRAINT ck_invoice_items_total
                CHECK (
                    item_type = 'DISCOUNT'
                    OR total_amount >= 0
                ),

            CONSTRAINT ck_invoice_items_metadata
                CHECK (jsonb_typeof(metadata) = 'object')
        );
        """
    )

    # ------------------------------------------------------------------
    # PAYMENTS
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE payments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            invoice_id UUID NOT NULL,
            idempotency_key VARCHAR(255) NOT NULL,
            method payment_method NOT NULL DEFAULT 'PIX',
            status payment_status NOT NULL DEFAULT 'PENDING',
            currency CHAR(3) NOT NULL DEFAULT 'BRL',
            amount NUMERIC(12, 2) NOT NULL,
            reference VARCHAR(255),
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            paid_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_payments_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT uq_payments_idempotency
                UNIQUE (tenant_id, idempotency_key),

            CONSTRAINT fk_payments_invoice
                FOREIGN KEY (invoice_id, tenant_id)
                REFERENCES invoices (id, tenant_id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_payments_idempotency_key
                CHECK (btrim(idempotency_key) <> ''),

            CONSTRAINT ck_payments_currency
                CHECK (currency = 'BRL'),

            CONSTRAINT ck_payments_amount
                CHECK (amount > 0),

            CONSTRAINT ck_payments_metadata
                CHECK (jsonb_typeof(metadata) = 'object'),

            CONSTRAINT ck_payments_paid_at
                CHECK (
                    status <> 'CONFIRMED'
                    OR paid_at IS NOT NULL
                )
        );
        """
    )

    # ------------------------------------------------------------------
    # TRANSACTIONAL OUTBOX
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE outbox_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            dedupe_key VARCHAR(255) NOT NULL,
            event_type VARCHAR(160) NOT NULL,
            aggregate_type VARCHAR(160) NOT NULL,
            aggregate_id UUID NOT NULL,
            payload JSONB NOT NULL,
            status outbox_status NOT NULL DEFAULT 'PENDING',
            attempts INTEGER NOT NULL DEFAULT 0,
            available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            processed_at TIMESTAMPTZ,
            last_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_outbox_events_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT uq_outbox_events_dedupe
                UNIQUE (tenant_id, dedupe_key),

            CONSTRAINT fk_outbox_events_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants (id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_outbox_events_dedupe_key
                CHECK (btrim(dedupe_key) <> ''),

            CONSTRAINT ck_outbox_events_event_type
                CHECK (btrim(event_type) <> ''),

            CONSTRAINT ck_outbox_events_aggregate_type
                CHECK (btrim(aggregate_type) <> ''),

            CONSTRAINT ck_outbox_events_payload
                CHECK (jsonb_typeof(payload) = 'object'),

            CONSTRAINT ck_outbox_events_attempts
                CHECK (attempts >= 0)
        );
        """
    )

    # ------------------------------------------------------------------
    # AUDIT
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE TABLE audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            actor_external_user_id VARCHAR(255),
            action VARCHAR(160) NOT NULL,
            entity_type VARCHAR(160) NOT NULL,
            entity_id UUID,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_audit_logs_id_tenant
                UNIQUE (id, tenant_id),

            CONSTRAINT fk_audit_logs_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants (id)
                ON DELETE RESTRICT,

            CONSTRAINT ck_audit_logs_action
                CHECK (btrim(action) <> ''),

            CONSTRAINT ck_audit_logs_entity_type
                CHECK (btrim(entity_type) <> ''),

            CONSTRAINT ck_audit_logs_metadata
                CHECK (jsonb_typeof(metadata) = 'object')
        );
        """
    )

    # ------------------------------------------------------------------
    # INDEXES
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE INDEX ix_units_tenant
            ON units (tenant_id);

        CREATE INDEX ix_tenant_memberships_tenant_role_status
            ON tenant_memberships (tenant_id, role, status);

        CREATE INDEX ix_professionals_tenant_status
            ON professionals (tenant_id, status);

        CREATE INDEX ix_resources_tenant_unit
            ON resources (tenant_id, unit_id);

        CREATE INDEX ix_resources_tenant_status
            ON resources (tenant_id, operational_status);

        CREATE INDEX ix_booking_series_tenant_professional
            ON booking_series (tenant_id, professional_id);

        CREATE INDEX ix_bookings_tenant_resource_period
            ON bookings (tenant_id, resource_id, starts_at, ends_at);

        CREATE INDEX ix_bookings_tenant_professional_period
            ON bookings (tenant_id, professional_id, starts_at, ends_at);

        CREATE INDEX ix_bookings_tenant_status
            ON bookings (tenant_id, status);

        CREATE INDEX ix_resource_occupancies_tenant_resource
            ON resource_occupancies (tenant_id, resource_id);

        CREATE INDEX ix_resource_occupancies_period_gist
            ON resource_occupancies
            USING gist (period);

        CREATE INDEX ix_usages_tenant_status
            ON usages (tenant_id, status);

        CREATE INDEX ix_pricing_rules_resolution
            ON pricing_rules (
                tenant_id,
                status,
                priority,
                valid_from,
                valid_until
            );

        CREATE INDEX ix_invoices_tenant_professional_status
            ON invoices (tenant_id, professional_id, status);

        CREATE INDEX ix_invoice_items_invoice
            ON invoice_items (tenant_id, invoice_id);

        CREATE INDEX ix_payments_invoice_status
            ON payments (tenant_id, invoice_id, status);

        CREATE INDEX ix_outbox_events_delivery
            ON outbox_events (status, available_at, created_at);

        CREATE INDEX ix_audit_logs_tenant_occurred
            ON audit_logs (tenant_id, occurred_at DESC);
        """
    )

    # ------------------------------------------------------------------
    # IMMUTABLE BOOKING PRICING SNAPSHOT
    # ------------------------------------------------------------------

    op.execute(
        """
        CREATE FUNCTION prevent_booking_pricing_snapshot_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.pricing_snapshot IS DISTINCT FROM OLD.pricing_snapshot THEN
                RAISE EXCEPTION
                    'booking pricing_snapshot is immutable';
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_bookings_pricing_snapshot_immutable
        BEFORE UPDATE OF pricing_snapshot
        ON bookings
        FOR EACH ROW
        EXECUTE FUNCTION prevent_booking_pricing_snapshot_update();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS
            trg_bookings_pricing_snapshot_immutable
            ON bookings;

        DROP FUNCTION IF EXISTS
            prevent_booking_pricing_snapshot_update();

        DROP TABLE IF EXISTS audit_logs;
        DROP TABLE IF EXISTS outbox_events;
        DROP TABLE IF EXISTS payments;
        DROP TABLE IF EXISTS invoice_items;
        DROP TABLE IF EXISTS invoices;
        DROP TABLE IF EXISTS pricing_rules;
        DROP TABLE IF EXISTS usages;
        DROP TABLE IF EXISTS resource_occupancies;
        DROP TABLE IF EXISTS bookings;
        DROP TABLE IF EXISTS booking_series;
        DROP TABLE IF EXISTS resources;
        DROP TABLE IF EXISTS resource_categories;
        DROP TABLE IF EXISTS professionals;
        DROP TABLE IF EXISTS tenant_memberships;
        DROP TABLE IF EXISTS unit_reception_hours;
        DROP TABLE IF EXISTS units;
        DROP TABLE IF EXISTS tenants;

        DROP TYPE IF EXISTS outbox_status;
        DROP TYPE IF EXISTS payment_method;
        DROP TYPE IF EXISTS payment_status;
        DROP TYPE IF EXISTS invoice_item_type;
        DROP TYPE IF EXISTS invoice_status;
        DROP TYPE IF EXISTS pricing_rule_status;
        DROP TYPE IF EXISTS usage_status;
        DROP TYPE IF EXISTS occupancy_status;
        DROP TYPE IF EXISTS occupancy_source_type;
        DROP TYPE IF EXISTS booking_status;
        DROP TYPE IF EXISTS resource_status;
        DROP TYPE IF EXISTS professional_status;
        DROP TYPE IF EXISTS membership_status;
        DROP TYPE IF EXISTS membership_role;
        DROP TYPE IF EXISTS tenant_status;
        """
    )
