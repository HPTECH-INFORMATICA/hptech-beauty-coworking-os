# M7-A3-T28 — Billing Operational Read Boundary Contract

> "Quem pede um, pede bis."

**Status:** HUMAN HOMOLOGATED / LOCKED

## Purpose

Define the minimum tenant-scoped Billing read boundary required to expose already-materialized Invoice evidence to future Reception / Owner workflows without changing Pricing, materialization, Invoice lifecycle, or Payment semantics.

## Existing authority preserved

T28 does not reopen or reinterpret:

- T25 accumulated Invoice materialization and identity;
- PER_USAGE Invoice identity;
- InvoiceItem persisted evidence and total derivation;
- T26 reception-closing authority (still awaiting human homologation);
- T27 terminal Outbox failure policy (still awaiting human approval);
- confirmed PIX Payment behavior already implemented by the API;
- existing server-side tenancy/RBAC foundations.

## Homologated V1 read boundary

The Billing operational API is read-only and tenant-scoped.

### Invoice summary

The API exposes persisted or deterministically derived Invoice evidence within the approved boundary:

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

No invented business status such as issued, overdue, closed, due, collectible, forgiven, or settled is part of T28.

### Invoice detail

Invoice detail exposes persisted InvoiceItems faithfully, preserving stored item type, description, quantity, unit amount, total amount, Usage identity when present, and temporal segmentation evidence when present.

### Payment evidence

Invoice detail may expose confirmed-payment total and remaining amount only as deterministic read projections from persisted Payments and Invoice total. Reads do not create or mutate Payments.

## Tenant and authorization boundary

- Every Invoice read is tenant-scoped server-side.
- Cross-tenant guessed Invoice IDs do not disclose existence or financial data.
- The endpoint uses authenticated TenantContext/RBAC infrastructure rather than request-provided tenant authority.
- V1 Billing read requires existing `OPERATIONS` permission.
- Owner, Admin and Reception satisfy that baseline; Professional fails closed because its baseline is `PROFESSIONAL_OWN` rather than coworking-wide `OPERATIONS`.

## Query/pagination boundary

The homologated implementation supports persisted identity/status filters and deterministic ordering `created_at DESC, id DESC`, with bounded `limit` and non-negative `offset`.

## Write prohibition

T28 authorizes no new Billing write endpoint. It does not authorize closing accumulated Invoices, setting `manual_closed_at`, reopening/cancelling Invoices, editing InvoiceItems, manual adjustments/discounts, due dates, total mutation, Payment bypasses, Outbox retries, or Pricing/Billing contract changes.

## Invoice lifecycle boundary remains unresolved

The physical schema contains `manual_closed_at`, while T25 deliberately does not authorize the worker to close/rotate/reopen MANUAL invoices. T28 does not decide who may close a MANUAL accumulated Invoice, under what conditions, what mutations remain legal after closing, or whether automatic-cycle Invoices require an explicit close/issue transition.

Any such lifecycle write requires a separate traceable contract and must not be inferred from this homologation.

## Implementation evidence

The implementation merged through PR #1 and provides:

- `GET /api/v1/invoices`;
- `GET /api/v1/invoices/{invoice_id}`;
- tenant-scoped repository reads;
- `OPERATIONS` authorization;
- persisted InvoiceItem evidence;
- confirmed-payment and remaining projections;
- deterministic pagination;
- service/router regression tests;
- no migration;
- no frontend change;
- no Billing write route.

Merged baseline commit: `c5e7f01bdafefe7b502e6e88f1cb9ee7d7b5ce31`.

The post-merge Quality Gate completed successfully for API, Worker and Web before human homologation.

## Frontend boundary

T28 does not homologate or authorize a Financeiro frontend. Frontend expansion remains a separate product gate built on this locked API boundary.

## Promotion / lock record

- Human implementation approval: 2026-09-14.
- Technical implementation: merged and Quality Gate verified on 2026-09-14.
- Human homologation: explicitly granted on 2026-09-14 after technical verification.
- Final state: **HUMAN HOMOLOGATED / LOCKED**.

T28 must not be reopened silently. Any change to this boundary requires a new traceable gate.

> "Quem pede um, pede bis."
