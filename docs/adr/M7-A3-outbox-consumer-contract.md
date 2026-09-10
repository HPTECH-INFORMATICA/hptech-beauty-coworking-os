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

