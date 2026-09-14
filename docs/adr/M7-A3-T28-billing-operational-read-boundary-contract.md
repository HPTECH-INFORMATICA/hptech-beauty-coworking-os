# M7-A3-T28 — Billing Operational Read Boundary Contract

> "Quem pede um, pede bis."

**Status:** HUMAN APPROVED / IMPLEMENTATION AUTHORIZED

## Purpose

Define the minimum tenant-scoped Billing read boundary required to expose already-materialized Invoice evidence to future Reception / Owner workflows without changing Pricing, materialization, Invoice lifecycle, or Payment semantics.

This contract exists because the repository already materializes PER_USAGE and ACCUMULATED_OPEN_INVOICE records and already accepts confirmed PIX payments by `invoice_id`, while the current FastAPI application has no Invoice/Billing read router. The missing read boundary prevents the product surface from safely discovering and inspecting the financial evidence that Payments already consumes.

## Existing authority preserved

T28 does not reopen or reinterpret:

- T25 accumulated Invoice materialization and identity;
- PER_USAGE Invoice identity;
- InvoiceItem persisted evidence and total derivation;
- T26 reception-closing authority (still awaiting human homologation);
- T27 terminal Outbox failure policy (still awaiting human approval);
- confirmed PIX Payment behavior already implemented by the API;
- existing server-side tenancy/RBAC foundations.

## Repository evidence motivating the boundary

The current repository establishes all of the following:

1. Worker materialization creates/reuses Invoice records and persists InvoiceItems.
2. Accumulated Invoice identity contains `professional_billing_contract_id`, cycle boundaries and `manual_closed_at`.
3. Payment confirmation already locks an Invoice by tenant + invoice ID, reads `status`, `currency` and `total_amount`, persists a confirmed PIX Payment, and recomputes Invoice payment status.
4. The FastAPI application currently registers Payments but no Invoice/Billing router.
5. Therefore a future Financeiro surface must not bypass the API or query Billing tables directly from the frontend.

## Approved V1 read boundary

The first Billing operational API is read-only and tenant-scoped.

### Invoice summary

The API MAY expose a paginated/listable Invoice summary containing only persisted or deterministically derived evidence already authorized by existing contracts:

- `id`;
- `professional_id`;
- `source_usage_id` when PER_USAGE;
- `professional_billing_contract_id` when accumulated;
- `billing_cycle_start`;
- `billing_cycle_end`;
- `manual_closed_at`;
- `status`;
- `currency`;
- `subtotal_amount`;
- `discount_amount`;
- `total_amount`;
- `created_at`;
- `updated_at`.

The API MUST NOT invent a new business status such as issued, overdue, closed, due, collectible, forgiven, or settled unless that state already exists in the frozen schema/contracts.

### Invoice detail

Invoice detail MAY additionally expose the persisted InvoiceItems belonging to that Invoice, including their existing identity/evidence fields. It MUST preserve the stored item type, description, quantity, unit amount, total amount, Usage identity when present, and temporal segmentation evidence when present.

### Payment evidence

Invoice detail MAY expose confirmed-payment totals and remaining amount as deterministic read projections from persisted Payments and Invoice total. It MUST NOT create or mutate a Payment as a side effect of a read.

## Tenant and authorization boundary

- Every Invoice read MUST be tenant-scoped server-side.
- An Invoice ID from another tenant MUST never disclose existence or financial data.
- The endpoint MUST use the existing authenticated TenantContext/RBAC infrastructure rather than accepting tenant authority from request payloads.
- Exact role/permission exposure for Owner, Admin, Reception and Professional MUST be reconciled against the frozen RBAC baseline before implementation. T28 does not silently broaden Professional access to coworking-wide financial data.
- The current RBAC baseline grants `OPERATIONS` to Owner, Admin and Reception, while Professional has only `PROFESSIONAL_OWN`. Because confirmed PIX settlement already requires `OPERATIONS`, the V1 Billing read boundary SHALL also require `OPERATIONS`. Professional therefore fails closed and receives no coworking-wide Invoice read access.

## Query/filter boundary

The first read boundary MAY support only filters backed by existing persisted identity, such as:

- Invoice ID;
- professional ID;
- existing Invoice status;
- cycle/time interval where applicable.

No search semantics based on invented labels, receivable aging, due date, overdue status or accounting categories are authorized.

Pagination/order must be deterministic. The approved implementation uses persisted ordering `created_at DESC, id DESC` with bounded `limit` and non-negative `offset`.

## Write prohibition

T28 does NOT authorize any new Billing write endpoint.

In particular, it does not authorize:

- closing an accumulated Invoice;
- setting `manual_closed_at`;
- reopening an Invoice;
- cancelling an Invoice;
- editing InvoiceItems;
- adding adjustments or discounts manually;
- setting due dates;
- changing materialized totals;
- marking an Invoice paid outside the already-approved Payment flow;
- retrying Outbox events;
- changing Pricing or Billing contracts.

## Invoice lifecycle boundary discovered by audit

The physical schema already contains `manual_closed_at`, and accumulated materialization deliberately requires an eligible MANUAL Invoice to have `manual_closed_at IS NULL`. However, T25 explicitly does not authorize the worker to close/rotate/reopen MANUAL invoices.

Therefore the repository has a real lifecycle boundary that remains unresolved: who may close a MANUAL accumulated Invoice, under what conditions, what financial mutations remain legal after closing, and whether automatic cycle Invoices require an explicit closing/issuing transition.

T28 intentionally does not answer those questions. They require a separate traceable lifecycle contract before any write API is implemented.

## Required implementation evidence

Tests must prove at least:

- tenant isolation for list and detail;
- no cross-tenant Invoice disclosure by guessed ID;
- deterministic pagination/order;
- PER_USAGE and accumulated identities serialize without conflation;
- InvoiceItems remain faithful to persisted evidence;
- confirmed-payment projection cannot exceed or mutate persisted financial evidence;
- unauthorized roles fail closed according to existing RBAC authority;
- reads perform no Invoice/InvoiceItem/Payment writes;
- OpenAPI contract and runtime route remain aligned.

## No migration gate

No migration is authorized or expected for this read boundary. The API must consume the existing schema.

If implementation discovers that a new persisted field is required merely to perform the read, stop and open a separate schema contract rather than silently migrating.

## Frontend boundary

T28 does not authorize Financeiro frontend implementation. A frontend surface may be opened only after the Billing read API is implemented, tested and reconciled with the product navigation/role model.

This prevents the frontend from becoming the source of financial truth or depending directly on database details.

## Promotion rule

Human approval was explicitly granted on 2026-09-14, promoting T28 to an implementation-authorized baseline. Technical completion and final HUMAN HOMOLOGATION remain separate gates and MUST NOT be inferred from this approval.

> "Quem pede um, pede bis."
