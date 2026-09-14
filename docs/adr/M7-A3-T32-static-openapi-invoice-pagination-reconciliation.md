# M7-A3-T32 — Static OpenAPI Invoice Pagination Reconciliation

> "Quem pede um, pede bis."

**Status:** HUMAN APPROVED / IMPLEMENTATION AUTHORIZED

## Purpose

Reconcile one residual documentation drift discovered by the Product Reconciliation Gate after T31: the locked T28 runtime `GET /api/v1/invoices` accepts bounded `limit` and non-negative `offset`, while the static OpenAPI currently omits those two already-homologated query parameters.

## Existing authority

T28 is `HUMAN HOMOLOGATED / LOCKED` and explicitly homologates deterministic ordering `created_at DESC, id DESC`, bounded `limit` and non-negative `offset`.

The runtime Billing router implements:

- `limit`: integer, default `50`, minimum `1`, maximum `100`;
- `offset`: integer, default `0`, minimum `0`.

T31 is `HUMAN HOMOLOGATED / LOCKED` and authorizes the static OpenAPI to describe the already locked T28 Billing read surface without expanding runtime semantics.

## Verified residual drift

`docs/api/openapi.yaml` currently documents `professional_id` and `status` for `GET /api/v1/invoices`, but omits `limit` and `offset`.

This is a documentation-contract defect only. Runtime behavior is already implemented and homologated.

## Authorized reconciliation

T32 authorizes exactly one OpenAPI correction under `GET /api/v1/invoices`:

- add optional query parameter `limit` with `type: integer`, `default: 50`, `minimum: 1`, `maximum: 100`;
- add optional query parameter `offset` with `type: integer`, `default: 0`, `minimum: 0`.

No other path, schema, response, runtime code, database migration, worker behavior, frontend, PRD, Architecture Freeze, T26, T27, T28, T29, T30 or T31 semantics may be changed by this gate.

## Approval record

Human approval for this exact reconciliation was explicitly granted on 2026-09-14 after the defect and intended narrow correction were presented.

T32 is therefore **HUMAN APPROVED / IMPLEMENTATION AUTHORIZED**. Final homologation remains separate and requires post-implementation verification.

> "Quem pede um, pede bis."
