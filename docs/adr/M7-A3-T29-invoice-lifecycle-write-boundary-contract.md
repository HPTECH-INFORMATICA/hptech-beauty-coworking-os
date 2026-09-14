# M7-A3-T29 — Invoice Lifecycle Write Boundary Contract

> "Quem pede um, pede bis."

**Status:** PROPOSED / AWAITING HUMAN APPROVAL

## Purpose

Resolve the Invoice lifecycle gap exposed by the locked T25 accumulated-materialization contract and the locked T28 Billing operational read boundary before any Billing lifecycle write API or Financeiro UI is implemented.

T29 is a business/architecture decision gate. This proposal does not authorize production code, migration, frontend work, or a new Invoice status.

## Existing authority preserved

T29 MUST NOT reopen or reinterpret:

- T25 accumulated Invoice identity and materialization;
- T28 tenant-scoped read-only Billing API;
- PER_USAGE Invoice identity;
- persisted InvoiceItem evidence and total derivation;
- existing confirmed PIX Payment behavior;
- T26 reception-closing authority, still awaiting human homologation;
- T27 terminal Outbox failure policy, still awaiting human approval;
- the independently locked static OpenAPI V1 baseline.

## Physical evidence already present

Migration `0007_invoice_cycle_identity` already persists `manual_closed_at TIMESTAMPTZ NULL` and enforces at most one active MANUAL accumulated Invoice per tenant + historical professional Billing contract while `manual_closed_at IS NULL`.

T25 explicitly requires the worker to materialize only into `OPEN` Invoices and explicitly prohibits the worker from closing, rotating, reopening, or assigning `manual_closed_at` to MANUAL Invoices.

The existing Payment service may transition an Invoice from `OPEN` to `PARTIALLY_PAID` or `PAID` when confirmed PIX evidence is registered. It rejects payment into `CANCELLED` or already `PAID` Invoices.

Therefore the schema and existing behavior prove that a lifecycle boundary is required, but they do not by themselves authorize who closes an Invoice or the legal post-close mutations.

## Proposed V1 lifecycle boundary

### 1. MANUAL accumulated Invoice closure

V1 SHOULD allow explicit closure only for an accumulated MANUAL Invoice identified by all of:

- `source_usage_id IS NULL`;
- `professional_billing_contract_id IS NOT NULL`;
- `billing_cycle_start IS NULL`;
- `billing_cycle_end IS NULL`;
- `manual_closed_at IS NULL`.

Closure SHOULD persist `manual_closed_at` as a timezone-aware UTC instant.

Closure MUST NOT rewrite, delete, move, merge, or regenerate existing InvoiceItems.

Closure MUST NOT silently change Invoice totals; totals remain derived from persisted InvoiceItems.

After successful closure, the worker MUST NOT append new automatic financial effects to that closed MANUAL Invoice. A later completed Usage may resolve/create the next active MANUAL Invoice according to the already-locked T25 identity rules.

### 2. Authorization proposal

V1 SHOULD require existing `Permission.OPERATIONS`, preserving the same coworking-wide operational authority used by T28 Billing reads and confirmed PIX registration.

Under the current RBAC baseline this permits Owner, Admin and Reception and excludes Professional.

No new permission is proposed by T29 unless human approval explicitly requires a narrower role boundary.

### 3. Eligible financial state

A MANUAL Invoice SHOULD be closable only while its persisted status is `OPEN` or `PARTIALLY_PAID`.

A `PAID` or `CANCELLED` Invoice SHOULD fail closed for the explicit MANUAL-close operation because no new lifecycle mutation is required to establish payment/cancellation state.

This proposal does not redefine Payment semantics and does not create a new `CLOSED` Invoice status. `manual_closed_at` is the MANUAL materialization lifecycle boundary; `status` remains the existing financial/payment state.

### 4. Automatic accumulated cycles

WEEKLY, BIWEEKLY and MONTHLY Invoices already have immutable persisted `billing_cycle_start` / `billing_cycle_end` identity. V1 T29 SHOULD NOT add an explicit close/issue mutation to automatic-cycle Invoices.

Their cycle boundary already prevents later Usage allocation into the wrong cycle through T25 cycle resolution. Adding a second close state without a proven business requirement would duplicate lifecycle authority.

### 5. PER_USAGE Invoices

T29 SHOULD NOT add a close operation to PER_USAGE Invoices. Their lifecycle identity is the completed source Usage and their financial state continues to be governed by existing Invoice/Payment semantics.

### 6. Concurrency and idempotency

The lifecycle write MUST be tenant-scoped and lock the target Invoice row before mutation.

A first valid close MUST atomically persist `manual_closed_at`.

A repeated close request against the same already-closed Invoice SHOULD be idempotent only when the caller is requesting closure of that same Invoice and no contradictory mutation is requested; it MUST NOT reopen or replace the recorded close instant.

Concurrent attempts MUST converge on one persisted closure and MUST NOT produce two active successor MANUAL Invoices through the lifecycle endpoint itself.

### 7. Payment interaction

Closing a MANUAL Invoice MUST NOT mark it paid, create a Payment, cancel it, forgive remaining balance, or bypass the existing Payment API.

A closed MANUAL Invoice with remaining balance MAY continue to receive a valid existing Payment if its financial `status` otherwise permits payment. This preserves the separation between materialization closure and settlement.

### 8. Mutation prohibition after closure

After `manual_closed_at` is set:

- automatic worker materialization into that Invoice is forbidden by T25;
- InvoiceItems MUST remain immutable through the lifecycle endpoint;
- totals MUST NOT be manually overwritten;
- reopening is not authorized in V1;
- cancellation is not authorized by T29;
- manual ADJUSTMENT/DISCOUNT creation is not authorized by T29;
- due-date or issuance semantics are not authorized by T29.

## Proposed API boundary after approval

If T29 is human-approved, implementation MAY add one tenant-scoped lifecycle command for MANUAL accumulated Invoice closure. Exact route naming MUST be reconciled with the API contract gate before promotion.

The implementation MUST NOT add generic Invoice CRUD or unrelated financial writes.

## Audit requirement

A financial lifecycle write is operationally significant. Before implementation promotion, the repository MUST identify the existing Audit/Outbox authority applicable to this command. If no approved event contract exists, the implementation MUST stop at a separate traceable audit-event decision rather than invent an event name silently.

## Required tests after approval

Implementation tests MUST cover:

- tenant isolation;
- `OPERATIONS` authorization and Professional fail-closed behavior;
- MANUAL identity validation;
- OPEN closure;
- PARTIALLY_PAID closure;
- PAID/CANCELLED rejection under the approved rule;
- already-closed idempotency;
- immutable original close instant;
- automatic-cycle and PER_USAGE rejection;
- no InvoiceItem or total mutation;
- no Payment side effect;
- worker cannot rematerialize into the closed MANUAL Invoice;
- successor MANUAL identity remains governed by T25/database uniqueness;
- concurrency behavior;
- audit/event behavior once separately authorized if necessary.

## Non-goals

T29 does not authorize:

- a new Invoice status;
- generic Invoice edit/delete;
- reopening;
- cancellation;
- manual InvoiceItem creation;
- discounts/adjustments;
- due dates;
- issuance/overdue/collection semantics;
- automatic-cycle explicit close;
- PER_USAGE close;
- Payment changes;
- Pricing changes;
- Outbox retry-policy changes;
- Financeiro frontend;
- static OpenAPI V1 modification before its own reconciliation gate;
- database migration unless implementation proves a missing physical invariant.

## Human decisions required

Approval of T29 means approval of the following V1 business choices:

1. MANUAL accumulated Invoice closure is explicit and represented by existing `manual_closed_at` rather than a new Invoice status.
2. Owner, Admin and Reception may close through existing `OPERATIONS`; Professional may not.
3. OPEN and PARTIALLY_PAID are eligible for closure; PAID and CANCELLED are not.
4. Closing stops future materialization into that MANUAL Invoice but does not settle its balance.
5. Closed unpaid/partially-paid MANUAL Invoices may still receive valid Payments through the existing Payment boundary.
6. Automatic-cycle and PER_USAGE Invoices receive no new explicit close operation in V1.
7. Reopening/cancellation/adjustment/discount/due-date/issuance behavior remains outside this gate.

Until explicit human approval, this document is proposal-only and MUST NOT be treated as implementation authorization.

> "Quem pede um, pede bis."
