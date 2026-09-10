# ADR — M7-A3 Outbox Consumer Contract

## Status

APPROVED

## Context

BCOS-M7-A2 froze the Billing boundary:

checkout
→ USAGE_COMPLETED
→ Transactional Outbox
→ asynchronous/idempotent worker
→ Pricing/Billing
→ Invoice/InvoiceItem

The physical Outbox schema already provides:

- status: PENDING, PROCESSING, PROCESSED, FAILED
- attempts
- available_at
- processed_at
- last_error
- UNIQUE (tenant_id, dedupe_key)
- delivery index on (status, available_at, created_at)

The worker currently exists only as a skeleton and has no Outbox consumer implementation.

## Decision

### Eligible events

The worker may claim only events satisfying:

- status = PENDING
- available_at <= now()

Eligible events are ordered by:

1. available_at
2. created_at

### Concurrent claim

Claiming must occur inside a short database transaction using PostgreSQL row-level locking:

FOR UPDATE SKIP LOCKED

This prevents concurrent workers from claiming the same event while allowing each worker to advance independently through the queue.

### Claim transition

When an event is successfully claimed:

PENDING
→ PROCESSING

The worker increments attempts when the processing attempt actually begins.

### Successful processing

On successful completion:

PROCESSING
→ PROCESSED

The worker sets:

- processed_at = now()
- last_error = NULL

### Recoverable processing failure

A recoverable failure must not lose the event.

The event returns to:

PROCESSING
→ PENDING

The worker records:

- last_error with sanitized diagnostic information
- available_at with the next eligible retry time

The retry limit and backoff policy are intentionally not defined by this ADR.

### FAILED status

FAILED is reserved for a future explicit retry/failure policy, including:

- exhausted retries
- failures classified as non-recoverable

This ADR does not define those thresholds or classifications.

### Unknown event types

Unknown event types must never be silently marked as PROCESSED.

### Supported event type

The first supported event type is:

USAGE_COMPLETED

Its frozen payload remains:

{
  "usage_id": "<usage UUID>",
  "checked_out_at": "<ISO datetime>"
}

The payload must not be expanded merely to simplify the worker.

Additional information must be hydrated tenant-safely from authoritative database state.

### Transaction boundary

Claiming must use a short transaction.

The worker must not hold the claim row lock during the complete Pricing/Billing operation.

Claim and financial processing are therefore separate transactional phases.

### Abandoned PROCESSING recovery

The current schema does not provide an explicit:

- claimed_at
- locked_until
- worker lease

Therefore recovery of events abandoned in PROCESSING after worker failure remains an explicit unresolved production requirement.

The system must not be considered production-ready for Outbox processing until this recovery policy is defined and implemented.

## Initial implementation sequence

1. Worker foundation
2. Safe Outbox claim
3. USAGE_COMPLETED dispatcher
4. Retry/recovery mechanics
5. Pricing/Billing integration

## Non-goals

This ADR does not define:

- overtime calculation
- pricing formula
- rounding
- tolerance
- discounts
- interpretation of PricingRule.rule_definition
- retry count
- backoff algorithm
- FAILED threshold
- abandoned PROCESSING lease/recovery mechanism
- Payment creation or settlement

## Governance

BCOS-M7-A2 remains HUMAN HOMOLOGATED / LOCKED.

This ADR does not reopen or modify the frozen M7-A2 Billing boundary.

Quem pede um, pede bis.

## Processing Recovery Field — HUMAN APPROVED

The Outbox requires an explicit temporal reference for abandoned
`PROCESSING` recovery.

Approved physical field:

```sql
processing_started_at TIMESTAMPTZ NULL
```

Approved semantics:

PENDING -> PROCESSING sets processing_started_at = now().
PROCESSING -> PROCESSED clears processing_started_at.
recoverable failure PROCESSING -> PENDING clears processing_started_at.
created_at must not be used as processing-start evidence.
available_at must not be overloaded as processing-start evidence.
recovery timeout remains undefined.
retry backoff remains undefined.
retry limit remains undefined.
FAILED transition policy remains undefined.
worker_id, heartbeat and locked_until remain out of scope.

This decision does not yet authorize a migration. Schema evolution follows
only after this contract is persisted.

Human approval:

APROVADO M7-A3 PROCESSING RECOVERY FIELD

Quem pede um, pede bis.

## M7-A3-T2 — Recoverable Retry Scheduling Contract

**Status:** HUMAN APPROVED

For a recoverable processing failure, an Outbox event transitions from
`PROCESSING` back to `PENDING`.

The retry schedule is determined from the attempt that has just failed:

`delay_seconds = min(30 * 2^(attempts - 1), 900)`

The event MUST be updated with:

- `status = PENDING`;
- `processing_started_at = NULL`;
- `last_error` containing only a sanitized error representation;
- `available_at = now() + delay_seconds`.

`available_at` MUST be strictly in the future when the recoverable-failure
transition is persisted.

The transition MUST only affect an event that still has status `PROCESSING`.

The `attempts` value MUST NOT be incremented by the recoverable-failure
transition. Attempts continue to be incremented only when a new processing
attempt actually begins, as defined by the existing M7-A3 consumer contract.

For V1, the resulting schedule is:

- attempt 1: 30 seconds;
- attempt 2: 60 seconds;
- attempt 3: 120 seconds;
- attempt 4: 240 seconds;
- attempt 5: 480 seconds;
- attempt 6 and subsequent attempts: 900 seconds.

This contract defines scheduling only. It MUST NOT be interpreted as defining
a maximum retry count or a terminal failure policy.

### Explicit non-goals

This decision does not define:

- maximum number of attempts;
- transition to `FAILED`;
- terminal failure criteria;
- abandoned `PROCESSING` recovery timeout;
- worker heartbeat, lease, or ownership;
- Pricing or Billing semantics;
- Payment creation or settlement.

Those concerns remain outside M7-A3-T2 and require separate explicit
architectural decisions before implementation.

## M7-A3-T3 — Error Sanitization Contract

**Status:** HUMAN APPROVED

Recoverable Outbox processing failures may persist a sanitized diagnostic
representation in `last_error`.

The persisted representation MUST use the following form when an exception
message is present:

`<ExceptionClass>: <sanitized message>`

When the exception message is empty, the persisted representation MUST contain
only:

`<ExceptionClass>`

The sanitization rules are:

- maximum persisted length: 500 characters;
- carriage returns, line feeds, and tab characters MUST be replaced with spaces;
- repeated whitespace MUST be normalized;
- traceback MUST NOT be persisted;
- `repr(exc)` MUST NOT be persisted;
- stack traces MUST NOT be persisted;
- environment variables MUST NOT be persisted;
- `DATABASE_URL`, tokens, secrets, credentials, or equivalent sensitive values
  MUST NOT be persisted;
- truncation MUST occur only after sanitization.

`last_error` is operational diagnostic data only. It MUST NOT define terminal
failure behavior, retry limits, or transition to `FAILED`.

### Explicit non-goals

This decision does not define:

- maximum retry count;
- transition to `FAILED`;
- terminal failure criteria;
- abandoned `PROCESSING` recovery timeout;
- worker heartbeat, lease, or ownership;
- Pricing or Billing semantics;
- Payment creation or settlement.

Those concerns remain outside M7-A3-T3 and require separate explicit
architectural decisions before implementation.


## M7-A3-T4 — Abandoned PROCESSING Recovery Contract

**Status:** HUMAN APPROVED

An Outbox event is eligible for abandoned-processing recovery only when all
of the following are true:

- `status = PROCESSING`;
- `processing_started_at IS NOT NULL`;
- `processing_started_at <= now() - 15 minutes`.

The V1 abandoned-processing timeout is 15 minutes.

Eligible abandoned events transition from `PROCESSING` back to `PENDING`.

The recovery transition MUST set:

- `status = PENDING`;
- `processing_started_at = NULL`;
- `available_at = now()`;
- `last_error = ProcessingRecoveryError: abandoned PROCESSING recovered after timeout`.

The recovery transition MUST NOT increment or decrement `attempts`.

The existing attempt has already been counted when the event entered
`PROCESSING`. A subsequent attempt is counted only when the event is claimed
again through the existing `PENDING -> PROCESSING` claim contract.

The M7-A3-T2 recoverable-failure backoff MUST NOT be applied by abandoned
processing recovery. An abandoned event becomes immediately eligible for a
new claim after recovery.

Recovery MUST be atomic and concurrency-safe. An update MUST only affect an
event that still has status `PROCESSING` and still satisfies the approved
15-minute cutoff at the time of the recovery statement.

A `PROCESSING` event whose `processing_started_at` is `NULL` MUST NOT be
automatically recovered. Without a valid processing-start timestamp, the
worker has no approved temporal evidence that the event is abandoned.

### Explicit non-goals

This decision does not define:

- maximum retry count;
- transition to `FAILED`;
- terminal failure criteria;
- worker heartbeat;
- worker ownership or worker identifier;
- lease or `locked_until`;
- Pricing or Billing semantics;
- Payment creation or settlement.

Human approval:

APROVADO M7-A3-T4 ABANDONED PROCESSING RECOVERY CONTRACT

Quem pede um, pede bis.


## M7-A3-T5 — Consumer Execution Lifecycle Contract

**Status:** HUMAN APPROVED

This contract freezes the V1 execution lifecycle for processing one Outbox
event while preserving the previously approved separation between claim,
processing, retry, and abandoned PROCESSING recovery.

### One-event iteration

A single consumer iteration processes at most one Outbox event.

The claim phase runs in its own short transaction:

1. call `claim_next_event()`;
2. if an eligible event is claimed, commit the claim transaction;
3. if no eligible event exists, finish the iteration as IDLE without error.

No polling interval or long-running loop semantics are defined by this
contract.

### Processing transaction

After a successful claim, processing starts in a new transaction.

For the currently supported `USAGE_COMPLETED` event:

1. dispatch the event through `dispatch_event(...)`;
2. execute the event handler;
3. after the handler succeeds, execute `mark_event_processed(...)`;
4. commit only after both processing and the Outbox success transition have
   succeeded.

The future Pricing/Billing effects produced by the handler and the transition
from `PROCESSING` to `PROCESSED` MUST therefore be committed atomically in the
same processing transaction.

No partial financial effects from a failed attempt may remain persisted.

### Failure path

If any exception occurs during dispatch, handler execution, or
`mark_event_processed(...)`:

1. roll back the processing transaction;
2. open a new short transaction;
3. execute `mark_event_for_retry(...)`;
4. commit the retry transition.

The retry transition MUST continue to obey the approved M7-A3-T2 retry
scheduling contract.

The persisted error MUST continue to obey the approved M7-A3-T3 error
sanitization contract.

An unknown event type MUST NOT be silently marked `PROCESSED`.

### Terminal failure policy

This contract does not define:

- maximum attempts;
- automatic transition to `FAILED`;
- terminal failure criteria.

`FAILED` remains reserved for a future explicit policy decision.

### Abandoned PROCESSING recovery

The approved M7-A3-T4 abandoned PROCESSING recovery remains a separate
maintenance concern.

This contract does not implicitly run `recover_abandoned_events()` before or
after every claim.

Its operational cadence requires a separate explicit decision.

### Explicit non-goals

This contract does not define:

- polling interval;
- infinite worker loop;
- shutdown or signal handling;
- heartbeat;
- worker ownership or worker ID;
- lease or `locked_until`;
- internal worker concurrency;
- number of worker instances;
- Pricing/Billing calculation semantics;
- Payment creation or settlement.

## M7-A3-T6 — Worker Runtime Loop & Recovery Cadence Contract

Status: HUMAN APPROVED

The V1 worker runtime follows these rules:

1. On worker startup, run `recover_abandoned_events()` once in its own short transaction before the first consumer iteration.
2. One worker instance executes `process_one()` sequentially, with no internal event-processing concurrency.
3. After `PROCESSED` or `RETRY_SCHEDULED`, the next consumer iteration may begin immediately.
4. After `IDLE`, wait 5 seconds before attempting the next consumer iteration.
5. In addition to startup recovery, run `recover_abandoned_events()` every 60 seconds in its own short transaction.
6. The 60-second cadence does not change the M7-A3-T4 abandoned-processing cutoff of 15 minutes.
7. Recovery and `process_one()` never share the same transaction.
8. A recoverable event failure handled by T5 does not terminate the runtime loop.
9. Infrastructure failures outside the T5 event failure path are not converted into event retry outcomes. They propagate and terminate the worker process with failure so an external supervisor may restart it.
10. Normal cancellation or interruption must not fabricate an event retry outside the T5 failure path.

Explicit non-goals:

- internal worker concurrency;
- worker identity or ownership;
- heartbeat or lease;
- maximum attempts or terminal `FAILED` policy;
- dynamic runtime interval configuration;
- Pricing/Billing semantics;
- Payment creation or settlement;
- external supervisor or deployment restart policy.

## M7-A3-T7 — Pricing & Overtime Business Rules Contract

**Status:** HUMAN APPROVED

This contract defines the V1 business behavior for contracted time, overtime,
conflict-aware penalties, forgiveness, and configurable coworking pricing rules.

### 1. Supported commercial modalities

The BCOS Pricing/Billing flow must support these contractual modalities:

- hourly;
- period;
- weekly;
- monthly.

The Pricing Engine must not hard-code monetary values directly in worker code.
Commercial values and applicable policies must remain administrable by the coworking.

Each commercial modality may have its own coworking-configured base price:

- hourly;
- period;
- weekly;
- monthly.

Prices may vary between configured commercial rules. Period rules may also have
different configured prices for distinct coworking-defined periods, such as morning
and afternoon.

The applicable commercial rule and contracted pricing context must remain frozen in
the Booking pricing_snapshot so later rule or price changes do not rewrite the
financial context originally contracted.

This decision does not yet define how a period, weekly, or monthly base price is
converted into an equivalent hourly price for proportional overtime calculations.

### 2. Hourly bookings

For an hourly booking:

- when the booked end time is reached and another professional is scheduled to use
  the same resource immediately afterward, the professional who exceeds the booked
  time may be subject to a penalty because another professional is waiting;
- when there is no immediately following booking for the same resource and the
  exceeded time is from 1 through 29 minutes, overtime is calculated proportionally
  by exact exceeded minutes using the applicable hourly price;
- the proportional overtime formula is:
  `(applicable hourly price / 60) * exceeded whole minutes`;
- the resulting proportional overtime charge may be forgiven by an authorized
  coworking user;
- when the exceeded time is 30 minutes or more, the next full hour is charged;
- therefore, exactly 30 minutes already reaches the full-hour charging threshold.

The conflict penalty must be configurable by the coworking using one of these
commercial modes:

- a fixed monetary amount in BRL; or
- a percentage applied over the applicable hourly price.

The worker must not hard-code the penalty amount.

The occurrence of a conflict penalty must remain distinguishable and traceable from
the normal overtime charge.

This contract does not yet define the exact persistence schema or administrative API
used to configure these penalty modes.

### 3. Period bookings

The coworking may define fixed periods, including examples such as:

- morning: 08:00 to 12:00;
- afternoon: 12:00 to 18:00.

For a period booking:

- if another professional is scheduled immediately after the contracted period for
  the same resource, exceeding the end time may result in a penalty;
- when there is no conflicting following booking, overtime follows the applicable
  overtime policy;
- for afternoon or any other period that reaches reception closing, overtime charging
  must still obey the approved M7-A2-T1 reception closing temporal contract.

Time after the applicable reception closing cutoff must not generate OVERTIME.

### 4. Weekly plans

Weekly plans use fixed contracted hours.

- When another professional is scheduled immediately after the fixed contracted time
  for the same resource, exceeding that time may result in a penalty.
- When there is no conflicting following booking, overtime follows the same applicable
  rules as hourly or period bookings, according to the contracted schedule.

### 5. Monthly plans

Monthly plans are based on fixed full periods, one or two times per week.

They inherit the same applicable overtime and conflict behavior defined for hourly
or period bookings, according to the contracted schedule.

### 6. Configurable coworking policies

Business rules must be administrable by authorized coworking users.

The system must support the business capability to configure and manage applicable
rules instead of embedding commercial values directly in code.

This includes the business need to support operations such as:

- create;
- edit;
- deactivate/block;
- delete when allowed by lifecycle/integrity rules;
- forgive an applicable charge;
- manage future pricing and overtime policies.

The exact authorization matrix, lifecycle constraints, API operations, persistence
shape, and audit event model remain subject to their respective implementation
contracts and existing Architecture Freeze rules.

### 7. Automatic rule versus administrative decision

Automatic pricing behavior and administrative overrides are distinct concepts.

A configured automatic rule may determine that an overtime charge or penalty applies.

An authorized forgiveness or override must not silently erase the fact that a
financial decision occurred. It must remain representable as a traceable business
action when Billing/Audit integration is implemented.

Forgiveness must preserve the original OVERTIME financial fact.

When an authorized coworking user forgives an overtime charge:

- the original OVERTIME item remains recorded with its calculated amount;
- a separate DISCOUNT item represents the forgiven amount;
- the discount may represent a full or partial forgiveness;
- the financial history must therefore preserve both the amount originally due and
  the administrative decision that reduced it.

Forgiveness must not silently delete the OVERTIME item or rewrite it to zero.

### 8. Authoritative runtime context

The future USAGE_COMPLETED Pricing/Billing handler must hydrate authoritative state
tenant-safely from the database.

The financial decision may use, as applicable:

- Usage actual timestamps;
- Booking contracted starts_at and ends_at;
- Booking immutable pricing_snapshot;
- Booking unit/resource/professional context;
- applicable Unit reception hours;
- immediately following booking/resource occupancy context required to determine
  scheduling conflict.

The USAGE_COMPLETED Outbox payload must not be expanded merely to duplicate this state.

### 9. Billing boundary

Pricing determines the financial result.

Billing materializes that result into Invoice and InvoiceItem records under the
existing idempotency and tenant-isolation constraints.

Existing financial item types include:

- BASE_LEASE;
- OVERTIME;
- ADJUSTMENT;
- DISCOUNT.

This contract does not redefine Payment creation or settlement.

### 10. Explicit non-goals and pending commercial decisions

The following remain undefined until separately approved:

- exact internal schema and semantics of PricingRule.rule_definition;
- authorization matrix for rule administration and forgiveness;
- API CRUD details for pricing-policy administration;
- audit event names and metadata for overrides/forgiveness;
- terminal Outbox FAILED/retry policy;
- Payment creation and settlement semantics.

These pending points must not be invented during implementation.

## M7-A3-T8 - Pricing Rule Definition V1 Contract

**Status:** HUMAN APPROVED

Purpose: define the machine-readable V1 structure of
`PricingRule.rule_definition` required by the already approved
Pricing/Overtime business rules, without changing the outer
`Booking.pricing_snapshot` structure.

### Approved minimum fields

- `schema_version`
- `modality`
- `base_price_amount`
- `overtime`
- optional `conflict_penalty`

### Proposed modalities

- `HOURLY`
- `PERIOD`
- `WEEKLY`
- `MONTHLY`

### Proposed overtime object

The `overtime` object must carry the values needed to execute the
already approved rules, including:

- explicit overtime hourly monetary basis;
- proportional charging through 29 exceeded minutes;
- full-hour threshold starting exactly at 30 minutes;
- indication that forgiveness is permitted.

For non-hourly plans, the overtime hourly monetary basis must be
stored explicitly in the frozen rule. The worker must not invent a
conversion from period, weekly, or monthly base price.

### Reception closing

M7-A2-T1 remains authoritative.

Checkout must be evaluated in the Unit IANA timezone and time after
reception closing must not generate OVERTIME.

Missing Reception Hours configuration remains a processing error.

### Conflict penalty

When configured by the coworking, the rule must support the already
approved modes:

- fixed BRL amount;
- percentage over the applicable overtime hourly monetary basis.

The worker must never hard-code a penalty.

### Frozen source

The financial worker must consume the rule definition frozen inside:

`Booking.pricing_snapshot["pricing_rule"]["rule_definition"]`

It must not resolve a newer live PricingRule to recalculate the
commercial agreement.

### Financial safety

Financial arithmetic must use decimal arithmetic rather than binary
floating point.

Malformed or unsupported frozen pricing data must fail closed and use
the existing Outbox retry/error lifecycle.

### Not defined by this contract

This proposal does not yet freeze:

- exact JSON key names beyond the conceptual fields above;
- exact decimal-string validation format;
- rounding mode;
- administrative PricingRule CRUD/UI;
- RBAC matrix for forgiveness;
- Audit event names;
- Outbox terminal FAILED policy;
- Payment creation or settlement.

## M7-A3-T9 - Pricing Rule Definition JSON Schema V1

**Status:** HUMAN APPROVED

Purpose: freeze the V1 machine-readable JSON structure used inside
`PricingRule.rule_definition` for the already approved M7-A3-T8 contract.

### Approved JSON structure

```json
{
  "schema_version": 1,
  "modality": "HOURLY | PERIOD | WEEKLY | MONTHLY",
  "base_price_amount": "decimal",
  "overtime": {
    "hourly_price_amount": "decimal",
    "proportional_until_minutes": 29,
    "full_hour_from_minutes": 30,
    "forgiveness_allowed": true
  },
  "conflict_penalty": {
    "mode": "FIXED_AMOUNT | PERCENTAGE",
    "value": "decimal"
  }
}
Approved field semantics
schema_version must be 1.
modality must be one of:
HOURLY
PERIOD
WEEKLY
MONTHLY
base_price_amount is the configured base monetary amount for the
contracted modality.
overtime.hourly_price_amount is the explicit hourly monetary basis
used for overtime calculations.
overtime.proportional_until_minutes is 29.
overtime.full_hour_from_minutes is 30.
overtime.forgiveness_allowed indicates that authorized forgiveness
may be applied according to the already approved business rules.
conflict_penalty is optional.
when present, conflict_penalty.mode must be:
FIXED_AMOUNT; or
PERCENTAGE.
conflict_penalty.value carries the configured monetary amount or
percentage value according to the selected mode.
Frozen source

The worker must consume this structure only from:

Booking.pricing_snapshot["pricing_rule"]["rule_definition"]

It must not replace the frozen pricing rule with a newer live rule.

Validation behavior

Unsupported, malformed, missing, or incompatible required pricing data
must fail closed.

The event must remain subject to the already approved Outbox
retry/error lifecycle and must not be silently marked as processed.

Financial values must be parsed using decimal arithmetic rather than
binary floating point.

Explicitly still undefined

This contract does not define:

monetary rounding mode;
currency quantization policy;
administrative PricingRule CRUD/UI;
RBAC matrix for rule administration or forgiveness;
Audit event names and metadata;
Outbox terminal FAILED policy;
Payment creation or settlement semantics.

## M7-A3-T10 - Overtime Minute Precision Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the temporal precision used to convert actual overtime duration into
billable overtime minutes, without changing the already approved commercial
rules of M7-A3-T7.

### Approved Contract

1. Actual overtime duration is measured from the contracted booking end time to
   the authoritative Usage `checked_out_at`.

2. Overtime is converted to billable minutes using **completed whole minutes**.

3. Residual seconds do not promote the overtime duration to the next minute.

4. Examples:
   - less than 1 completed minute -> 0 billable overtime minutes;
   - 1m00s through 1m59s -> 1 billable overtime minute;
   - 29m59s -> 29 billable overtime minutes;
   - 30m00s -> 30 billable overtime minutes;
   - 30m59s -> 30 billable overtime minutes.

5. The already approved full-hour threshold remains unchanged:
   - 1 through 29 completed overtime minutes remain within the proportional /
     forgivable range;
   - exactly 30 completed overtime minutes reaches the full-next-hour threshold;
   - more than 30 completed overtime minutes remains subject to the already
     approved full-hour overtime rule.

6. Reception closing evaluation remains based on the real local timestamp
   defined by M7-A2-T1. Minute truncation must not move, round, or redefine the
   reception `closes_at` boundary.

7. This contract defines temporal quantification only. It does not define
   monetary rounding, currency quantization, conflict detection, conflict
   penalty calculation, Invoice materialization, Payment handling, or worker
   runtime wiring.

