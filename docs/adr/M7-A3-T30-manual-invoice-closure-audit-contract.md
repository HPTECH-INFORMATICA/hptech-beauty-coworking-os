# M7-A3-T30 — MANUAL Invoice Closure Audit Contract

> "Quem pede um, pede bis."

**Status:** HUMAN APPROVED / IMPLEMENTATION AUTHORIZED

## Purpose

Define the exact audit evidence required by approved T29 before the MANUAL accumulated Invoice closure command may be promoted to production.

T30 is intentionally narrow. It does not reopen T29 lifecycle semantics and does not authorize any additional Billing mutation.

## Existing audit authority

The API already provides `create_audit_log(...)`, which writes tenant, actor external user id, action, entity type, entity id and JSON metadata into `audit_logs` inside the caller-owned database transaction.

Existing Booking cancellation uses that mechanism transactionally with action `BOOKING_CANCELLED` and entity type `BOOKING`. T30 follows that established audit mechanism rather than adding a new audit subsystem or Outbox event.

## Approved V1 audit evidence

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

## Required implementation tests

Implementation tests must prove:

- first valid close writes one `INVOICE_MANUAL_CLOSED` / `INVOICE` audit row;
- tenant and actor come from authenticated TenantContext;
- metadata reflects the persisted close instant and financial status;
- closure and audit are atomic;
- audit failure rolls back closure;
- idempotent retry creates no duplicate closure audit;
- rejected/unauthorized/cross-tenant requests create no closure audit;
- no Outbox event is created by this command.

## Non-goals

T30 does not authorize new audit tables, new Outbox consumers, generic financial-event taxonomy, rejection event names, frontend work, static OpenAPI changes, migrations, T26 changes, T27 changes, or any Invoice mutation beyond approved T29.

## Approval record

Human approval explicitly granted on 2026-09-14.

Approval authorizes the exact V1 audit action `INVOICE_MANUAL_CLOSED`, entity type `INVOICE`, minimal metadata boundary, atomic audit requirement, no duplicate audit on idempotent retry, and no new Outbox event.

This is implementation authorization, not final implementation homologation.

> "Quem pede um, pede bis."
