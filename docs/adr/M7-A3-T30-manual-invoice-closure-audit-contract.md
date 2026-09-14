# M7-A3-T30 — MANUAL Invoice Closure Audit Contract

> "Quem pede um, pede bis."

**Status:** HUMAN HOMOLOGATED / LOCKED

## Purpose

Define the exact audit evidence required by T29 for the MANUAL accumulated Invoice closure command.

T30 is intentionally narrow. It does not reopen T29 lifecycle semantics and does not authorize any additional Billing mutation.

## Existing audit authority

The API provides `create_audit_log(...)`, which writes tenant, actor external user id, action, entity type, entity id and JSON metadata into `audit_logs` inside the caller-owned database transaction.

Existing Booking cancellation uses that mechanism transactionally with action `BOOKING_CANCELLED` and entity type `BOOKING`. T30 follows that established audit mechanism rather than adding a new audit subsystem or Outbox event.

## Locked V1 audit evidence

A successful first MANUAL Invoice closure writes exactly one audit log in the same transaction as `manual_closed_at` persistence:

- `action = "INVOICE_MANUAL_CLOSED"`;
- `entity_type = "INVOICE"`;
- `entity_id = invoice.id`;
- `tenant_id = authenticated TenantContext.tenant_id`;
- `actor_external_user_id = authenticated TenantContext.external_user_id`;
- metadata contains the persisted `manual_closed_at` as an ISO-8601 UTC value and the Invoice financial `status` observed at closure.

The audit metadata must not duplicate InvoiceItems, Payment details, pricing evidence, or personally unnecessary financial payload.

## Atomicity

The Invoice lifecycle mutation and its audit row commit atomically in the existing API transaction. If audit persistence fails, the first closure rolls back. A successful first closure without its audit evidence is forbidden.

## Idempotent retry

A repeated request against an already-closed MANUAL Invoice is a read/idempotent outcome and preserves the original `manual_closed_at`.

It does not create another `INVOICE_MANUAL_CLOSED` audit row because no new lifecycle mutation occurred.

Concurrent first-close attempts converge on one persisted closure and one closure audit row through Invoice row locking and transactional serialization.

## Failure/rejection audit boundary

Authorization failures, cross-tenant not-found outcomes, invalid Invoice identity, PAID/CANCELLED rejection, automatic-cycle rejection and PER_USAGE rejection do not create `INVOICE_MANUAL_CLOSED`, because closure did not occur.

T30 introduces no separate rejection/security audit event name.

## Outbox boundary

T30 authorizes no new Outbox event. MANUAL Invoice closure has no approved asynchronous downstream consumer requirement in the current V1 architecture. Audit evidence belongs in `audit_logs`; inventing an Outbox event would expand the contract without a proven consumer.

## Implementation and verification record

The T29/T30 implementation was squash-merged to `main` as `f4a1ba22f5393173c7e8fda8d73663ddd0544095` on 2026-09-14.

Implementation regression coverage verifies the approved audit boundary together with T29 lifecycle behavior. PR Quality Gate #91 and post-merge `main` Quality Gate #93 completed successfully.

No new audit table, Outbox event/consumer, migration, frontend, static OpenAPI, T26 or T27 change was introduced.

## Homologation record

Human approval of the T30 contract was explicitly granted on 2026-09-14. After implementation, successful verification and merge to `main`, the user explicitly approved continuation/finalization on 2026-09-14.

T30 is therefore **HUMAN HOMOLOGATED / LOCKED**. Future changes to the MANUAL Invoice closure audit contract require a new traceable gate.

> "Quem pede um, pede bis."
