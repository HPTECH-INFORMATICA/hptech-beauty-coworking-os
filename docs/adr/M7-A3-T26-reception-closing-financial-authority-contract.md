# M7-A3-T26 — Reception Closing Financial Authority Reconciliation

> "Quem pede um, pede bis."

**Status:** PROPOSED / AWAITING HUMAN APPROVAL

## Purpose

Resolve a contractual contradiction discovered during the BCOS Product Reconciliation Gate without silently rewriting previously approved history.

The contradiction is between:

- `M7-A2-T1 — Reception Closing Temporal Contract`, which defines `closes_at` as the maximum chargeable overtime instant and excludes time after reception closing from OVERTIME;
- M7-A3-T7/T8, which preserve M7-A2-T1 as authoritative and state that time after reception closing must not generate OVERTIME; and
- `M7-A3-T11 — Reception Closing Overtime Segmentation Contract`, which later states that after-closing overtime remains financially traceable and may be charged or forgiven.

The current worker implementation and regression suite follow M7-A2-T1/T8 financial semantics: after-closing elapsed time can remain temporal evidence, but it does not materialize a financial OVERTIME charge.

## Proposed authoritative reconciliation

If human-approved, this gate freezes the following authority for V1:

1. `Unit.reception_hours` and the Unit IANA timezone remain the temporal authority for reception closing.
2. `closes_at` is the maximum chargeable overtime instant.
3. Elapsed time strictly after `closes_at` MUST NOT materialize an OVERTIME financial effect.
4. Exactly `closes_at` belongs to the chargeable pre-close interval; only elapsed time strictly after that instant is after-closing time.
5. A reception day configured as closed MUST NOT generate OVERTIME financial effects.
6. Missing or invalid Reception Hours evidence remains a fail-closed processing error; the worker MUST NOT infer an implicit closing time.
7. The temporal classifier MAY preserve an after-closing segment for auditability, diagnostics, or future explicitly approved policy. Preserving temporal evidence does not make that segment financially chargeable.
8. The worker MUST NOT materialize a zero-valued OVERTIME item merely to represent after-closing elapsed time. Temporal evidence and financial effects remain distinct concerns.
9. M7-A3-T11 remains historical evidence of an approved but conflicting interpretation. Upon approval of T26, only T11 clauses that permit charging or financial forgiveness of after-closing overtime are superseded for V1.
10. T11's half-open temporal boundary semantics remain compatible: exactly `closes_at` is pre-close; strictly later elapsed time is after-close.
11. M7-A3-T10 whole-minute temporal precision, T12 monetary precision, and subsequent Pricing/Billing contracts remain unchanged except where they would otherwise be applied to an after-closing segment that this gate declares non-chargeable.
12. No automatic DISCOUNT is generated for after-closing elapsed time because no financial OVERTIME charge exists to forgive under this authority.

## Required regression protection

The implementation baseline must continue proving at least:

- overtime entirely before reception closing remains chargeable under the frozen pricing rule;
- overtime crossing reception closing materializes only the supported pre-close financial portion;
- checkout exactly at reception closing preserves the pre-close boundary;
- overtime starting only after reception closing produces no OVERTIME financial effect;
- a closed reception day produces no OVERTIME financial effect;
- temporal after-close evidence cannot silently become a charge through downstream Invoice materialization.

## Scope and non-goals

This reconciliation does NOT define or change:

- Pricing formulas;
- monetary rounding;
- Billing lifecycle or Invoice closing;
- Invoice due dates;
- Payment creation or settlement;
- terminal Outbox `FAILED` policy;
- RBAC administration;
- forgiveness UI/API;
- frontend behavior;
- database schema or migrations;
- T25 accumulated-invoice identity or cutoff allocation.

No migration is authorized or required by this reconciliation.

## Promotion rule

This document is deliberately **not** a locked baseline yet.

Only explicit human approval may promote M7-A3-T26 to `HUMAN HOMOLOGATED / LOCKED`. Until then, it records the discovered contradiction and the proposed resolution that matches the currently protected implementation behavior.

> "Quem pede um, pede bis."
