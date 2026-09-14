# M7-A3-T29 — Invoice Lifecycle Write Boundary Contract

> "Quem pede um, pede bis."

**Status:** HUMAN APPROVED / IMPLEMENTATION AUTHORIZED

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

One tenant-scoped MANUAL Invoice closure command is authorized after the audit-event boundary below is separately approved. Generic Invoice CRUD is forbidden.

## Audit requirement — implementation blocker identified

Repository audit after human approval confirmed an existing generic transactional `audit_logs` writer and an established API precedent where `BOOKING_CANCELLED` is persisted in the same caller-owned transaction as its operational mutation.

No previously approved audit action/entity/metadata contract for MANUAL Invoice closure was found. T29 therefore does **not** authorize inventing an Invoice closure event name during implementation. T30 is the separate traceable decision gate for that audit boundary.

Production implementation of the T29 lifecycle command is authorized in principle but remains blocked from promotion until T30 is human-approved. This is the exact stop condition required by the original T29 audit requirement.

## Required implementation tests

After the audit boundary is approved, tests must cover tenant isolation; OPERATIONS/Professional authorization; MANUAL identity; OPEN and PARTIALLY_PAID closure; PAID/CANCELLED rejection; already-closed idempotency; immutable close instant; automatic/PER_USAGE rejection; no InvoiceItem/total/Payment side effect; worker non-rematerialization into closed MANUAL Invoice; successor identity under T25/database uniqueness; concurrency; and approved audit behavior.

## Approval record

Human approval explicitly granted on 2026-09-14. This approval authorizes the V1 business/lifecycle choices above; it is not final implementation homologation.

Final state at this gate: **HUMAN APPROVED / IMPLEMENTATION AUTHORIZED**.

> "Quem pede um, pede bis."
