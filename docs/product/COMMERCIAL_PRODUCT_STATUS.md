# BCOS — Commercial Product Delivery Status

> "Quem pede um, pede bis."

## Current direction

The operational journey already implemented remains valid, but it is no longer treated as sufficient evidence of product launch readiness.

The authoritative expansion baseline is:

- `docs/product/COMMERCIAL_ADMIN_BASELINE.md`

## Product delivery target

BCOS must prove the complete business journey:

`HPTECH onboarding → tenant activation → tenant configuration → professional access → commercial availability/calendar + price → booking → check-in → usage → check-out → Billing → receipt/payment → tenant administrative finance`.

## Active gate

**C1 — Product authority and identity**

Before new commercial booking homologation, implementation must establish:

1. explicit HPTECH platform-operator authority;
2. production identity/session authority;
3. tenant onboarding/lifecycle contract;
4. OWNER invitation/first-access lifecycle;
5. tenant user administration authority.

## Existing engines preserved

The following are not discarded or rewritten merely because the commercial/admin surface is incomplete:

- strict tenant isolation;
- ResourceOccupancy;
- Booking distinct from Usage;
- Pricing authority and immutable booking pricing snapshot;
- Billing/Invoice;
- Payments;
- Outbox/Worker;
- audit foundation.

## Launch readiness

**NOT LAUNCH READY.**

The existing reception/booking operational surface is an implemented subsystem. It is not the whole commercial SaaS product. C1 through C7 in the commercial/admin baseline must be implemented and human-homologated before BCOS is represented as launch-ready.

> "Quem pede um, pede bis."
