# M7-A3-T31 — Static OpenAPI Billing Reconciliation Contract

> "Quem pede um, pede bis."

**Status:** PROPOSED / AWAITING HUMAN APPROVAL

## Purpose

Reconcile the independently locked static OpenAPI V1 document with the already homologated runtime Billing boundaries T28, T29 and T30 without silently reopening unrelated API contracts.

## Verified drift

The static `docs/api/openapi.yaml` already declares the `Invoices` tag and documents:

- `GET /api/v1/invoices` with operationId `listInvoices`;
- `GET /api/v1/invoices/{invoice_id}` with operationId `getInvoice`.

However, the current runtime Billing API exposes additional homologated contract surface that is not represented by the static document:

- `POST /api/v1/invoices/{invoice_id}/close` with operationId `closeManualInvoice`;
- runtime `InvoiceSummary` includes `source_usage_id`, `professional_billing_contract_id`, `billing_cycle_start`, `billing_cycle_end` and `manual_closed_at`;
- runtime `InvoiceDetail` includes InvoiceItems plus deterministic `confirmed_amount` and `remaining_amount` projections;
- runtime lifecycle write behavior is governed by locked T29/T30.

Targeted inspection of the static V1 document found no `manual_closed_at`, `professional_billing_contract_id` or `billing_cycle_start` representation for the homologated runtime boundary, and no MANUAL close action.

## Proposed reconciliation boundary

If approved, T31 authorizes a documentation-only update to `docs/api/openapi.yaml` limited to the already implemented and homologated Billing behavior.

The reconciliation must:

1. preserve existing `GET /api/v1/invoices` and `GET /api/v1/invoices/{invoice_id}` operationIds;
2. align the static Invoice read schemas with locked T28 runtime projections;
3. add the exact locked T29 runtime command `POST /api/v1/invoices/{invoice_id}/close` with operationId `closeManualInvoice`;
4. document that the command requires the existing authenticated tenant context and `OPERATIONS` authorization;
5. document success using the runtime Invoice summary representation;
6. document 403, 404 and 409 outcomes consistently with runtime behavior;
7. document `manual_closed_at` as the MANUAL materialization lifecycle boundary while financial `status` remains OPEN/PARTIALLY_PAID/PAID/CANCELLED;
8. introduce no generic Invoice CRUD, reopen, cancel, adjustment, discount, due-date, issuance or automatic-cycle close semantics;
9. introduce no new Payment, Pricing, Outbox, T26 or T27 semantics;
10. change no runtime code, database migration or frontend.

## Authority preservation

T31 is reconciliation only. It may describe behavior already locked by T28/T29/T30, but it cannot expand or reinterpret those gates.

The existing OpenAPI V1 baseline remains locked until this additive reconciliation is explicitly approved, implemented, validated and separately homologated.

## Validation requirements

Implementation must prove:

- the static OpenAPI parses successfully;
- existing static contract tests remain green;
- Billing list/detail paths remain documented;
- the MANUAL close path and operationId match runtime exactly;
- documented Billing schemas cover the homologated runtime fields without inventing new fields;
- no unrelated static API path or schema is modified except where strictly required by shared references;
- full BCOS Quality Gate remains green.

## Non-goals

T31 does not authorize runtime API changes, migrations, frontend work, Financeiro UI, T26 homologation, T27 implementation, new Invoice lifecycle semantics, new Payment behavior, new Outbox events or a wholesale rewrite/regeneration of the static OpenAPI document.

## Decision required

Human approval is required before modifying the locked static `docs/api/openapi.yaml` baseline.

Approval of T31 would authorize only the narrow additive reconciliation described above. Final homologation would remain separate after implementation and green verification.

> "Quem pede um, pede bis."
