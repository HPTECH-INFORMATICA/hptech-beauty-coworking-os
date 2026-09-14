# M7-A3-T27 — Terminal Outbox Failure Policy Contract

> "Quem pede um, pede bis."

**Status:** PROPOSED / AWAITING HUMAN APPROVAL

## Purpose

Close the explicit M7-A3 gap that has remained intentionally undefined since the retry, consumer lifecycle, and runtime contracts: maximum processing attempts, the transition to terminal `FAILED`, and the recovery boundary for terminal events.

This gate does not change Pricing, Billing, Payment, or Reception business semantics. It defines only the terminal lifecycle of an Outbox event after repeated recoverable processing failures.

## Existing locked foundations preserved

T27 preserves without modification:

- T1 eligibility and atomic `PENDING -> PROCESSING` claim;
- the existing increment of `attempts` at claim time;
- T2 bounded exponential retry scheduling for recoverable failures;
- T3 sanitized `last_error` persistence;
- T4 abandoned `PROCESSING` recovery without incrementing `attempts`;
- T5 atomic processing transaction and rollback before failure-state persistence;
- T6 runtime loop and recovery cadence.

The database baseline already reserves `FAILED` in the `outbox_status` enum, so this proposal requires no schema change merely to represent the terminal state.

## Proposed V1 policy

1. `attempts` continues to mean the number of claims that successfully transitioned the event from `PENDING` to `PROCESSING`.
2. The V1 maximum is **5 processing attempts** per Outbox event.
3. A recoverable processing failure from an event whose current `attempts < 5` follows the existing T2 retry path:
   - processing transaction rolls back;
   - event transitions from `PROCESSING` back to `PENDING`;
   - `processing_started_at = NULL`;
   - sanitized `last_error` is persisted;
   - `available_at` is scheduled using the existing bounded exponential backoff.
4. A processing failure from an event whose current `attempts >= 5` is terminal for V1 and transitions from `PROCESSING` to `FAILED` in the separate post-rollback failure transaction.
5. The terminal transition MUST set:
   - `status = FAILED`;
   - `processing_started_at = NULL`;
   - `processed_at = NULL`;
   - sanitized `last_error` using the existing T3 sanitizer.
6. The terminal transition MUST NOT increment or decrement `attempts`. The fifth attempt was already counted during claim.
7. `FAILED` events are not eligible for `claim_next_event()` and are not eligible for T4 abandoned-PROCESSING recovery.
8. `available_at` has no scheduling authority while status is `FAILED`; the terminal transition does not use it to imply an automatic retry.
9. The worker MUST NOT automatically reopen a `FAILED` event.
10. A future manual/operator retry mechanism, if required, must be defined by a separate contract with authorization, audit, and idempotency semantics. T27 does not authorize one.
11. A failure to persist the terminal `FAILED` transition is an infrastructure failure. It MUST propagate rather than being reported as a successful terminal outcome.
12. An unknown event type follows the same attempt accounting and terminal policy; it must never be silently marked `PROCESSED`.

## Consumer result boundary

If T27 is approved and implemented, the consumer may expose a distinct terminal iteration result such as `FAILED` only after the terminal state has been committed successfully.

The runtime loop may continue after a successfully persisted terminal event because the individual event is isolated from subsequent eligible events. This does not convert infrastructure failures into terminal event outcomes.

## Required implementation evidence

Before technical completion, regression coverage must prove at least:

- attempts 1 through 4 schedule retry under the existing backoff;
- failure on attempt 5 transitions to `FAILED` rather than `PENDING`;
- terminal transition preserves attempts at 5;
- terminal error text uses the existing sanitizer and length limit;
- `FAILED` is excluded from claim eligibility;
- `FAILED` is excluded from abandoned-processing recovery;
- financial/materialization writes from the failed fifth processing transaction are rolled back before `FAILED` is committed;
- a failure while persisting `FAILED` propagates as infrastructure failure;
- unknown event types cannot bypass the terminal policy.

## No migration gate

No database migration is authorized by this proposal. `FAILED` already exists in the physical `outbox_status` enum.

If implementation discovers that a new persisted field is actually required, implementation must stop at that boundary and open a separate migration contract rather than silently changing the schema.

## Non-goals

T27 does not define:

- manual retry/reopen API;
- operator UI for failed events;
- notifications or alerts for failed events;
- dead-letter tables or queues;
- worker ownership, heartbeat, or lease;
- dynamic maximum-attempt configuration;
- Pricing or Billing formulas;
- Invoice closing or due dates;
- Payment behavior;
- frontend navigation;
- RBAC for a future operator recovery action.

## Promotion rule

This is a proposed business/operational contract. Implementation is not authorized by this document alone.

Only explicit human approval may promote T27 to an approved implementation baseline.

> "Quem pede um, pede bis."
