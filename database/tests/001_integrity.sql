-- HPTECH Beauty Coworking OS
-- Database Integrity Test Suite
--
-- This suite is intentionally transactional.
-- It must leave no persistent test data.
--
-- Execution against real PostgreSQL belongs to BCOS-M0.2-G.

BEGIN;

DO $bcos_integrity$
DECLARE
    tenant_a UUID;
    tenant_b UUID;

    unit_a UUID;
    unit_b UUID;

    professional_a UUID;
    professional_b UUID;

    category_a UUID;
    category_b UUID;

    resource_a1 UUID;
    resource_a2 UUID;
    resource_b1 UUID;

    booking_a1 UUID;
    booking_a2 UUID;

    usage_a1 UUID;

    invoice_a1 UUID;

    overlap_rejected BOOLEAN := FALSE;
    cross_tenant_rejected BOOLEAN := FALSE;
    payment_duplicate_rejected BOOLEAN := FALSE;
    billing_duplicate_rejected BOOLEAN := FALSE;
    snapshot_update_rejected BOOLEAN := FALSE;
BEGIN
    --------------------------------------------------------------------
    -- FIXTURES
    --------------------------------------------------------------------

    INSERT INTO tenants (
        name,
        slug
    )
    VALUES (
        'BCOS Integrity Tenant A',
        'bcos-integrity-a'
    )
    RETURNING id INTO tenant_a;

    INSERT INTO tenants (
        name,
        slug
    )
    VALUES (
        'BCOS Integrity Tenant B',
        'bcos-integrity-b'
    )
    RETURNING id INTO tenant_b;

    INSERT INTO units (
        tenant_id,
        name,
        timezone
    )
    VALUES (
        tenant_a,
        'Unit A',
        'America/Sao_Paulo'
    )
    RETURNING id INTO unit_a;

    INSERT INTO units (
        tenant_id,
        name,
        timezone
    )
    VALUES (
        tenant_b,
        'Unit B',
        'America/Sao_Paulo'
    )
    RETURNING id INTO unit_b;

    INSERT INTO professionals (
        tenant_id,
        name
    )
    VALUES (
        tenant_a,
        'Professional A'
    )
    RETURNING id INTO professional_a;

    INSERT INTO professionals (
        tenant_id,
        name
    )
    VALUES (
        tenant_b,
        'Professional B'
    )
    RETURNING id INTO professional_b;

    INSERT INTO resource_categories (
        tenant_id,
        name
    )
    VALUES (
        tenant_a,
        'Room'
    )
    RETURNING id INTO category_a;

    INSERT INTO resource_categories (
        tenant_id,
        name
    )
    VALUES (
        tenant_b,
        'Room'
    )
    RETURNING id INTO category_b;

    INSERT INTO resources (
        tenant_id,
        unit_id,
        category_id,
        name
    )
    VALUES (
        tenant_a,
        unit_a,
        category_a,
        'Resource A1'
    )
    RETURNING id INTO resource_a1;

    INSERT INTO resources (
        tenant_id,
        unit_id,
        category_id,
        name
    )
    VALUES (
        tenant_a,
        unit_a,
        category_a,
        'Resource A2'
    )
    RETURNING id INTO resource_a2;

    INSERT INTO resources (
        tenant_id,
        unit_id,
        category_id,
        name
    )
    VALUES (
        tenant_b,
        unit_b,
        category_b,
        'Resource B1'
    )
    RETURNING id INTO resource_b1;

    INSERT INTO bookings (
        tenant_id,
        unit_id,
        resource_id,
        professional_id,
        status,
        starts_at,
        ends_at,
        pricing_snapshot
    )
    VALUES (
        tenant_a,
        unit_a,
        resource_a1,
        professional_a,
        'CONFIRMED',
        '2030-01-01 10:00:00+00',
        '2030-01-01 11:00:00+00',
        '{"currency":"BRL","base_amount":"100.00"}'::jsonb
    )
    RETURNING id INTO booking_a1;

    INSERT INTO bookings (
        tenant_id,
        unit_id,
        resource_id,
        professional_id,
        status,
        starts_at,
        ends_at,
        pricing_snapshot
    )
    VALUES (
        tenant_a,
        unit_a,
        resource_a1,
        professional_a,
        'CONFIRMED',
        '2030-01-01 11:00:00+00',
        '2030-01-01 12:00:00+00',
        '{"currency":"BRL","base_amount":"100.00"}'::jsonb
    )
    RETURNING id INTO booking_a2;

    --------------------------------------------------------------------
    -- TEST 1
    -- Same resource + overlapping ACTIVE periods must be rejected.
    --------------------------------------------------------------------

    INSERT INTO resource_occupancies (
        tenant_id,
        resource_id,
        period,
        source_type,
        source_id
    )
    VALUES (
        tenant_a,
        resource_a1,
        tstzrange(
            '2030-01-01 10:00:00+00',
            '2030-01-01 11:00:00+00',
            '[)'
        ),
        'BOOKING',
        booking_a1
    );

    BEGIN
        INSERT INTO resource_occupancies (
            tenant_id,
            resource_id,
            period,
            source_type,
            source_id
        )
        VALUES (
            tenant_a,
            resource_a1,
            tstzrange(
                '2030-01-01 10:30:00+00',
                '2030-01-01 11:30:00+00',
                '[)'
            ),
            'MANUAL_BLOCK',
            gen_random_uuid()
        );

    EXCEPTION
        WHEN exclusion_violation THEN
            overlap_rejected := TRUE;
    END;

    IF NOT overlap_rejected THEN
        RAISE EXCEPTION
            'INTEGRITY FAILURE: overlapping occupancy was accepted';
    END IF;

    --------------------------------------------------------------------
    -- TEST 2
    -- Adjacent [) periods on the same resource must be accepted.
    --------------------------------------------------------------------

    INSERT INTO resource_occupancies (
        tenant_id,
        resource_id,
        period,
        source_type,
        source_id
    )
    VALUES (
        tenant_a,
        resource_a1,
        tstzrange(
            '2030-01-01 11:00:00+00',
            '2030-01-01 12:00:00+00',
            '[)'
        ),
        'BOOKING',
        booking_a2
    );

    --------------------------------------------------------------------
    -- TEST 3
    -- Different resources may occupy the same period.
    --------------------------------------------------------------------

    INSERT INTO resource_occupancies (
        tenant_id,
        resource_id,
        period,
        source_type,
        source_id
    )
    VALUES (
        tenant_a,
        resource_a2,
        tstzrange(
            '2030-01-01 10:00:00+00',
            '2030-01-01 11:00:00+00',
            '[)'
        ),
        'MANUAL_BLOCK',
        gen_random_uuid()
    );

    --------------------------------------------------------------------
    -- TEST 4
    -- A different tenant remains independently isolated.
    --------------------------------------------------------------------

    INSERT INTO resource_occupancies (
        tenant_id,
        resource_id,
        period,
        source_type,
        source_id
    )
    VALUES (
        tenant_b,
        resource_b1,
        tstzrange(
            '2030-01-01 10:00:00+00',
            '2030-01-01 11:00:00+00',
            '[)'
        ),
        'MANUAL_BLOCK',
        gen_random_uuid()
    );

    --------------------------------------------------------------------
    -- TEST 5
    -- Composite FK must reject cross-tenant resource references.
    --------------------------------------------------------------------

    BEGIN
        INSERT INTO bookings (
            tenant_id,
            unit_id,
            resource_id,
            professional_id,
            status,
            starts_at,
            ends_at,
            pricing_snapshot
        )
        VALUES (
            tenant_a,
            unit_a,
            resource_b1,
            professional_a,
            'CONFIRMED',
            '2030-01-02 10:00:00+00',
            '2030-01-02 11:00:00+00',
            '{"currency":"BRL","base_amount":"100.00"}'::jsonb
        );

    EXCEPTION
        WHEN foreign_key_violation THEN
            cross_tenant_rejected := TRUE;
    END;

    IF NOT cross_tenant_rejected THEN
        RAISE EXCEPTION
            'INTEGRITY FAILURE: cross-tenant booking resource was accepted';
    END IF;

    --------------------------------------------------------------------
    -- TEST 6
    -- Booking pricing snapshot must be immutable.
    --------------------------------------------------------------------

    BEGIN
        UPDATE bookings
        SET pricing_snapshot =
            '{"currency":"BRL","base_amount":"999.00"}'::jsonb
        WHERE id = booking_a1
          AND tenant_id = tenant_a;

    EXCEPTION
        WHEN raise_exception THEN
            snapshot_update_rejected := TRUE;
    END;

    IF NOT snapshot_update_rejected THEN
        RAISE EXCEPTION
            'INTEGRITY FAILURE: pricing snapshot mutation was accepted';
    END IF;

    --------------------------------------------------------------------
    -- BILLING FIXTURES
    --------------------------------------------------------------------

    INSERT INTO usages (
        tenant_id,
        booking_id,
        resource_id,
        professional_id,
        status,
        checked_in_at,
        checked_out_at
    )
    VALUES (
        tenant_a,
        booking_a1,
        resource_a1,
        professional_a,
        'COMPLETED',
        '2030-01-01 10:00:00+00',
        '2030-01-01 11:00:00+00'
    )
    RETURNING id INTO usage_a1;

    INSERT INTO invoices (
        tenant_id,
        professional_id,
        status,
        subtotal_amount,
        total_amount
    )
    VALUES (
        tenant_a,
        professional_a,
        'OPEN',
        100.00,
        100.00
    )
    RETURNING id INTO invoice_a1;

    INSERT INTO invoice_items (
        tenant_id,
        invoice_id,
        usage_id,
        item_type,
        description,
        quantity,
        unit_amount,
        total_amount
    )
    VALUES (
        tenant_a,
        invoice_a1,
        usage_a1,
        'BASE_LEASE',
        'Base lease',
        1,
        100.00,
        100.00
    );

    --------------------------------------------------------------------
    -- TEST 7
    -- Billing must be idempotent by Usage + item type.
    --------------------------------------------------------------------

    BEGIN
        INSERT INTO invoice_items (
            tenant_id,
            invoice_id,
            usage_id,
            item_type,
            description,
            quantity,
            unit_amount,
            total_amount
        )
        VALUES (
            tenant_a,
            invoice_a1,
            usage_a1,
            'BASE_LEASE',
            'Duplicate base lease',
            1,
            100.00,
            100.00
        );

    EXCEPTION
        WHEN unique_violation THEN
            billing_duplicate_rejected := TRUE;
    END;

    IF NOT billing_duplicate_rejected THEN
        RAISE EXCEPTION
            'INTEGRITY FAILURE: duplicate billing source was accepted';
    END IF;

    --------------------------------------------------------------------
    -- TEST 8
    -- Payment idempotency key must reject duplicate processing.
    --------------------------------------------------------------------

    INSERT INTO payments (
        tenant_id,
        invoice_id,
        idempotency_key,
        method,
        status,
        amount
    )
    VALUES (
        tenant_a,
        invoice_a1,
        'integrity-payment-001',
        'PIX',
        'PENDING',
        100.00
    );

    BEGIN
        INSERT INTO payments (
            tenant_id,
            invoice_id,
            idempotency_key,
            method,
            status,
            amount
        )
        VALUES (
            tenant_a,
            invoice_a1,
            'integrity-payment-001',
            'PIX',
            'PENDING',
            100.00
        );

    EXCEPTION
        WHEN unique_violation THEN
            payment_duplicate_rejected := TRUE;
    END;

    IF NOT payment_duplicate_rejected THEN
        RAISE EXCEPTION
            'INTEGRITY FAILURE: duplicate payment idempotency key was accepted';
    END IF;

    --------------------------------------------------------------------
    -- FINAL ASSERTIONS
    --------------------------------------------------------------------

    IF NOT (
        overlap_rejected
        AND cross_tenant_rejected
        AND payment_duplicate_rejected
        AND billing_duplicate_rejected
        AND snapshot_update_rejected
    ) THEN
        RAISE EXCEPTION
            'INTEGRITY FAILURE: one or more expected protections did not execute';
    END IF;

    RAISE NOTICE
        'BCOS DATABASE INTEGRITY TEST SUITE: PASS';
END
$bcos_integrity$;

ROLLBACK;