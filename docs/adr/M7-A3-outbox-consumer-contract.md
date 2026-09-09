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


