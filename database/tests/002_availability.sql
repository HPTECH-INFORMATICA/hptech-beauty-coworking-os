-- HPTECH Beauty Coworking OS
-- M3 Availability PostgreSQL Integration Test
--
-- This suite is intentionally transactional.
-- It must leave no persistent test data.

BEGIN;

DO $bcos_availability$
DECLARE
    tenant_a UUID;
    tenant_b UUID;
    unit_a UUID;
    unit_b UUID;
    category_a UUID;
    category_b UUID;
    resource_free UUID;
    resource_active UUID;
    resource_released UUID;
    resource_adjacent UUID;
    resource_tenant_b UUID;
    result_available BOOLEAN;
    result_reason TEXT;
BEGIN
    --------------------------------------------------------------------
    -- FIXTURES
    --------------------------------------------------------------------

    INSERT INTO tenants (name, slug)
    VALUES (
        'BCOS M3 Availability Tenant A',
        'bcos-m3-availability-a'
    )
    RETURNING id INTO tenant_a;

    INSERT INTO tenants (name, slug)
    VALUES (
        'BCOS M3 Availability Tenant B',
        'bcos-m3-availability-b'
    )
    RETURNING id INTO tenant_b;

    INSERT INTO units (tenant_id, name, timezone)
    VALUES (
        tenant_a,
        'M3 Unit A',
        'America/Sao_Paulo'
    )
    RETURNING id INTO unit_a;

    INSERT INTO units (tenant_id, name, timezone)
    VALUES (
        tenant_b,
        'M3 Unit B',
        'America/Sao_Paulo'
    )
    RETURNING id INTO unit_b;

    INSERT INTO resource_categories (tenant_id, name)
    VALUES (tenant_a, 'M3 Room A')
    RETURNING id INTO category_a;

    INSERT INTO resource_categories (tenant_id, name)
    VALUES (tenant_b, 'M3 Room B')
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
        'M3 Free'
    )
    RETURNING id INTO resource_free;

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
        'M3 Active'
    )
    RETURNING id INTO resource_active;

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
        'M3 Released'
    )
    RETURNING id INTO resource_released;

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
        'M3 Adjacent'
    )
    RETURNING id INTO resource_adjacent;

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
        'M3 Tenant B'
    )
    RETURNING id INTO resource_tenant_b;

    INSERT INTO resource_occupancies (
        tenant_id,
        resource_id,
        period,
        source_type,
        source_id
    )
    VALUES (
        tenant_a,
        resource_active,
        tstzrange(
            '2031-01-10 10:00:00+00',
            '2031-01-10 11:00:00+00',
            '[)'
        ),
        'MANUAL_BLOCK',
        gen_random_uuid()
    );

    INSERT INTO resource_occupancies (
        tenant_id,
        resource_id,
        period,
        source_type,
        source_id,
        status,
        released_at
    )
    VALUES (
        tenant_a,
        resource_released,
        tstzrange(
            '2031-01-10 10:00:00+00',
            '2031-01-10 11:00:00+00',
            '[)'
        ),
        'CLEANING',
        gen_random_uuid(),
        'RELEASED',
        now()
    );

    INSERT INTO resource_occupancies (
        tenant_id,
        resource_id,
        period,
        source_type,
        source_id
    )
    VALUES (
        tenant_a,
        resource_adjacent,
        tstzrange(
            '2031-01-10 09:00:00+00',
            '2031-01-10 10:00:00+00',
            '[)'
        ),
        'MAINTENANCE',
        gen_random_uuid()
    );

    INSERT INTO resource_occupancies (
        tenant_id,
        resource_id,
        period,
        source_type,
        source_id
    )
    VALUES (
        tenant_b,
        resource_tenant_b,
        tstzrange(
            '2031-01-10 10:00:00+00',
            '2031-01-10 11:00:00+00',
            '[)'
        ),
        'MANUAL_BLOCK',
        gen_random_uuid()
    );

    --------------------------------------------------------------------
    -- TEST 1
    -- Resource without occupancy must be available.
    --------------------------------------------------------------------

    SELECT
        NOT EXISTS (
            SELECT 1
            FROM resource_occupancies ro
            WHERE ro.tenant_id = tenant_a
              AND ro.resource_id = resource_free
              AND ro.status = 'ACTIVE'
              AND ro.period && tstzrange(
                  '2031-01-10 10:00:00+00',
                  '2031-01-10 11:00:00+00',
                  '[)'
              )
        )
    INTO result_available;

    IF NOT result_available THEN
        RAISE EXCEPTION
            'M3 AVAILABILITY FAILURE: free resource reported unavailable';
    END IF;

    --------------------------------------------------------------------
    -- TEST 2
    -- Overlapping ACTIVE occupancy must block and expose source reason.
    --------------------------------------------------------------------

    SELECT
        NOT EXISTS (
            SELECT 1
            FROM resource_occupancies ro
            WHERE ro.tenant_id = tenant_a
              AND ro.resource_id = resource_active
              AND ro.status = 'ACTIVE'
              AND ro.period && tstzrange(
                  '2031-01-10 10:15:00+00',
                  '2031-01-10 10:45:00+00',
                  '[)'
              )
        ),
        (
            SELECT ro.source_type::text
            FROM resource_occupancies ro
            WHERE ro.tenant_id = tenant_a
              AND ro.resource_id = resource_active
              AND ro.status = 'ACTIVE'
              AND ro.period && tstzrange(
                  '2031-01-10 10:15:00+00',
                  '2031-01-10 10:45:00+00',
                  '[)'
              )
            ORDER BY lower(ro.period), ro.id
            LIMIT 1
        )
    INTO result_available, result_reason;

    IF result_available OR result_reason <> 'MANUAL_BLOCK' THEN
        RAISE EXCEPTION
            'M3 AVAILABILITY FAILURE: ACTIVE occupancy semantics invalid';
    END IF;

    --------------------------------------------------------------------
    -- TEST 3
    -- RELEASED occupancy must not block availability.
    --------------------------------------------------------------------

    SELECT
        NOT EXISTS (
            SELECT 1
            FROM resource_occupancies ro
            WHERE ro.tenant_id = tenant_a
              AND ro.resource_id = resource_released
              AND ro.status = 'ACTIVE'
              AND ro.period && tstzrange(
                  '2031-01-10 10:00:00+00',
                  '2031-01-10 11:00:00+00',
                  '[)'
              )
        )
    INTO result_available;

    IF NOT result_available THEN
        RAISE EXCEPTION
            'M3 AVAILABILITY FAILURE: RELEASED occupancy blocked resource';
    END IF;

    --------------------------------------------------------------------
    -- TEST 4
    -- Adjacent [) occupancy ending at starts_at must not overlap.
    --------------------------------------------------------------------

    SELECT
        NOT EXISTS (
            SELECT 1
            FROM resource_occupancies ro
            WHERE ro.tenant_id = tenant_a
              AND ro.resource_id = resource_adjacent
              AND ro.status = 'ACTIVE'
              AND ro.period && tstzrange(
                  '2031-01-10 10:00:00+00',
                  '2031-01-10 11:00:00+00',
                  '[)'
              )
        )
    INTO result_available;

    IF NOT result_available THEN
        RAISE EXCEPTION
            'M3 AVAILABILITY FAILURE: adjacent [) period overlapped';
    END IF;

    --------------------------------------------------------------------
    -- TEST 5
    -- Occupancy from another tenant must not affect tenant A.
    --------------------------------------------------------------------

    SELECT
        NOT EXISTS (
            SELECT 1
            FROM resource_occupancies ro
            WHERE ro.tenant_id = tenant_a
              AND ro.resource_id = resource_tenant_b
              AND ro.status = 'ACTIVE'
              AND ro.period && tstzrange(
                  '2031-01-10 10:00:00+00',
                  '2031-01-10 11:00:00+00',
                  '[)'
              )
        )
    INTO result_available;

    IF NOT result_available THEN
        RAISE EXCEPTION
            'M3 AVAILABILITY FAILURE: cross-tenant occupancy leaked';
    END IF;

    RAISE NOTICE
        'BCOS M3 AVAILABILITY POSTGRESQL TEST SUITE: PASS';
END
$bcos_availability$;

ROLLBACK;
