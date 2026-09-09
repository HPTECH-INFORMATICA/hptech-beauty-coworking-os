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
