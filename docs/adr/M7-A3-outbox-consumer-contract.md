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

