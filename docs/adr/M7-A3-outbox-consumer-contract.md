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

## M7-A3-T11 - Reception Closing Overtime Segmentation Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the approved business rule for overtime that crosses the reception
closing boundary.

This contract supersedes only the previous interpretation that overtime
occurring after reception closing must always be excluded from charging.

### Approved Contract

1. Reception closing does not erase overtime that occurs after `closes_at`.

2. When overtime crosses the reception closing boundary, the worker must
   account for the overtime in separate temporal segments:

   - overtime occurring up to `closes_at`;
   - overtime occurring after `closes_at`.

3. Example:

   - contracted booking end: 17:30;
   - reception closes: 18:00;
   - actual checkout: 18:20.

   The system must account for:

   - 30 minutes of overtime from 17:30 through 18:00;
   - 20 minutes of overtime after reception closing, from 18:00 through 18:20.

4. Overtime occurring after reception closing remains financially traceable and
   must not be discarded or silently converted to zero.

5. The overtime segment occurring after reception closing may be:

   - charged; or
   - forgiven by an authorized coworking decision.

6. Forgiveness does not delete the original overtime record. When Billing is
   materialized, the already approved T7 rule remains authoritative:

   - the original OVERTIME amount remains recorded;
   - forgiveness is represented separately through DISCOUNT.

7. Exactly `closes_at` belongs to the segment up to reception closing.
   Only elapsed time strictly after `closes_at` belongs to the
   after-closing segment.

8. M7-A3-T10 remains authoritative for conversion of elapsed durations into
   completed whole overtime minutes.

9. This contract defines temporal segmentation and charge/forgiveness
   eligibility only. It does not define monetary rounding, currency
   quantization, RBAC details, Invoice persistence mechanics, Payment handling,
   or worker `main.py` wiring.

## M7-A3-T12 - Monetary Precision & Rounding Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the monetary precision and rounding rules required by the M7 Pricing/Billing worker before any financial amount is materialized.

This contract does not reopen or modify previously approved Pricing, Overtime, Reception Closing, forgiveness, or Billing business rules.

### Contract

1. All financial arithmetic MUST use decimal arithmetic.
   - Python `Decimal` is the canonical worker representation.
   - Binary floating-point arithmetic MUST NOT be used for financial calculations.

2. Intermediate calculations MAY retain full available Decimal precision.
   - Intermediate values MUST NOT be unnecessarily quantized after each operation.

3. Monetary values that are materialized or persisted MUST be quantized to two decimal places:
   - `Decimal("0.01")`

4. The V1 currency remains:
   - `BRL`

5. The V1 monetary rounding mode is:
   - `ROUND_HALF_UP`

6. Examples:
   - `1.664` -> `1.66`
   - `1.665` -> `1.67`
   - `1.666...` -> `1.67`

7. Quantization MUST occur on the monetary result that will be persisted or materially exposed as a financial amount, rather than repeatedly during intermediate arithmetic.

8. The existing physical Billing baseline remains authoritative:
   - Invoice monetary amounts use `NUMERIC(12, 2)`.
   - Invoice Item monetary amounts use `NUMERIC(12, 2)`.
   - Payment amount uses `NUMERIC(12, 2)`.
   - Invoice Item quantity uses `NUMERIC(12, 4)` and is not itself a monetary precision rule.

9. Invoice totals MUST be derived from the monetary values materialized for their items.
   - The worker MUST NOT independently recompute invoice totals using a separate arithmetic path that could produce a different rounded result.

10. Example under the already approved proportional overtime rule:
    - applicable overtime hourly price: `100.00`
    - completed overtime minutes: `1`
    - intermediate amount: `100.00 / 60 * 1`
    - materialized monetary amount: `1.67`

### Failure behavior

If a financial calculation cannot be represented or validated under this contract, processing MUST fail closed and follow the existing M7-A3 Outbox retry/error lifecycle.

### Non-goals

This contract does not yet define:

- Invoice persistence implementation;
- Invoice Item persistence implementation;
- exact OVERTIME item metadata;
- administrative forgiveness execution;
- RBAC for forgiveness;
- conflict detection implementation;
- terminal `FAILED` policy;
- Payment creation or settlement;
- worker `main.py` wiring.

## M7-A3-T13 - Multi-Hour Overtime Charging Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze how overtime charging continues beyond the first hour while preserving the
Coworking as the authority that defines the commercial proportionality and
full-hour threshold.

This contract does not authorize the worker to hard-code a universal commercial
threshold.

### Contract

1. The Coworking defines the overtime commercial rule.

2. The worker MUST NOT hard-code `29` minutes as a universal proportional limit
   or `30` minutes as a universal full-hour threshold.

3. The frozen Pricing Rule remains the authoritative source for these parameters:

   - `overtime.proportional_until_minutes`
   - `overtime.full_hour_from_minutes`
   - `overtime.hourly_price_amount`

4. A Coworking MAY configure the already discussed rule in which:

   - exceeded minutes below the configured full-hour threshold are charged
     proportionally;
   - when the configured threshold is reached or exceeded, a full additional
     hour is charged.

5. When the configured threshold is `30`, exactly `30` minutes already reaches
   the full-hour charging threshold.

6. For overtime extending across multiple hours, charging is evaluated using
   complete elapsed hour blocks plus the remaining minutes.

7. Each complete 60-minute overtime block contributes one full overtime hour
   using the frozen `overtime.hourly_price_amount`.

8. Remaining minutes after the complete overtime hour blocks MUST be evaluated
   using the proportional/full-hour parameters frozen by the Coworking in the
   Pricing Rule.

9. Example when the Coworking configuration is:

   - `proportional_until_minutes = 29`
   - `full_hour_from_minutes = 30`

   then:

   - 60 minutes = 1 full overtime hour;
   - 61 through 89 minutes = 1 full overtime hour plus proportional remaining
     minutes;
   - 90 through 119 minutes = 2 full overtime hours;
   - 120 minutes = 2 full overtime hours;
   - 120 through 149 minutes follows the same rule for the remaining minutes;
   - 150 minutes reaches 3 full overtime hours.

10. The same algorithm MUST work with another valid Coworking-configured
    proportional/full-hour threshold without changing worker source code.

11. The commercial parameters used for calculation MUST come from the immutable
    Booking `pricing_snapshot`, never from a newer live Pricing Rule.

12. Monetary arithmetic and materialization continue to follow M7-A3-T12:

    - Python `Decimal`;
    - no binary float;
    - BRL;
    - materialized monetary values quantized to `Decimal("0.01")`;
    - `ROUND_HALF_UP`.

13. Overtime forgiveness remains an administrative decision under the already
    approved rule:

    - the original OVERTIME value remains recorded;
    - any forgiven value is represented separately by DISCOUNT.

### Supersession clarification

This contract supersedes the prior technical interpretation that the worker may
treat `29` and `30` as unconditional hard-coded commercial constants.

The previously approved `29/30` behavior remains valid when those are the values
configured and frozen by the Coworking for the applicable Pricing Rule.

The Coworking remains the authority that defines the proportionality and the
threshold at which remaining overtime becomes a full additional hour.

### Non-goals

This contract does not yet define:

- Pricing Rule administration UI;
- RBAC for changing commercial rules;
- Invoice or Invoice Item persistence implementation;
- exact OVERTIME metadata;
- conflict detection implementation;
- administrative forgiveness execution;
- terminal `FAILED` policy;
- Payment creation or settlement;
- worker `main.py` wiring.

## M7-A3-T14 - Invoice Materialization Mode Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the business rule that Billing must support more than one Invoice
materialization mode and that the Coworking, according to its commercial
contract with each professional, defines which mode applies.

### Contract

1. BCOS MUST support both Invoice materialization modes:

   - `PER_USAGE`
   - `ACCUMULATED_OPEN_INVOICE`

2. The Coworking is the authority that defines which Invoice materialization
   mode applies according to the commercial contract established with the
   professional.

3. The worker MUST NOT choose an Invoice materialization mode by itself.

4. The worker MUST NOT assume one of the modes as a universal default.

### PER_USAGE

5. In `PER_USAGE` mode, each completed Usage produces its own Invoice.

6. Financial items generated from that Usage belong to the Invoice associated
   with that specific Usage.

7. Reprocessing the same `USAGE_COMPLETED` event MUST NOT create duplicate
   financial items or duplicate effective billing for that Usage.

### ACCUMULATED_OPEN_INVOICE

8. In `ACCUMULATED_OPEN_INVOICE` mode, financial items from multiple completed
   Usages of the same professional MAY be accumulated into an applicable open
   Invoice.

9. A new completed Usage MAY append its financial items to that applicable
   open Invoice while the Invoice remains eligible to receive additional
   charges under the professional contract.

10. A settled, cancelled, or otherwise no-longer-eligible Invoice MUST NOT
    receive new Usage charges.

11. Reprocessing the same `USAGE_COMPLETED` event MUST NOT duplicate the
    financial item for the same Usage and item type.

### Existing physical idempotency

12. The current Billing schema remains authoritative for Invoice Item
    idempotency:

    `UNIQUE (tenant_id, usage_id, item_type)`

13. Billing materialization MUST remain tenant-safe.

14. Invoice ownership remains associated with the professional through the
    existing `professional_id`.

### Contract authority

15. The applicable Invoice materialization mode comes from the professional's
    commercial arrangement configured by the Coworking.

16. Changes to a professional's future commercial arrangement MUST NOT silently
    rewrite already materialized historical Billing records.

### Non-goals

This contract does not yet define:

- the exact database field or table that stores the professional's selected
  Invoice materialization mode;
- the administrative screen used to configure the mode;
- the exact open-Invoice lookup query;
- Invoice closing cadence or due-date policy;
- manual Invoice closing;
- Billing RBAC;
- Billing Audit event names;
- Payment creation or settlement;
- worker `main.py` wiring.

## M7-A3-T15 - Professional Billing Contract History

**Status:** HUMAN APPROVED

### Purpose

Freeze the historical contract model used to determine which Invoice
materialization mode applies to a professional over time.

This contract preserves historical Billing behavior when the Coworking changes
the professional's commercial arrangement in the future.

### Contract

1. The Coworking MAY change a professional's Invoice materialization mode over
   time.

2. Supported Invoice materialization modes remain:

   - `PER_USAGE`
   - `ACCUMULATED_OPEN_INVOICE`

3. A professional's Billing configuration MUST be historically versioned rather
   than represented only as a mutable current value.

4. Each professional Billing contract configuration MUST define its own
   validity period.

5. The historical contract model MUST support at least:

   - `valid_from`
   - `valid_until`

6. The applicable contract for a Usage MUST be resolved according to the
   contract validity applicable to that Usage/reservation context.

7. The worker MUST NOT simply read the professional's latest/current contract
   when materializing historical Billing.

8. A future contract change MUST NOT silently rewrite:

   - previously materialized Invoices;
   - previously materialized Invoice Items;
   - the Invoice materialization mode that applied to historical Usage.

9. Professional Billing contract history is tenant-scoped.

10. A contract record MUST belong to exactly one professional within the same
    tenant.

11. Professional Billing contract history is a Billing/commercial concern.

12. The Invoice materialization mode MUST NOT be stored inside
    `pricing_rules.rule_definition`.

13. Pricing Rules remain responsible for financial pricing semantics, while the
    Professional Billing Contract determines how those financial results are
    grouped into Invoices.

### Temporal behavior

14. The contract validity model MUST permit:

    - an active contract with no `valid_until`;
    - a closed historical contract;
    - a future contract beginning at a later `valid_from`.

15. When a professional changes Billing mode, the previous historical contract
    MUST remain preserved.

16. The system MUST fail closed if no unambiguous applicable Billing contract
    can be resolved for the Usage that is being financially materialized.

### Non-goals

This contract does not yet define:

- the exact physical table name;
- the complete database column set;
- overlap-prevention constraints for contract validity periods;
- administrative CRUD endpoints;
- administrative UI;
- Billing RBAC;
- Billing Audit event names;
- exact open-Invoice lookup rules;
- Invoice closing cadence;
- Payment creation or settlement;
- worker `main.py` wiring.

## M7-A3-T16 - Professional Billing Contract Physical Schema

**Status:** HUMAN APPROVED

### Purpose

Freeze the physical persistence model for the professional Billing contract
history approved in M7-A3-T15.

The schema must preserve tenant isolation, historical validity, and an
unambiguous Invoice materialization mode for a professional at any applicable
point in time.

### Table

The physical model SHALL use a dedicated table:

`professional_billing_contracts`

### Required columns

The table MUST contain at least:

- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `tenant_id UUID NOT NULL`
- `professional_id UUID NOT NULL`
- `invoice_mode`
- `valid_from TIMESTAMPTZ NOT NULL`
- `valid_until TIMESTAMPTZ`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

### Invoice materialization mode

1. `invoice_mode` MUST be physically restricted to the two modes approved in
   M7-A3-T14:

   - `PER_USAGE`
   - `ACCUMULATED_OPEN_INVOICE`

2. The database MUST reject any value outside those approved modes.

3. There is no universal default mode.

4. A contract record MUST explicitly declare its `invoice_mode`.

### Tenant-safe professional ownership

5. Every Billing contract belongs to exactly one professional within the same
   tenant.

6. The physical foreign key MUST preserve tenant isolation through:

   `(professional_id, tenant_id) -> professionals(id, tenant_id)`

7. Cross-tenant professional references MUST be impossible at the database
   constraint level.

### Historical validity

8. `valid_from` is mandatory.

9. `valid_until` MAY be NULL to represent an open-ended contract.

10. When `valid_until` is present:

    `valid_until > valid_from`

    MUST be enforced physically.

11. Historical contract rows MUST remain preserved when a future contract is
    created.

12. Future contracts MAY be stored before their `valid_from` becomes active.

### Temporal non-overlap

13. For the same `(tenant_id, professional_id)`, contract validity intervals
    MUST NOT overlap.

14. Temporal non-overlap MUST be enforced physically by PostgreSQL and MUST NOT
    depend only on worker or API validation.

15. An open-ended contract therefore prevents another overlapping contract from
    becoming valid for the same professional until the prior interval is
    properly closed.

16. Adjacent validity intervals are allowed when one contract ends exactly when
    the next contract begins.

17. The physical interval semantics SHALL be modeled as half-open validity:

    `[valid_from, valid_until)`

    so that the exact `valid_until` instant belongs to the following contract,
    when one exists.

### Identity and supporting constraints

18. The table MUST preserve a tenant-safe identity constraint compatible with
    the rest of the BCOS schema:

    `UNIQUE (id, tenant_id)`

19. The physical schema SHOULD provide indexes required for efficient lookup by:

    - `tenant_id`
    - `professional_id`
    - temporal validity

20. Physical constraints are authoritative for invalid or ambiguous contract
    states.

### Separation of responsibilities

21. `professional_billing_contracts` belongs to the Billing/commercial
    configuration boundary.

22. `invoice_mode` MUST NOT be stored in `pricing_rules.rule_definition`.

23. `pricing_rules` remains responsible for pricing semantics.

24. `professional_billing_contracts` determines how calculated financial
    results are grouped into Invoices.

### Migration direction

25. This contract authorizes a future BCOS migration to introduce:

    - the Invoice mode database type;
    - the `professional_billing_contracts` table;
    - tenant-safe foreign keys;
    - validity constraints;
    - PostgreSQL-enforced non-overlapping validity intervals;
    - supporting indexes.

26. The migration MUST preserve all previously locked schema and behavior.

### Non-goals

This contract does not yet define:

- API CRUD endpoints for professional Billing contracts;
- administrative UI;
- RBAC for contract maintenance;
- Audit event names;
- exact worker contract-resolution SQL;
- exact accumulated open-Invoice lookup;
- Invoice closing cadence;
- Payment behavior;
- worker `main.py` wiring.

## M7-A3-T17 - Professional Billing Contract Resolution

**Status:** HUMAN APPROVED

### Purpose

Freeze how the worker resolves the historically applicable professional Billing
contract for a completed Usage.

The resolution must preserve the commercial agreement that applied to the
Booking context and must not drift when the professional's contract changes
later.

### Authoritative resolution key

1. Contract resolution MUST be tenant-safe.

2. The lookup key is:

   - `tenant_id`
   - `professional_id`

3. The authoritative temporal instant is:

   `UsagePricingContext.booking_starts_at`

4. `booking_starts_at` determines which historical professional Billing contract
   applies to the Usage.

5. The worker MUST NOT use the latest/current professional contract merely
   because it is current at processing time.

6. `checked_in_at` and `checked_out_at` MUST NOT determine the historical
   Billing contract version.

### Temporal applicability

7. Contract validity follows the half-open interval approved in M7-A3-T16:

   `[valid_from, valid_until)`

8. A closed contract is applicable when:

   `valid_from <= booking_starts_at`

   AND

   `booking_starts_at < valid_until`

9. An open-ended contract is applicable when:

   `valid_from <= booking_starts_at`

   AND

   `valid_until IS NULL`

10. A contract ending exactly at `booking_starts_at` is NOT applicable to that
    Booking.

11. A contract beginning exactly at `booking_starts_at` IS applicable.

### Resolution cardinality

12. Exactly one professional Billing contract MUST resolve for the Usage.

13. If no applicable contract exists, processing MUST fail closed.

14. If more than one applicable contract is observed, processing MUST fail
    closed.

15. The PostgreSQL temporal exclusion constraint from M7-A3-T16 remains the
    physical authority preventing overlapping professional contracts.

### Historical integrity

16. A later professional contract change MUST NOT change the Invoice
    materialization mode applicable to an earlier Booking.

17. A Booking created under `PER_USAGE` remains governed by that contract even
    if the professional later changes to `ACCUMULATED_OPEN_INVOICE`.

18. A Booking created under `ACCUMULATED_OPEN_INVOICE` remains governed by that
    contract even if the professional later changes to `PER_USAGE`.

19. Worker processing time is irrelevant to historical contract selection.

### Separation of responsibilities

20. Professional Billing contract resolution is separate from Pricing Rule
    resolution.

21. `pricing_snapshot` remains authoritative for frozen Pricing semantics.

22. `professional_billing_contracts` remains authoritative for Invoice
    materialization mode.

23. The professional Billing contract MUST NOT be copied into or inferred from
    `pricing_rules.rule_definition`.

### Worker behavior

24. The worker MAY hydrate the applicable professional Billing contract as part
    of the financial processing context.

25. The resolved result MUST expose at least:

    - professional Billing contract id;
    - tenant id;
    - professional id;
    - invoice materialization mode;
    - valid_from;
    - valid_until.

26. Resolution errors MUST propagate as processing failures and MUST NOT cause an
    Outbox event to be silently marked PROCESSED.

### Non-goals

This contract does not yet define:

- Invoice creation;
- InvoiceItem creation;
- accumulated open-Invoice lookup;
- Invoice closing cadence;
- professional contract CRUD API;
- administrative UI;
- RBAC;
- Audit event names;
- Payment behavior;
- worker `main.py` wiring.

## M7-A3-T18 - Invoice Materialization Idempotency Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the physical and transactional idempotency rules required before the
worker may materialize Billing Invoices.

This contract preserves the two Invoice materialization modes approved in
M7-A3-T14 and the historical professional Billing contract resolution approved
in M7-A3-T17.

### PER_USAGE physical identity

1. `PER_USAGE` MUST have a physical Invoice identity tied to the Usage that
   originated that Invoice.

2. The `invoices` table MUST support:

   `source_usage_id UUID NULL`

3. For an Invoice materialized under `PER_USAGE`, `source_usage_id` MUST
   reference the authoritative completed Usage.

4. `source_usage_id` MUST be tenant-safe through a composite foreign key:

   `(source_usage_id, tenant_id) -> usages(id, tenant_id)`

5. PostgreSQL MUST physically guarantee that the same Usage cannot own more
   than one PER_USAGE Invoice within the tenant.

6. The physical uniqueness authority is:

   `UNIQUE (tenant_id, source_usage_id) WHERE source_usage_id IS NOT NULL`

7. The worker MUST NOT rely only on application checks to prevent duplicate
   PER_USAGE Invoices.

### ACCUMULATED_OPEN_INVOICE behavior

8. For `ACCUMULATED_OPEN_INVOICE`, `source_usage_id` MUST remain NULL.

9. An accumulated Invoice may contain financial items from multiple Usages and
   therefore MUST NOT use a single Usage as its Invoice identity.

10. The existing Invoice lookup index by tenant, professional and status may
    assist future lookup, but it does not define commercial Invoice
    eligibility.

11. This contract does NOT define which OPEN accumulated Invoice is eligible
    for reuse.

12. `ACCUMULATED_OPEN_INVOICE` materialization MUST NOT be implemented until
    the open-Invoice eligibility/lifecycle rule is separately frozen.

### InvoiceItem idempotency

13. The existing physical constraint:

    `UNIQUE (tenant_id, usage_id, item_type)`

    remains authoritative for preventing duplicate financial items generated
    from the same Usage and InvoiceItemType.

14. Invoice-level idempotency and InvoiceItem-level idempotency are separate
    guarantees and both MUST be preserved.

15. The worker MUST NOT treat the InvoiceItem uniqueness constraint alone as
    sufficient protection against duplicate or orphan PER_USAGE Invoices.

### Transactional boundary

16. Invoice creation or reuse, InvoiceItem materialization, Invoice total
    updates and Outbox success marking MUST remain inside the financial
    processing transaction defined by M7-A3-T5.

17. A failed financial transaction MUST roll back its Invoice and InvoiceItem
    mutations.

18. Reprocessing the same `USAGE_COMPLETED` event MUST NOT produce:

    - duplicate effective charges;
    - duplicate PER_USAGE Invoices;
    - orphan Invoices caused by an InvoiceItem uniqueness conflict.

### Materialization mode authority

19. The worker MUST NOT choose the Invoice materialization mode.

20. The mode remains authoritative from the historical professional Billing
    contract resolved under M7-A3-T17.

21. No universal default Invoice materialization mode is authorized.

22. A future professional Billing contract change MUST NOT rewrite historical
    Invoice materialization already performed for an earlier Usage.

### Tenant isolation

23. All Invoice identity and idempotency guarantees MUST be tenant-scoped.

24. A Usage from one tenant MUST never identify or attach to an Invoice from
    another tenant.

### Physical schema authorization

25. A migration adding nullable `invoices.source_usage_id` is authorized.

26. That migration is also authorized to add:

    - the tenant-safe Usage foreign key;
    - the partial unique index/constraint for
      `(tenant_id, source_usage_id)` where `source_usage_id IS NOT NULL`;
    - any supporting index strictly required by this frozen contract.

27. No unrelated Billing schema expansion is authorized by T18.

### Non-goals

This contract does not yet define:

- accumulated OPEN Invoice eligibility;
- accumulated Invoice closing cadence;
- billing competence/period;
- due-date calculation;
- manual Invoice closing;
- BASE_LEASE materialization semantics;
- OVERTIME InvoiceItem metadata shape;
- DISCOUNT materialization details;
- Payment behavior;
- Billing CRUD API;
- administrative UI;
- RBAC;
- Audit event names;
- worker `main.py` wiring.

## M7-A3-T19 - Accumulated Invoice Contract Lifecycle

**Status:** HUMAN APPROVED

### Purpose

Freeze the commercial authority and lifecycle rules that determine whether an
Invoice under `ACCUMULATED_OPEN_INVOICE` remains eligible to receive financial
items from additional Usages.

This contract preserves the Coworking's authority over its commercial
arrangement with each professional and does not impose a universal Billing
cycle.

### Commercial authority

1. Contractual and bureaucratic conditions are defined by the Coworking
   together with the professional.

2. The BCOS MUST register and execute the agreed commercial conditions; it MUST
   NOT invent a universal commercial policy.

3. The Coworking and professional may define contractual conditions involving,
   as applicable:

   - contract duration;
   - Invoice closing conditions;
   - renewal;
   - a new contract;
   - contractual amendments/addenda.

4. No single Invoice closing cadence is mandatory for every professional or
   tenant.

5. When supported by the applicable commercial contract, closing policies may
   include arrangements such as weekly, biweekly, monthly, manual or another
   explicitly configured contractual cadence.

6. The worker MUST NOT choose a closing policy on behalf of the Coworking.

### Accumulated Invoice eligibility

7. An Invoice may receive another Usage under
   `ACCUMULATED_OPEN_INVOICE` only when it is:

   - associated with the same tenant;
   - associated with the same professional;
   - `OPEN`;
   - eligible under the professional's applicable historical Billing contract.

8. `PAID` and `CANCELLED` Invoices MUST NOT receive new financial items.

9. An Invoice that has been contractually closed or is no longer eligible under
   the applicable contractual lifecycle MUST NOT receive new financial items.

10. Merely finding an `OPEN` Invoice for the professional is NOT sufficient to
    establish eligibility.

11. The existing lookup index on tenant, professional and status is a lookup
    aid only; it is not the commercial eligibility authority.

### Historical integrity

12. Contract lifecycle configuration MUST preserve history.

13. Contract termination, renewal, replacement by a new contract or an
    amendment/addendum MUST NOT rewrite previously materialized Billing.

14. A future contractual change MUST NOT retroactively move InvoiceItems from
    one Invoice to another.

15. A future contractual change MUST NOT retroactively change the Invoice
    materialization mode already applied to a historical Usage.

16. The historical professional Billing contract resolution defined in
    M7-A3-T17 remains authoritative for determining the contract applicable to
    the Usage.

### Contract changes

17. Renewal, new contract and amendment/addendum are historically significant
    commercial events and MUST be representable without destroying prior
    contractual history.

18. Where a contractual change modifies Billing behavior for future Usages, the
    changed configuration MUST take effect according to its configured
    temporal validity.

19. The worker MUST NOT simply use the latest/current commercial configuration
    when processing historical Billing.

### Fail-closed behavior

20. If the worker cannot unambiguously determine whether an accumulated Invoice
    is eligible under the applicable contract, financial processing MUST fail
    closed.

21. Missing contractual configuration MUST NOT authorize implicit reuse of an
    arbitrary OPEN Invoice.

22. Multiple candidate Invoices without an authoritative eligibility rule MUST
    NOT be resolved by arbitrary ordering, newest-record selection or
    application guesswork.

### Relationship with previous contracts

23. M7-A3-T14 remains authoritative for the existence of both materialization
    modes:

    - `PER_USAGE`;
    - `ACCUMULATED_OPEN_INVOICE`.

24. M7-A3-T15 remains authoritative for historical professional Billing
    contract configuration.

25. M7-A3-T16 remains authoritative for the physical historical professional
    Billing contract baseline.

26. M7-A3-T17 remains authoritative for resolving the professional Billing
    contract at `booking_starts_at`.

27. M7-A3-T18 remains authoritative for Invoice and InvoiceItem idempotency.

28. T19 does not authorize accumulated Invoice materialization until the
    physical representation of its contractual eligibility/lifecycle is
    separately frozen.

### Non-goals

This contract does not yet define:

- the exact physical columns used to store closing policy;
- the exact schema for weekly, biweekly, monthly, manual or other contractual
  cadence configuration;
- the exact accumulated Invoice eligibility query;
- automatic versus manual closing commands;
- due-date calculation;
- professional contract CRUD API;
- contract document storage;
- electronic signature;
- administrative UI;
- RBAC;
- Audit event names;
- Payment behavior;
- worker `main.py` wiring.

## M7-A3-T20 - Accumulated Invoice Lifecycle Modes V1

**Status:** HUMAN APPROVED

### Purpose

Freeze the V1 set of contractual lifecycle modes available for
`ACCUMULATED_OPEN_INVOICE`.

This contract does not create a universal closing cadence. The applicable mode
is selected by the Coworking according to its commercial arrangement with the
professional.

### V1 lifecycle modes

The supported lifecycle modes are exactly:

- `WEEKLY`
- `BIWEEKLY`
- `MONTHLY`
- `MANUAL`

### Commercial authority

1. The Coworking defines the lifecycle mode together with the professional
   according to the applicable commercial contract.

2. The BCOS MUST NOT choose a lifecycle mode automatically.

3. There is no universal default lifecycle mode.

4. Different professionals in the same tenant MAY use different lifecycle
   modes.

5. A professional's lifecycle mode MAY change over time through termination,
   renewal, a new contract or an amendment/addendum, subject to the historical
   contract rules already frozen in M7-A3-T15 and M7-A3-T19.

### Mode semantics

#### WEEKLY

6. `WEEKLY` represents a contractually configured weekly Invoice lifecycle.

7. T20 defines the mode identifier only. The exact weekday, cutoff timestamp
   and closing calculation are not frozen by T20.

#### BIWEEKLY

8. `BIWEEKLY` represents a contractually configured biweekly Invoice lifecycle.

9. T20 defines the mode identifier only. The exact biweekly anchor, interval
   calculation and cutoff timestamp are not frozen by T20.

#### MONTHLY

10. `MONTHLY` represents a contractually configured monthly Invoice lifecycle.

11. T20 defines the mode identifier only. The exact day-of-month, month-end
    behavior and cutoff timestamp are not frozen by T20.

#### MANUAL

12. `MANUAL` means that automatic time-based Invoice closing MUST NOT be
    inferred by the worker.

13. A MANUAL accumulated Invoice remains subject to the eligibility rules
    frozen in M7-A3-T19.

14. The exact authorized command/API used to close a MANUAL Invoice is outside
    T20.

### Historical integrity

15. Lifecycle mode configuration MUST be historically associated with the
    applicable professional Billing contract.

16. A future lifecycle mode change MUST NOT rewrite previously materialized
    Billing.

17. The applicable historical contract remains resolved according to
    M7-A3-T17.

18. The worker MUST NOT use the latest/current lifecycle mode merely because it
    is current at processing time.

### Fail-closed behavior

19. Missing lifecycle configuration for an accumulated Billing contract MUST
    NOT cause the worker to invent a mode.

20. An unsupported lifecycle mode MUST fail closed.

21. Ambiguous lifecycle configuration MUST fail closed.

### Relationship with previous contracts

22. M7-A3-T14 remains authoritative for the two Invoice materialization modes.

23. M7-A3-T15 through T17 remain authoritative for historical professional
    Billing contracts and their resolution.

24. M7-A3-T18 remains authoritative for Invoice materialization idempotency.

25. M7-A3-T19 remains authoritative for accumulated Invoice contractual
    lifecycle and eligibility.

26. T20 freezes only the V1 lifecycle mode vocabulary. It does not yet
    authorize the physical schema or accumulated Invoice materialization.

### Non-goals

T20 does not yet define:

- physical database columns for lifecycle configuration;
- lifecycle enum implementation in PostgreSQL;
- weekly weekday configuration;
- biweekly anchor configuration;
- monthly closing-day configuration;
- cutoff timestamp calculation;
- timezone application;
- automatic closing execution;
- manual closing API;
- due-date calculation;
- accumulated Invoice lookup SQL;
- Invoice materialization code;
- Payment behavior;
- worker `main.py` wiring.

## M7-A3-T21 - Accumulated Invoice Lifecycle Configuration

**Status:** HUMAN APPROVED

### Purpose

Freeze the V1 contractual configuration required to make the accumulated
Invoice lifecycle deterministic without imposing a universal commercial
calendar on the Coworking.

The Coworking defines the applicable day, week, month and closing time
according to its commercial contract with the professional.

### Commercial authority

1. Lifecycle calendar configuration is defined by the Coworking according to
   the applicable contract with the professional.

2. The BCOS MUST NOT impose a universal closing day, week, month or time.

3. The worker MUST NOT invent missing lifecycle calendar values.

4. There is no universal default closing time.

5. Different professional Billing contracts MAY have different lifecycle
   configurations within the same tenant.

6. Contract termination, renewal, replacement and amendment/addendum MAY
   establish new lifecycle configuration for future contractual validity
   without rewriting historical Billing.

### WEEKLY

7. `WEEKLY` MUST have an explicitly configured weekday.

8. `WEEKLY` MUST have an explicitly configured closing local time.

9. The weekday uses the BCOS convention:

   - `0` = Monday;
   - `1` = Tuesday;
   - `2` = Wednesday;
   - `3` = Thursday;
   - `4` = Friday;
   - `5` = Saturday;
   - `6` = Sunday.

10. The worker MUST NOT infer a weekday or closing time when either is absent.

### BIWEEKLY

11. `BIWEEKLY` represents deterministic consecutive 14-day contractual cycles.

12. `BIWEEKLY` MUST have an explicitly configured cycle anchor.

13. The anchor establishes the contractual 14-day cycle boundary.

14. `BIWEEKLY` MUST have an explicitly configured closing local time.

15. The worker MUST NOT infer an anchor or closing time.

### MONTHLY

16. `MONTHLY` MUST have an explicitly configured day of month.

17. `MONTHLY` MUST have an explicitly configured closing local time.

18. The configured day of month MUST be within `1..31`.

19. If a calendar month does not contain the configured day, the effective
    closing day for that month is the last calendar day of that month.

20. The worker MUST NOT infer a day of month or closing time.

### MANUAL

21. `MANUAL` has no automatic calendar cutoff.

22. `MANUAL` MUST NOT require weekly, biweekly or monthly calendar fields.

23. `MANUAL` MUST NOT cause the worker to infer an automatic closing timestamp.

24. Manual closing remains an explicit Coworking action whose command/API is
    outside T21.

### Timezone

25. Automatic lifecycle cutoff is interpreted using the IANA timezone of the
    Unit associated with the Usage.

26. Closing time is a local contractual wall-clock time and MUST be combined
    with the applicable calendar boundary in the Unit timezone before temporal
    comparison.

27. The worker MUST NOT treat the configured local closing time as UTC.

28. Historical Billing MUST continue to use the Unit and Usage context
    applicable to the Usage being processed.

### Historical authority

29. Lifecycle configuration belongs to the historical professional Billing
    contract context.

30. M7-A3-T17 remains authoritative for selecting the professional Billing
    contract applicable at `booking_starts_at`.

31. Processing time MUST NOT determine which lifecycle configuration applies.

32. A future lifecycle change MUST NOT retroactively change the accumulated
    Invoice cycle applied to a historical Usage.

### Fail-closed behavior

33. Missing required configuration for an automatic lifecycle mode MUST fail
    closed.

34. Configuration incompatible with the selected lifecycle mode MUST be
    rejected rather than silently ignored.

35. Unsupported or ambiguous lifecycle configuration MUST fail closed.

### Physical direction authorized for the next stage

36. The physical schema MAY extend `professional_billing_contracts` to persist
    the lifecycle mode and its mode-specific calendar configuration.

37. The physical schema MUST preserve the distinction between:

    - `PER_USAGE`, where accumulated lifecycle configuration does not apply;
    - `ACCUMULATED_OPEN_INVOICE`, where a valid T20/T21 lifecycle
      configuration is required.

38. Physical constraints SHOULD enforce mode-compatible configuration wherever
    PostgreSQL can express the invariant safely.

39. No universal database default may choose a lifecycle mode, weekday,
    day-of-month, cycle anchor or closing time for the Coworking.

### Relationship with previous contracts

40. M7-A3-T14 remains authoritative for Invoice materialization mode.

41. M7-A3-T15 through T17 remain authoritative for historical professional
    Billing contracts and their resolution.

42. M7-A3-T18 remains authoritative for Invoice materialization idempotency.

43. M7-A3-T19 remains authoritative for accumulated Invoice contractual
    lifecycle and eligibility.

44. M7-A3-T20 remains authoritative for the V1 lifecycle modes:
    `WEEKLY`, `BIWEEKLY`, `MONTHLY`, `MANUAL`.

### Non-goals

T21 does not yet define:

- exact PostgreSQL column names and types;
- PostgreSQL lifecycle enum implementation;
- the migration;
- accumulated Invoice lookup/locking SQL;
- Invoice materialization;
- automatic closing execution;
- manual closing API;
- due-date calculation;
- Payment behavior;
- administrative UI;
- RBAC;
- Audit event names;
- worker `main.py` wiring.

## M7-A3-T22 - Physical Lifecycle Schema

**Status:** HUMAN APPROVED

### Purpose

Freeze the physical V1 representation of accumulated Invoice lifecycle
configuration on the historical professional Billing contract.

This schema persists only contractual configuration. It does not yet authorize
accumulated Invoice materialization.

### Physical fields

`professional_billing_contracts` SHALL be extended with:

- `lifecycle_mode`
- `lifecycle_weekday SMALLINT NULL`
- `lifecycle_biweekly_anchor DATE NULL`
- `lifecycle_month_day SMALLINT NULL`
- `lifecycle_closing_time TIME WITHOUT TIME ZONE NULL`

### Lifecycle mode vocabulary

The PostgreSQL lifecycle mode SHALL support exactly:

- `WEEKLY`
- `BIWEEKLY`
- `MONTHLY`
- `MANUAL`

No lifecycle mode SHALL have a database default.

### PER_USAGE invariant

1. When `invoice_mode = 'PER_USAGE'`:

   - `lifecycle_mode` MUST be NULL;
   - `lifecycle_weekday` MUST be NULL;
   - `lifecycle_biweekly_anchor` MUST be NULL;
   - `lifecycle_month_day` MUST be NULL;
   - `lifecycle_closing_time` MUST be NULL.

2. Accumulated lifecycle configuration MUST NOT be stored on a `PER_USAGE`
   professional Billing contract.

### ACCUMULATED_OPEN_INVOICE invariant

3. When `invoice_mode = 'ACCUMULATED_OPEN_INVOICE'`, `lifecycle_mode` MUST be
   explicitly configured.

4. No universal lifecycle mode default is permitted.

### WEEKLY physical configuration

5. When `lifecycle_mode = 'WEEKLY'`:

   - `lifecycle_weekday` MUST NOT be NULL;
   - `lifecycle_weekday` MUST be within `0..6`;
   - `lifecycle_closing_time` MUST NOT be NULL;
   - `lifecycle_biweekly_anchor` MUST be NULL;
   - `lifecycle_month_day` MUST be NULL.

6. Weekday convention remains:

   - `0` = Monday;
   - `1` = Tuesday;
   - `2` = Wednesday;
   - `3` = Thursday;
   - `4` = Friday;
   - `5` = Saturday;
   - `6` = Sunday.

### BIWEEKLY physical configuration

7. When `lifecycle_mode = 'BIWEEKLY'`:

   - `lifecycle_biweekly_anchor` MUST NOT be NULL;
   - `lifecycle_closing_time` MUST NOT be NULL;
   - `lifecycle_weekday` MUST be NULL;
   - `lifecycle_month_day` MUST be NULL.

8. `lifecycle_biweekly_anchor` is a local calendar `DATE` that represents the
   beginning of the first contractual 14-day cycle.

9. Successive BIWEEKLY cycles advance in deterministic 14-day increments from
   the configured anchor.

10. The configured local closing time applies to the applicable contractual
    BIWEEKLY boundary.

### MONTHLY physical configuration

11. When `lifecycle_mode = 'MONTHLY'`:

   - `lifecycle_month_day` MUST NOT be NULL;
   - `lifecycle_month_day` MUST be within `1..31`;
   - `lifecycle_closing_time` MUST NOT be NULL;
   - `lifecycle_weekday` MUST be NULL;
   - `lifecycle_biweekly_anchor` MUST be NULL.

12. If a calendar month does not contain the configured day, the effective
    closing day is the final calendar day of that month, as frozen in T21.

### MANUAL physical configuration

13. When `lifecycle_mode = 'MANUAL'`:

   - `lifecycle_weekday` MUST be NULL;
   - `lifecycle_biweekly_anchor` MUST be NULL;
   - `lifecycle_month_day` MUST be NULL;
   - `lifecycle_closing_time` MUST be NULL.

14. `MANUAL` MUST NOT imply or persist an automatic calendar cutoff.

### Local closing time semantics

15. `lifecycle_closing_time` is stored as `TIME WITHOUT TIME ZONE`.

16. The stored value represents contractual local wall-clock time.

17. The worker MUST NOT interpret this value as UTC.

18. The applicable IANA timezone continues to come from the Unit associated
    with the Usage, according to T21.

### Physical constraints

19. PostgreSQL MUST reject lifecycle configuration incompatible with
    `invoice_mode`.

20. PostgreSQL MUST reject mode-specific field combinations incompatible with
    `lifecycle_mode`.

21. PostgreSQL MUST enforce the valid weekday range `0..6`.

22. PostgreSQL MUST enforce the valid month-day range `1..31`.

23. PostgreSQL MUST NOT supply implicit commercial defaults for lifecycle mode,
    weekday, anchor, month day or closing time.

24. The lifecycle configuration remains part of the historical
    `professional_billing_contracts` row and therefore follows the temporal
    history guarantees frozen in T15-T17 and T19-T21.

### Migration authorization

25. A new Alembic migration is authorized to:

    - create the lifecycle PostgreSQL enum;
    - add the five lifecycle configuration columns;
    - add the required CHECK constraints;
    - preserve existing professional Billing contract data safely.

26. The migration MUST NOT implement Invoice materialization, Invoice closing,
    Payment behavior, APIs or worker runtime wiring.

### Relationship with previous contracts

27. T14 remains authoritative for Invoice materialization mode.

28. T15-T17 remain authoritative for historical professional Billing contract
    storage and resolution.

29. T18 remains authoritative for Invoice and InvoiceItem idempotency.

30. T19 remains authoritative for accumulated Invoice contractual lifecycle.

31. T20 remains authoritative for lifecycle mode vocabulary.

32. T21 remains authoritative for configurable day/week/month/time semantics.

### Non-goals

T22 does not yet define:

- accumulated Invoice lookup SQL;
- lifecycle cutoff calculation implementation;
- automatic Invoice closing execution;
- manual closing API;
- due-date calculation;
- Invoice materialization;
- InvoiceItem materialization;
- Payment behavior;
- administrative UI;
- RBAC;
- Audit event names;
- worker `main.py` wiring.

## M7-A3-T22.1 - Usage Billing Cycle Allocation Policy

**Status:** HUMAN APPROVED

### Purpose

Freeze the contractual authority that determines how financial effects from a
Usage are allocated when that Usage reaches or crosses an accumulated Invoice
lifecycle boundary.

The Coworking defines this policy for each professional according to the
applicable commercial contract.

### Contract authority

1. `booking_starts_at` remains authoritative under M7-A3-T17 for resolving the
   historical professional Billing contract applicable to the Usage.

2. `booking_starts_at` MUST NOT be treated as a universal rule forcing every
   financial effect of the Usage into one accumulated Invoice.

3. After resolving the historical contract, the worker MUST apply the cycle
   allocation policy configured by the Coworking for that contract.

4. There is no universal allocation-policy default.

5. The worker MUST NOT invent an allocation policy when configuration is
   missing or ambiguous.

### V1 allocation policies

The V1 policies are:

- `USAGE_COMPLETION`
- `FIXED_CUTOFF_SPLIT`

### USAGE_COMPLETION

6. `USAGE_COMPLETION` represents a contractual arrangement in which the
   financial lifecycle applicable to the Usage follows its effective
   completion.

7. A Usage is not automatically divided between accumulated Invoices merely
   because its actual use extends beyond the originally scheduled end or a
   calendar closing time.

8. The authoritative actual completion remains the completed Usage checkout
   context already established by the BCOS Usage flow.

9. Overtime calculation remains based on actual use according to the previously
   approved Pricing/Overtime contracts.

### FIXED_CUTOFF_SPLIT

10. `FIXED_CUTOFF_SPLIT` represents a contractual arrangement in which the
    configured lifecycle cutoff is an effective financial allocation boundary.

11. If a Usage crosses that cutoff, financial effects before and after the
    cutoff MAY belong to different accumulated Invoice cycles.

12. Financial effects up to the contractual cutoff belong to the cycle that is
    closing.

13. Financial effects after the contractual cutoff belong to the following
    applicable cycle.

14. The split MUST use the actual temporal Usage context and the contractual
    lifecycle cutoff.

15. The worker MUST NOT move post-cutoff financial effects back into the
    previous cycle merely because the Usage began before the cutoff.

### Separation from reception closing

16. Billing-cycle allocation is distinct from Reception Hours segmentation.

17. M7-A3-T11 remains authoritative for reception-closing overtime
    segmentation and charge/forgive treatment.

18. A lifecycle cutoff MUST NOT be interpreted as a reception closing time
    unless the Coworking's configuration independently makes those instants
    equal.

### Historical integrity

19. The allocation policy belongs to the historical professional Billing
    contract configuration.

20. Future termination, renewal, new contract or amendment/addendum MUST NOT
    rewrite the allocation policy applied to historical Billing.

21. Processing time MUST NOT determine which contract or allocation policy
    applies.

### Idempotency impact

22. `FIXED_CUTOFF_SPLIT` means one Usage may legitimately produce financial
    effects associated with more than one accumulated Invoice cycle.

23. Therefore the existing physical uniqueness
    `UNIQUE (tenant_id, usage_id, item_type)` on `invoice_items` MUST NOT be
    silently assumed sufficient for split-cycle materialization.

24. Any physical idempotency change required to represent split financial
    effects MUST be separately frozen before implementation.

25. M7-A3-T18 remains authoritative until such a physical extension is
    explicitly approved; T22.1 does not silently modify the database schema.

### Fail-closed behavior

26. Missing allocation policy MUST fail closed.

27. Unsupported allocation policy MUST fail closed.

28. Ambiguous cycle allocation MUST fail closed.

29. The worker MUST NOT choose between `USAGE_COMPLETION` and
    `FIXED_CUTOFF_SPLIT` on behalf of the Coworking.

### Relationship with previous contracts

30. T14-T18 remain authoritative for Invoice modes, historical Billing
    contracts, resolution and current idempotency guarantees.

31. T19-T22 remain authoritative for accumulated Invoice lifecycle,
    lifecycle modes, configurable calendar/time and physical lifecycle schema.

32. T22.1 extends those contracts only by freezing the contractual allocation
    behavior for a Usage that reaches or crosses a lifecycle boundary.

### Non-goals

T22.1 does not yet define:

- physical allocation-policy column or PostgreSQL enum;
- split InvoiceItem physical identity;
- accumulated Invoice lookup SQL;
- exact cycle-resolution algorithm;
- automatic Invoice closing execution;
- manual closing API;
- due-date calculation;
- Payment behavior;
- administrative UI;
- RBAC;
- Audit event names;
- worker `main.py` wiring.

## M7-A3-T22.2 - Split InvoiceItem Identity & Discount Link Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the logical identity and audit relationship required when one Usage
legitimately produces financial effects in more than one accumulated Invoice
cycle under M7-A3-T22.1.

This contract preserves idempotency while allowing legitimate financial
segmentation at a contractual lifecycle cutoff.

### Temporal financial segment

1. An InvoiceItem derived from a temporal portion of a Usage MAY represent an
   explicit financial interval.

2. The logical interval fields are:

   - `billing_period_start`
   - `billing_period_end`

3. A temporal financial interval MUST satisfy:

   `billing_period_start < billing_period_end`

4. The interval represents the actual portion of Usage time to which that
   financial effect applies.

5. Temporal intervals use the canonical UTC persistence model already adopted
   by BCOS. Contractual lifecycle cutoff calculation continues to use the
   Unit IANA timezone before conversion to the persisted instant.

6. A zero-length financial segment MUST NOT be materialized.

### Fixed-cutoff split

7. Under `FIXED_CUTOFF_SPLIT`, when a financial effect crosses the contractual
   lifecycle cutoff, the worker MAY materialize separate InvoiceItems for the
   portions before and after the cutoff.

8. The pre-cutoff segment belongs to the closing/current applicable Invoice
   cycle.

9. The post-cutoff segment belongs to the following applicable Invoice cycle.

10. Segmentation MUST NOT create overlapping temporal portions for the same
    financial effect.

11. Segmentation MUST NOT create an artificial gap in a continuous financial
    effect unless another already-approved Pricing rule explicitly makes that
    gap non-billable.

### Usage-completion policy

12. Under `USAGE_COMPLETION`, crossing the nominal lifecycle cutoff MUST NOT by
    itself split the Usage financial effect into multiple Invoice cycles.

13. T22.2 does not redefine how new Usages that begin after a nominal cutoff
    are assigned while another Usage is still in progress. That behavior
    remains outside this contract until explicitly frozen if required.

### InvoiceItem idempotent identity

14. The historical physical identity:

    `UNIQUE (tenant_id, usage_id, item_type)`

    is insufficient for temporal split materialization because two legitimate
    segments of the same Usage and item type may belong to different cycles.

15. For temporal Usage-derived financial segments, idempotent identity MUST
    include:

    - `tenant_id`
    - `usage_id`
    - `item_type`
    - `billing_period_start`
    - `billing_period_end`

16. Reprocessing the same Usage, item type and exact financial interval MUST
    NOT create a duplicate InvoiceItem.

17. Two non-overlapping legitimate intervals for the same Usage and item type
    MUST be independently materializable.

18. T22.2 does not authorize silently dropping all protection previously
    provided by T18.

19. The physical migration MUST preserve an idempotency guarantee for
    non-segmented Usage-derived InvoiceItems as well as segmented ones.

### BASE_LEASE

20. `BASE_LEASE` MUST NOT be automatically prorated or split merely because a
    Usage crosses a lifecycle cutoff.

21. Any future rule that prorates or divides `BASE_LEASE` across cycles requires
    a separately approved business and technical contract.

22. T22.2 therefore introduces no implicit BASE_LEASE proration formula.

### OVERTIME

23. `OVERTIME` MAY be represented by more than one InvoiceItem for the same
    Usage when a contractual fixed-cutoff split requires distinct financial
    intervals.

24. Each OVERTIME segment MUST preserve the actual temporal interval on which
    its financial calculation is based.

25. Existing approved Pricing, overtime-minute precision, reception-closing,
    multi-hour threshold, monetary precision and rounding contracts remain
    authoritative.

### Discount relationship

26. A `DISCOUNT` that represents forgiveness or reduction of a specific
    materialized charge MUST reference the original InvoiceItem rather than
    replacing, deleting or mutating the original financial evidence.

27. The logical relationship field is:

    `related_invoice_item_id`

28. The original charge remains auditable after the DISCOUNT is created.

29. A DISCOUNT linked to a specific charge MUST NOT ambiguously apply to another
    unrelated Usage segment.

30. Physical enforcement of tenant safety and Invoice consistency for the
    relationship MUST be defined in the corresponding schema contract before
    migration implementation.

31. The amount/sign representation of DISCOUNT remains governed by the Billing
    monetary contract and MUST NOT be reinvented by T22.2.

### General Invoice discounts

32. T22.2 does not define a general commercial discount applied to an entire
    Invoice.

33. A general Invoice-level discount, if required later, is a separate Billing
    concern and MUST NOT be conflated with forgiveness of a specific
    Usage-derived charge.

### Reception-closing separation

34. T22.2 financial segmentation does not replace M7-A3-T11.

35. Reception closing determines the approved reception/overtime segmentation
    and treatment.

36. Billing lifecycle cutoff determines accumulated Invoice-cycle allocation.

37. If both boundaries affect the same Usage, each contract MUST remain
    independently traceable in the resulting financial calculation.

### Auditability

38. A materialized temporal InvoiceItem MUST be explainable from:

    - the resolved historical professional Billing contract;
    - the Usage actual temporal context;
    - the applicable Pricing snapshot/rule;
    - the applicable lifecycle cutoff;
    - the applicable allocation policy;
    - the resulting financial interval.

39. Retries MUST reproduce the same logical temporal segment identity.

40. Processing time MUST NOT become part of financial segment identity.

### Fail-closed behavior

41. Invalid temporal interval MUST fail closed.

42. Ambiguous cutoff allocation MUST fail closed.

43. Overlapping duplicate financial segmentation MUST fail closed.

44. A specific-charge DISCOUNT whose target cannot be unambiguously resolved
    MUST fail closed.

### Physical-schema impact

45. T22.2 authorizes a later physical schema contract to introduce logical
    equivalents of:

    - `invoice_items.billing_period_start`
    - `invoice_items.billing_period_end`
    - `invoice_items.related_invoice_item_id`

46. T22.2 does NOT itself modify the database.

47. Migration `0005_billing_lifecycle` MUST NOT be rewritten to include these
    fields.

48. Any approved physical implementation MUST use a later Alembic revision.

49. The existing InvoiceItem uniqueness must not be silently removed before the
    replacement segmented/non-segmented idempotency constraints are explicitly
    frozen.

### Non-goals

T22.2 does not yet define:

- the exact PostgreSQL constraints/indexes for segmented and non-segmented
  InvoiceItems;
- the final self-referencing FK shape for `related_invoice_item_id`;
- accumulated Invoice cycle lookup SQL;
- financial item calculation formulas;
- BASE_LEASE proration;
- general Invoice-level discounts;
- automatic Invoice closing;
- Payment behavior;
- due dates;
- administrative UI;
- RBAC;
- Audit event names;
- worker `main.py` wiring.

## M7-A3-T22.3 - Split InvoiceItem Physical Schema Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the physical database contract required to support split and
non-split Usage-derived InvoiceItems while preserving idempotency and
specific-charge discount auditability.

### New InvoiceItem fields

1. A later Alembic revision MUST introduce:

   - `billing_period_start TIMESTAMPTZ NULL`
   - `billing_period_end TIMESTAMPTZ NULL`
   - `related_invoice_item_id UUID NULL`

2. `billing_period_start` and `billing_period_end` form one temporal pair.

3. Both fields MUST be NULL together or non-NULL together.

4. When non-NULL:

   `billing_period_start < billing_period_end`

5. Zero-length or inverted intervals MUST be rejected by the database.

### Non-segmented Usage-derived items

6. A non-segmented Usage-derived InvoiceItem has:

   - `usage_id IS NOT NULL`
   - `billing_period_start IS NULL`
   - `billing_period_end IS NULL`

7. Non-segmented idempotency MUST preserve the logical guarantee:

   `UNIQUE (tenant_id, usage_id, item_type)`

   for rows matching the non-segmented predicate.

8. A retry MUST NOT create a duplicate non-segmented financial effect.

### Segmented Usage-derived items

9. A segmented Usage-derived InvoiceItem has:

   - `usage_id IS NOT NULL`
   - `billing_period_start IS NOT NULL`
   - `billing_period_end IS NOT NULL`

10. Segmented idempotency MUST use the logical identity:

    - `tenant_id`
    - `usage_id`
    - `item_type`
    - `billing_period_start`
    - `billing_period_end`

11. The database MUST permit distinct legitimate temporal segments for the
    same Usage and item type.

12. The database MUST reject a duplicate of the same temporal segment.

13. The segmented identity MUST be implemented using a partial unique index or
    equivalent PostgreSQL mechanism whose NULL semantics do not weaken the
    idempotency guarantee.

### Existing InvoiceItem uniqueness

14. The existing physical uniqueness on:

    `(tenant_id, usage_id, item_type)`

    MUST NOT simply be dropped without replacement.

15. Its replacement MUST preserve protection for non-segmented items and add
    protection for segmented items atomically within the migration.

### Specific-charge DISCOUNT relationship

16. `related_invoice_item_id` represents a DISCOUNT associated with one
    specific original InvoiceItem.

17. The relationship MUST be tenant-safe.

18. The relationship MUST be Invoice-safe.

19. A specific-charge DISCOUNT MUST NOT reference an InvoiceItem belonging to
    another tenant.

20. A specific-charge DISCOUNT MUST NOT reference an InvoiceItem belonging to
    another Invoice.

21. The physical relationship MUST therefore use the logical composite
    reference:

    `(tenant_id, invoice_id, related_invoice_item_id)`

    to:

    `(tenant_id, invoice_id, id)`

22. The referenced InvoiceItem side MUST expose the required candidate key or
    uniqueness necessary for PostgreSQL to enforce that composite foreign key.

### Allowed relationship owner

23. When `related_invoice_item_id IS NOT NULL`, the referencing InvoiceItem
    MUST have:

    `item_type = DISCOUNT`

24. `BASE_LEASE`, `OVERTIME` and `ADJUSTMENT` MUST NOT carry a
    `related_invoice_item_id`.

25. A DISCOUNT MAY have `related_invoice_item_id IS NULL` because general
    Invoice-level discounts remain a separate future Billing concern.

### One specific DISCOUNT per original item in V1

26. V1 permits at most one specific-charge DISCOUNT for one original
    InvoiceItem.

27. The database MUST enforce the logical uniqueness:

    `(tenant_id, related_invoice_item_id)`

    where `related_invoice_item_id IS NOT NULL`.

28. A partial forgiveness is represented by the amount of that single
    specific-charge DISCOUNT.

29. Multiple rows MUST NOT be created merely to represent repeated partial
    adjustments against the same original charge in V1.

30. A future requirement for multiple specific discounts against one original
    item requires a new approved contract and migration.

### Original financial evidence

31. Creating a specific-charge DISCOUNT MUST NOT delete the original charge.

32. Creating a specific-charge DISCOUNT MUST NOT rewrite the original charge
    into a discounted value.

33. The original item and its related DISCOUNT remain separately auditable.

### BASE_LEASE

34. T22.3 does not authorize automatic BASE_LEASE segmentation.

35. BASE_LEASE remains non-segmented unless a future approved business and
    technical contract explicitly introduces proration.

### OVERTIME

36. OVERTIME MAY use temporal segmentation when required by
    `FIXED_CUTOFF_SPLIT`.

37. Distinct OVERTIME intervals from the same Usage MAY belong to different
    accumulated Invoices when the approved lifecycle allocation requires it.

38. Reprocessing the same OVERTIME interval MUST remain idempotent.

### Migration boundary

39. `0005_billing_lifecycle` MUST remain unchanged.

40. These physical changes MUST be introduced only by a later Alembic
    revision.

41. The later migration MUST preserve tenant-safe foreign keys and existing
    Billing referential integrity.

42. Migration downgrade behavior MUST be explicitly defined.

43. No database migration is executed by approval of T22.3 itself.

### Fail-closed behavior

44. Invalid interval pairs MUST fail closed.

45. Duplicate temporal segment identity MUST fail closed.

46. Cross-tenant related InvoiceItem references MUST fail closed.

47. Cross-Invoice related InvoiceItem references MUST fail closed.

48. A non-DISCOUNT item carrying `related_invoice_item_id` MUST fail closed.

49. A second specific-charge DISCOUNT targeting the same original InvoiceItem
    MUST fail closed in V1.

### Relationship with previous contracts

50. T18 remains authoritative for Invoice materialization idempotency.

51. T22.1 remains authoritative for Usage billing-cycle allocation policy.

52. T22.2 remains authoritative for temporal financial-segment identity and
    specific-charge discount linkage.

53. T22.3 freezes only their physical InvoiceItem schema representation.

### Non-goals

T22.3 does not define:

- accumulated Invoice cycle lookup SQL;
- cycle-resolution algorithm;
- OVERTIME financial calculation formulas;
- BASE_LEASE proration;
- general Invoice-level discount behavior;
- automatic Invoice closing;
- Payment behavior;
- due dates;
- administrative UI;
- RBAC;
- Audit event names;
- worker `main.py` wiring.

## M7-A3-T22.4 - Billing Cycle Allocation Policy Physical Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the physical representation of the Coworking-defined accumulated
Invoice cycle allocation policy established by M7-A3-T22.1.

### Physical field

1. `professional_billing_contracts` MUST expose:

   `cycle_allocation_policy`

2. The field belongs to the historical professional Billing contract.

3. Its PostgreSQL type MUST be a dedicated enum:

   `billing_cycle_allocation_policy`

4. V1 enum values are exactly:

   - `USAGE_COMPLETION`
   - `FIXED_CUTOFF_SPLIT`

5. There is no universal database default.

### Materialization-mode relationship

6. For `PER_USAGE`:

   `cycle_allocation_policy IS NULL`

7. For `ACCUMULATED_OPEN_INVOICE`:

   `cycle_allocation_policy IS NOT NULL`

8. An accumulated contract without an allocation policy MUST fail closed.

9. A PER_USAGE contract MUST NOT carry an accumulated cycle allocation policy.

### Contract authority

10. The Coworking chooses the allocation policy according to the commercial
    contract with the professional.

11. The worker MUST NOT choose or infer the policy.

12. `USAGE_COMPLETION` and `FIXED_CUTOFF_SPLIT` retain exactly the semantics
    frozen by M7-A3-T22.1.

### Historical integrity

13. `cycle_allocation_policy` is versioned together with the historical
    professional Billing contract.

14. A future change in allocation policy MUST NOT rewrite a historical contract
    version already applicable to prior Billing.

15. Contract resolution remains governed by M7-A3-T17.

16. `booking_starts_at` resolves which historical contract applies; it does not
    replace the allocation policy when resolving financial effects across
    accumulated Invoice cycles.

### Lifecycle relationship

17. T20-T22 remain authoritative for accumulated Invoice lifecycle mode,
    calendar configuration, closing time and physical lifecycle fields.

18. `cycle_allocation_policy` is orthogonal to `lifecycle_mode`.

19. Lifecycle configuration determines the contractual cycle boundary.

20. Allocation policy determines how a Usage that reaches or crosses that
    boundary is allocated.

21. The two concepts MUST NOT be collapsed into one enum or one implicit rule.

### Migration boundary

22. `0005_billing_lifecycle` MUST remain unchanged.

23. `cycle_allocation_policy` MUST be introduced by a later Alembic revision.

24. The later migration MUST add the enum, field and mode-consistency
    constraint without silently weakening the lifecycle constraints already
    frozen by T22.

25. No database migration is executed by approval of T22.4 itself.

### Fail-closed behavior

26. Missing allocation policy for `ACCUMULATED_OPEN_INVOICE` MUST fail closed.

27. Unsupported allocation policy MUST fail closed.

28. Allocation policy present on `PER_USAGE` MUST fail closed.

29. Processing time MUST NOT determine or replace the historical allocation
    policy.

### Relationship with previous contracts

30. T14 remains authoritative for Invoice materialization mode.

31. T15-T17 remain authoritative for professional Billing contract history and
    resolution.

32. T20-T22 remain authoritative for accumulated lifecycle configuration.

33. T22.1 remains authoritative for allocation-policy semantics.

34. T22.2-T22.3 remain authoritative for split InvoiceItem identity,
    idempotency and specific-charge DISCOUNT linkage.

35. T22.4 freezes only the physical contract field that records which
    allocation policy the Coworking selected.

### Non-goals

T22.4 does not define:

- accumulated Invoice cycle-resolution algorithm;
- split financial calculations;
- InvoiceItem migration details already governed by T22.3;
- automatic Invoice closing;
- Payment behavior;
- due dates;
- administrative UI;
- RBAC;
- Audit event names;
- worker `main.py` wiring.

## M7-A3-T22.5 - Migration Boundary Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the migration boundary that will physically implement the contracts
approved in T22.3 and T22.4 without rewriting migration `0005_billing_lifecycle`
and without inventing historical commercial policy.

### Alembic boundary

1. `0005_billing_lifecycle` remains immutable.

2. The physical implementation of T22.3 and T22.4 MUST be introduced by a
   later Alembic revision.

3. The intended next physical revision is conceptually `0006`, subject to the
   repository's actual Alembic head and revision naming rules at implementation
   time.

4. The later revision MUST depend on the then-current canonical Alembic head.

### Professional Billing contract changes

5. The later migration MUST introduce the dedicated PostgreSQL enum:

   `billing_cycle_allocation_policy`

6. V1 enum values are exactly:

   - `USAGE_COMPLETION`
   - `FIXED_CUTOFF_SPLIT`

7. The later migration MUST add:

   `professional_billing_contracts.cycle_allocation_policy`

8. The column MUST be nullable at the physical migration boundary to preserve
   pre-existing historical rows whose Coworking-defined policy is not known.

9. There MUST be no universal database default.

10. The migration MUST NOT backfill an allocation policy by inference.

11. The migration MUST NOT choose `USAGE_COMPLETION` or
    `FIXED_CUTOFF_SPLIT` on behalf of the Coworking.

### Historical compatibility

12. Existing historical `ACCUMULATED_OPEN_INVOICE` contracts MAY predate the
    allocation-policy field.

13. The mode-consistency rule introduced by T22.4 MUST therefore be installed
    using PostgreSQL historical-compatibility semantics equivalent to
    `CHECK ... NOT VALID`.

14. Existing rows are not automatically rewritten or treated as if the
    Coworking had selected a policy.

15. New or updated rows remain subject to the database CHECK even while the
    constraint is NOT VALID.

16. The worker MUST continue to fail closed when an applicable accumulated
    historical contract does not provide an unambiguous allocation policy.

17. Later explicit Coworking parametrization may make such historical data
    complete according to a separately authorized operational flow.

### Materialization-mode consistency

18. The physical consistency rule MUST preserve:

    - `PER_USAGE` -> `cycle_allocation_policy IS NULL`
    - `ACCUMULATED_OPEN_INVOICE` -> `cycle_allocation_policy IS NOT NULL`

19. The rule MUST NOT introduce a fallback or implicit policy.

### InvoiceItem fields

20. The later migration MUST add:

    - `billing_period_start TIMESTAMPTZ NULL`
    - `billing_period_end TIMESTAMPTZ NULL`
    - `related_invoice_item_id UUID NULL`

21. The migration MUST add a temporal-pair CHECK requiring either:

    - both billing-period fields NULL; or
    - both non-NULL with `billing_period_start < billing_period_end`.

### InvoiceItem idempotency replacement

22. The existing uniqueness protecting:

    `(tenant_id, usage_id, item_type)`

    MUST NOT be removed until its replacement protections are created within
    the same migration.

23. Non-segmented Usage-derived items MUST preserve partial uniqueness
    equivalent to:

    `UNIQUE (tenant_id, usage_id, item_type)`

    where:

    - `usage_id IS NOT NULL`
    - `billing_period_start IS NULL`
    - `billing_period_end IS NULL`

24. Segmented Usage-derived items MUST add partial uniqueness equivalent to:

    `UNIQUE (
        tenant_id,
        usage_id,
        item_type,
        billing_period_start,
        billing_period_end
    )`

    where:

    - `usage_id IS NOT NULL`
    - `billing_period_start IS NOT NULL`
    - `billing_period_end IS NOT NULL`

25. PostgreSQL NULL semantics MUST NOT create an idempotency gap.

### Related InvoiceItem relationship

26. `related_invoice_item_id` MUST support a tenant-safe and Invoice-safe
    relationship.

27. The referenced side MUST expose the candidate key required for the logical
    composite foreign key:

    `(tenant_id, invoice_id, related_invoice_item_id)`

    referencing:

    `(tenant_id, invoice_id, id)`

28. Cross-tenant relationships MUST be rejected.

29. Cross-Invoice relationships MUST be rejected.

30. A row MUST NOT reference itself.

31. The database MUST enforce:

    `related_invoice_item_id IS NULL OR related_invoice_item_id <> id`

32. When `related_invoice_item_id IS NOT NULL`, the referencing row MUST be a
    `DISCOUNT`.

33. Non-DISCOUNT items MUST NOT carry a related item reference.

34. V1 MUST enforce at most one specific-charge DISCOUNT for one original item
    using partial uniqueness equivalent to:

    `UNIQUE (tenant_id, related_invoice_item_id)`

    where `related_invoice_item_id IS NOT NULL`.

### Migration ordering and safety

35. Creation order MUST avoid temporarily removing idempotency or referential
    integrity.

36. Required candidate uniqueness MUST exist before creation of the composite
    foreign key that depends on it.

37. Replacement partial unique indexes MUST exist before the legacy
    `(tenant_id, usage_id, item_type)` uniqueness is removed.

38. The migration MUST be transactional according to the repository's existing
    Alembic/PostgreSQL conventions.

39. The migration MUST fail rather than silently coerce incompatible data.

### Downgrade

40. Downgrade behavior MUST be explicitly implemented.

41. The downgrade MUST remove dependent foreign keys and constraints before
    dropping supporting indexes, columns or enums.

42. Downgrade MUST NOT fabricate merged InvoiceItem data if segmented rows
    already exist.

43. If downgrade cannot safely restore the previous uniqueness because real
    split rows exist, the downgrade MUST fail closed rather than destroy or
    silently collapse financial evidence.

### Neon application boundary

44. Approval of T22.5 does not apply any migration to Neon.

45. Migration `0005_billing_lifecycle` remains pending application to Neon
    until the BCOS database connection is available.

46. A future `0006` MUST NOT be applied ahead of its dependency chain.

47. Database application and verification remain separate explicit gates.

### Relationship with previous contracts

48. T22.1 remains authoritative for allocation-policy semantics.

49. T22.2 remains authoritative for temporal financial-segment identity and
    discount linkage.

50. T22.3 remains authoritative for the InvoiceItem physical-schema contract.

51. T22.4 remains authoritative for the physical allocation-policy field.

52. T22.5 freezes only the safe migration boundary and historical compatibility
    strategy.

### Non-goals

T22.5 does not yet:

- create the Alembic revision;
- modify migration `0005`;
- apply database changes;
- backfill historical Coworking policy;
- implement cycle-resolution algorithms;
- implement Pricing/Billing materialization;
- wire worker `main.py`;
- define administrative UI or APIs for contract parametrization.


## M7-A3-T23 - Invoice Materialization Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze how the worker materializes the financial result of `USAGE_COMPLETED`
into `Invoice` and `InvoiceItem` while preserving the professional Billing
contract, historical integrity, lifecycle rules, allocation policy,
idempotency and transactional guarantees already approved in M7-A3.

### Contract source

1. Invoice materialization MUST use the
   `ProfessionalBillingContract` already resolved inside
   `UsagePricingContext`.

2. The materializer MUST NOT perform a second independent professional Billing
   contract resolution.

3. `booking_starts_at` remains authoritative only for selecting which historical
   professional Billing contract version applies, according to M7-A3-T17.

4. `booking_starts_at` MUST NOT be treated as a universal rule that forces all
   financial effects from one Usage into one accumulated Invoice cycle.

### Required professional Billing contract context

5. The worker contract representation MUST expose the historical fields required
   by the already-approved Billing lifecycle contracts, including:

   - `lifecycle_mode`
   - `lifecycle_weekday`
   - `lifecycle_biweekly_anchor`
   - `lifecycle_month_day`
   - `lifecycle_closing_time`
   - `cycle_allocation_policy`

6. The worker MUST NOT infer any missing lifecycle or allocation-policy value.

7. Historical professional Billing contract resolution remains tenant-safe and
   professional-safe.

### PER_USAGE materialization

8. For `PER_USAGE`, the Usage-specific Invoice identity is:

   `invoices.source_usage_id = usage_id`

9. The Invoice MUST belong to the same tenant and professional as the Usage and
   resolved historical professional Billing contract.

10. Reprocessing the same `USAGE_COMPLETED` MUST NOT create a second PER_USAGE
    Invoice for the same Usage.

11. `cycle_allocation_policy` MUST be NULL for `PER_USAGE`.

12. Accumulated Invoice lifecycle configuration does not apply to PER_USAGE
    materialization.

### ACCUMULATED_OPEN_INVOICE materialization

13. For `ACCUMULATED_OPEN_INVOICE`:

    `invoices.source_usage_id IS NULL`

14. The worker MUST NOT select an arbitrary OPEN Invoice merely because it
    belongs to the same professional.

15. An eligible accumulated Invoice MUST correspond to the same tenant,
    professional, applicable historical contract and correct contractual Billing
    cycle.

16. Lifecycle configuration and `cycle_allocation_policy` are mandatory for an
    accumulated contract.

17. Missing or ambiguous accumulated lifecycle or allocation context MUST fail
    closed.

18. OPEN status alone is insufficient to establish accumulated Invoice
    eligibility.

### Billing-cycle allocation policy

19. `USAGE_COMPLETION` retains exactly the semantics frozen by M7-A3-T22.1.

20. Under `USAGE_COMPLETION`, a nominal lifecycle cutoff MUST NOT by itself split
    the Usage financial effects across multiple accumulated Invoice cycles.

21. `FIXED_CUTOFF_SPLIT` retains exactly the semantics frozen by M7-A3-T22.1.

22. Under `FIXED_CUTOFF_SPLIT`, a Usage crossing the contractual lifecycle
    cutoff MAY produce financial effects in more than one accumulated Invoice
    cycle.

23. The materializer consumes the approved financial segmentation resulting from
    Pricing/Billing processing; it MUST NOT invent a new allocation rule.

24. Reception closing and accumulated Billing lifecycle cutoff remain separate
    contractual concepts.

### InvoiceItem materialization

25. Non-segmented Usage-derived InvoiceItems retain the idempotent identity:

    `tenant_id + usage_id + item_type`

26. Segmented Usage-derived InvoiceItems retain the idempotent identity:

    `tenant_id + usage_id + item_type + billing_period_start + billing_period_end`

27. A retry MUST reuse or recognize the existing logical financial effect rather
    than create a duplicate InvoiceItem.

28. A materialization conflict in which the existing row does not represent the
    same expected financial evidence MUST fail closed.

29. `BASE_LEASE` MUST NOT be automatically split or prorated merely because a
    Usage crosses a lifecycle cutoff.

30. `OVERTIME` MAY be temporally segmented when required by
    `FIXED_CUTOFF_SPLIT`.

31. Temporal InvoiceItem segmentation remains governed by M7-A3-T22.2 and
    M7-A3-T22.3.

### Specific-charge DISCOUNT

32. A DISCOUNT representing forgiveness or reduction of a specific materialized
    charge MUST preserve the original InvoiceItem.

33. Such a DISCOUNT MUST use `related_invoice_item_id`.

34. The related InvoiceItem MUST belong to the same tenant and same Invoice.

35. V1 permits at most one specific-charge DISCOUNT per original InvoiceItem.

36. A retry MUST NOT create a second specific-charge DISCOUNT for the same
    original InvoiceItem.

37. General Invoice-level discount behavior remains outside this contract.

### Transactional atomicity

38. Invoice selection or creation, InvoiceItem materialization and the successful
    transition of the Outbox event to `PROCESSED` MUST occur inside the same
    financial transaction established by M7-A3-T5.

39. A failure during materialization MUST roll back the complete financial
    transaction.

40. The Outbox event MUST NOT be marked `PROCESSED` if Invoice or InvoiceItem
    materialization fails.

41. Retry behavior continues to follow the approved Outbox retry and recovery
    contracts.

### Fail-closed behavior

42. Professional Billing contract absence MUST fail closed.

43. Ambiguous professional Billing contract resolution MUST fail closed.

44. Unsupported `invoice_mode` MUST fail closed.

45. Missing required accumulated lifecycle configuration MUST fail closed.

46. Missing required accumulated `cycle_allocation_policy` MUST fail closed.

47. Unsupported allocation policy MUST fail closed.

48. Indeterminate accumulated Billing cycle MUST fail closed.

49. Multiple accumulated Invoices matching a context that requires exactly one
    eligible Invoice MUST fail closed.

50. An idempotency conflict incompatible with the expected financial result MUST
    fail closed.

51. Cross-tenant or cross-professional Invoice materialization MUST fail closed.

### Accumulated Invoice physical identity boundary

52. T23 does NOT yet define the physical accumulated Invoice cycle identity.

53. The worker MUST NOT invent a lookup rule equivalent to "first OPEN Invoice"
    or "latest OPEN Invoice".

54. A separate approved contract MUST define how an accumulated Invoice is
    uniquely identified by its professional Billing contract and contractual
    lifecycle cycle before ACCUMULATED_OPEN_INVOICE materialization is
    implemented.

55. A fixed physical identity such as contract plus cycle boundaries MUST NOT be
    assumed until that separate contract is approved.

### Relationship with previous contracts

56. T14 remains authoritative for Invoice materialization mode.

57. T15-T17 remain authoritative for historical professional Billing contract
    persistence and resolution.

58. T18 remains authoritative for PER_USAGE Invoice idempotency.

59. T19-T22 remain authoritative for accumulated Invoice lifecycle and
    configuration.

60. T22.1 remains authoritative for Usage Billing cycle allocation policy.

61. T22.2-T22.3 remain authoritative for segmented InvoiceItem identity and
    specific-charge DISCOUNT linkage.

62. T22.4 remains authoritative for allocation-policy physical representation.

63. T22.5 remains authoritative for the migration boundary implementing the
    required physical support.

### Non-goals

T23 does not yet define:

- accumulated Invoice cycle physical identity;
- accumulated Invoice lookup SQL;
- exact lifecycle cutoff calculation implementation;
- automatic Invoice closing execution;
- manual closing API;
- due-date calculation;
- Payment behavior;
- general Invoice-level discount behavior;
- administrative UI;
- RBAC;
- Audit event names;
- worker `main.py` wiring.

## M7-A3-T24 - Accumulated Invoice Cycle Identity Contract

**Status:** HUMAN APPROVED

### Purpose

Freeze the logical identity used to resolve accumulated Invoices safely and
deterministically under `ACCUMULATED_OPEN_INVOICE`.

### General identity rules

1. An accumulated Invoice MUST belong to one historical professional Billing
   contract version.

2. `professional_id` alone MUST NOT identify an accumulated Invoice cycle.

3. `booking_starts_at` remains authoritative only for resolving which historical
   professional Billing contract applies.

4. `booking_starts_at` MUST NOT be used as a universal accumulated Invoice cycle
   identity.

5. The worker MUST NOT select an accumulated Invoice using arbitrary rules such
   as:

   - first OPEN Invoice;
   - latest OPEN Invoice;
   - most recently created Invoice;
   - any OPEN Invoice for the same professional.

### Automatic lifecycle modes

6. For `WEEKLY`, `BIWEEKLY` and `MONTHLY`, the logical accumulated Invoice cycle
   identity is:

   `tenant_id + professional_billing_contract_id + billing_cycle_start + billing_cycle_end`

7. `professional_billing_contract_id` identifies the exact historical contract
   version already resolved under M7-A3-T17 and M7-A3-T23.

8. `billing_cycle_start` and `billing_cycle_end` represent the effective
   contractual financial-cycle boundaries.

9. Cycle boundaries MUST be calculated using the Unit IANA timezone and then
   persisted as canonical UTC instants.

10. Automatic-cycle boundaries MUST satisfy:

    `billing_cycle_start < billing_cycle_end`

11. The same tenant, historical professional Billing contract and exact cycle
    interval MUST identify at most one accumulated Invoice.

12. Reprocessing the same financial effect MUST resolve the same accumulated
    Invoice rather than create another Invoice for the same logical cycle.

### FIXED_CUTOFF_SPLIT

13. Under `FIXED_CUTOFF_SPLIT`, one Usage MAY legitimately produce financial
    effects in two different accumulated Invoice cycles.

14. The pre-cutoff financial segment belongs to the Invoice identified by the
    closing/current cycle.

15. The post-cutoff financial segment belongs to the Invoice identified by the
    following applicable cycle.

16. The worker MUST NOT move both segments into one Invoice merely because the
    Usage began before the lifecycle cutoff.

### USAGE_COMPLETION

17. Under `USAGE_COMPLETION`, nominal lifecycle cutoff crossing alone does not
    split the Usage financial effects across multiple accumulated Invoice cycles.

18. The financial-cycle result continues to follow the approved allocation-policy
    semantics frozen in M7-A3-T22.1.

### MANUAL lifecycle mode

19. `MANUAL` has no automatic calendar cutoff.

20. The worker MUST NOT invent a `billing_cycle_end` for MANUAL using:

    - current time;
    - Invoice creation time;
    - Invoice issue time;
    - first Usage time;
    - last Usage time;
    - arbitrary calendar boundaries.

21. The system MAY create an accumulated Invoice when financial materialization
    first requires one for an applicable MANUAL contract.

22. Creation of the accumulated Invoice does NOT transfer closing authority to
    the worker.

23. Closing a MANUAL accumulated Invoice remains under explicit Coworking
    control.

24. The worker MUST NOT automatically close, rotate or replace a MANUAL
    accumulated Invoice based on elapsed time or calendar progression.

25. While exactly one accumulated Invoice remains eligible under the same tenant
    and historical professional Billing contract, new financial effects MAY be
    materialized into that Invoice.

26. After the Coworking closes that MANUAL Invoice, it MUST NOT receive new
    financial items.

27. A later Usage MAY require creation of a new accumulated Invoice for the same
    historical contract after the prior MANUAL Invoice is no longer eligible.

28. The worker MUST NOT implicitly reopen a previously closed MANUAL Invoice.

29. More than one simultaneously eligible MANUAL accumulated Invoice for the same
    tenant and historical professional Billing contract MUST fail closed.

30. MANUAL lifecycle semantics do not require the Coworking to pre-open an Invoice
    before the first financial materialization.

31. T24 does not define the API, UI, RBAC or administrative command used by the
    Coworking to close a MANUAL accumulated Invoice.

### PER_USAGE separation

32. `PER_USAGE` remains physically and logically distinct from accumulated Invoice
    identity.

33. `PER_USAGE` continues to use:

    `invoices.source_usage_id = usage_id`

34. Accumulated Invoices continue to use:

    `source_usage_id IS NULL`

35. Accumulated Invoice cycle identity MUST NOT reuse or overload
    `source_usage_id`.

### Eligibility

36. An accumulated Invoice is eligible only when it corresponds to the same:

    - tenant;
    - professional;
    - historical professional Billing contract;
    - applicable financial cycle or MANUAL lifecycle instance;
    - materializable Invoice state.

37. `OPEN` status alone is insufficient to identify or authorize an accumulated
    Invoice.

38. An Invoice belonging to another historical contract version MUST NOT receive
    financial effects merely because the professional is the same.

### Idempotency

39. Automatic-cycle materialization MUST preserve one logical accumulated Invoice
    per:

    `tenant_id + professional_billing_contract_id + billing_cycle_start + billing_cycle_end`

40. Retry MUST resolve the same logical accumulated Invoice.

41. Competing attempts MUST NOT create duplicate accumulated Invoices for the same
    logical automatic cycle.

42. MANUAL accumulated Invoice materialization MUST preserve the invariant that at
    most one eligible MANUAL Invoice exists for the same tenant and historical
    professional Billing contract at a time.

### Fail-closed behavior

43. Missing historical professional Billing contract MUST fail closed.

44. Ambiguous historical professional Billing contract resolution MUST fail closed.

45. Indeterminate automatic Billing-cycle boundaries MUST fail closed.

46. Invalid cycle interval MUST fail closed.

47. Multiple automatic Invoices matching one exact logical cycle MUST fail closed.

48. More than one eligible MANUAL Invoice for one historical contract MUST fail
    closed.

49. Unsupported lifecycle mode MUST fail closed.

50. The worker MUST NOT choose a fallback Invoice when accumulated identity cannot
    be resolved unambiguously.

### Physical-schema boundary

51. T24 freezes logical accumulated Invoice identity only.

52. T24 does NOT yet authorize a database migration.

53. A later physical-schema contract MUST define the required Invoice columns,
    foreign keys, uniqueness, historical compatibility and downgrade behavior.

54. Existing migration `0004_invoice_source_usage` remains authoritative for
    PER_USAGE Invoice identity.

55. Existing migrations `0005_billing_lifecycle` and
    `0006_invoice_item_segmentation` remain unchanged.

56. T24 approval does not apply any migration to Neon.

### Relationship with previous contracts

57. T14 remains authoritative for Invoice materialization mode.

58. T15-T17 remain authoritative for historical professional Billing contract
    storage and resolution.

59. T18 remains authoritative for PER_USAGE Invoice identity.

60. T19-T22 remain authoritative for accumulated Invoice lifecycle configuration.

61. T22.1 remains authoritative for Usage cycle allocation policy.

62. T22.2-T22.5 remain authoritative for InvoiceItem segmentation, discount
    linkage, physical allocation policy and migration boundaries.

63. T23 remains authoritative for Invoice materialization behavior and
    transactional atomicity.

64. T24 freezes only accumulated Invoice cycle identity and MANUAL lifecycle
    selection semantics.

### Non-goals

T24 does not yet define:

- physical accumulated Invoice schema;
- Alembic migration implementation;
- exact accumulated Invoice lookup SQL;
- exact lifecycle cutoff calculation code;
- automatic Invoice closing implementation;
- MANUAL closing API or UI;
- due-date calculation;
- Payment behavior;
- general Invoice-level discount behavior;
- RBAC;
- Audit event names;
- worker `main.py` wiring.
