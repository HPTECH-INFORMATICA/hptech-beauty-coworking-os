# M7-A3-T29 — Invoice Lifecycle Write Boundary Contract

> "Quem pede um, pede bis."

**Status:** HUMAN HOMOLOGATED / LOCKED

## Purpose

Resolve the Invoice lifecycle gap exposed by locked T25 and T28 before a Billing lifecycle write API is promoted.

## Existing authority preserved

T29 does not reopen T25, T28, PER_USAGE identity, InvoiceItem evidence, confirmed PIX Payment behavior, T26, T27, or the independently locked static OpenAPI V1 baseline.

## Approved V1 lifecycle boundary

### MANUAL accumulated Invoice closure

V1 allows explicit closure only for an accumulated MANUAL Invoice with `source_usage_id IS NULL`, a historical `professional_billing_contract_id`, NULL automatic cycle boundaries, and an active lifecycle represented by `manual_closed_at IS NULL`.

Closure persists a timezone-aware UTC `manual_closed_at`. It must not rewrite InvoiceItems or totals. After closure, the worker must not append financial effects to that Invoice; later completed Usage may resolve/create the next active MANUAL Invoice under locked T25 identity rules.

### Authorization

Closure requires existing `Permission.OPERATIONS`: Owner, Admin and Reception are allowed; Professional fails closed. No new permission is introduced.

### Financial state

Only `OPEN` and `PARTIALLY_PAID` MANUAL Invoices are eligible for first closure. `PAID` and `CANCELLED` fail closed. No `CLOSED` Invoice status is introduced: `manual_closed_at` is the materialization lifecycle boundary while `status` remains financial/payment state.

### Automatic cycles and PER_USAGE

WEEKLY, BIWEEKLY and MONTHLY accumulated Invoices receive no explicit close/issue mutation in V1. PER_USAGE Invoices receive no close operation.

### Concurrency and idempotency

The command is tenant-scoped and locks the target Invoice before mutation. First valid close atomically persists `manual_closed_at`. Repeated close of the same already-closed MANUAL Invoice is idempotent and must preserve the original close instant. Concurrent attempts must converge on one closure and the lifecycle endpoint itself must not create a successor Invoice.

### Payment interaction

Closure does not mark paid, create Payment, cancel, forgive balance or bypass Payments. A closed MANUAL Invoice with remaining balance may continue to receive a valid existing Payment when its financial status permits it.

### Post-close mutation boundary

T29 does not authorize reopening, cancellation, manual InvoiceItem creation, adjustments, discounts, due dates, issuance/overdue semantics, Pricing changes, Payment changes, Outbox retry changes or frontend work.

## API implementation boundary

One tenant-scoped MANUAL Invoice closure command is authorized and implemented under the separately approved and homologated T30 audit boundary. Generic Invoice CRUD remains forbidden.

## Audit requirement

The repository provides the existing transactional `audit_logs` writer. T30 defines the exact closure audit action/entity/metadata contract used by the implementation. No new Outbox event is introduced for this lifecycle command.

## Implementation and verification record

The T29/T30 implementation was squash-merged to `main` as `f4a1ba22f5393173c7e8fda8d73663ddd0544095` on 2026-09-14.

The implementation includes tenant-scoped MANUAL Invoice closure, row locking, `OPERATIONS` authorization, OPEN/PARTIALLY_PAID eligibility, PAID/CANCELLED rejection, automatic/PER_USAGE rejection, immutable idempotent `manual_closed_at`, transactional T30 audit evidence and HTTP/service regression coverage.

PR implementation Quality Gate #91 completed successfully. Post-merge `main` Quality Gate #93 also completed successfully against commit `f4a1ba22f5393173c7e8fda8d73663ddd0544095`.

No migration, frontend change, T26/T27 change or static OpenAPI change was introduced by T29/T30.

## Homologation record

Human implementation authorization was granted on 2026-09-14. After implementation, green PR verification, squash merge to `main` and green post-merge verification, the user explicitly approved continuation/finalization on 2026-09-14.

T29 is therefore **HUMAN HOMOLOGATED / LOCKED**. Future lifecycle expansion requires a new traceable gate and must not silently reopen T29.

> "Quem pede um, pede bis."
