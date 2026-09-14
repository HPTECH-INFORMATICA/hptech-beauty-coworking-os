# M7-A3-T31 — Static OpenAPI Billing Reconciliation Contract

> "Quem pede um, pede bis."

**Status:** HUMAN HOMOLOGATED / LOCKED

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

## Approved reconciliation boundary

T31 authorizes a documentation-only update to `docs/api/openapi.yaml` limited to the already implemented and homologated Billing behavior.

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

The existing OpenAPI V1 baseline remains locked with this homologated additive reconciliation.

## Validation evidence

Implementation was integrated to `main` by PR #5 at squash commit `7be0ad8281ec583bbd768926b9ac11ac6c9c173b`.

Verification evidence:

- PR Quality Gate #106 completed successfully;
- post-merge `main` BCOS Quality Gate #107, run `34905954114`, completed successfully;
- API, Worker and Web jobs completed successfully;
- the static MANUAL close path is documented as `POST /api/v1/invoices/{invoice_id}/close` with operationId `closeManualInvoice`;
- the static Invoice/InvoiceDetail/InvoiceItem projections were reconciled with the already homologated runtime Billing surface;
- no runtime code, migration, frontend, T26 or T27 semantics were changed by T31.

## Non-goals

T31 does not authorize runtime API changes, migrations, frontend work, Financeiro UI, T26 homologation, T27 implementation, new Invoice lifecycle semantics, new Payment behavior, new Outbox events or a wholesale rewrite/regeneration of the static OpenAPI document.

## Homologation record

Human implementation approval was explicitly granted on 2026-09-14. After implementation, PR integration and green post-merge verification, final human homologation was explicitly granted on 2026-09-14.

T31 is therefore **HUMAN HOMOLOGATED / LOCKED** for the exact narrow reconciliation above.

This homologation does not approve or homologate T26 or T27.

> "Quem pede um, pede bis."
