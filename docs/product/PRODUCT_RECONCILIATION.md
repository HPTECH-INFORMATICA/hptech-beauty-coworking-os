# BCOS — Product Reconciliation Gate

> "Quem pede um, pede bis."

**Status:** ACTIVE AUDIT / NOT A HOMOLOGATION RECORD

This matrix reconciles the product surface against the actual repository. It does not promote milestones independently; homologation authority remains in each gate/ADR and explicit human decisions. PRD MASTER v1.0 and Architecture Freeze v1.2 are immutable implementation authorities and are never reopened by this matrix.

| CAPACIDADE | DOMÍNIO / BACKEND | FRONTEND ATUAL | STATUS / GAP |
| --- | --- | --- | --- |
| Identity / Tenant / RBAC | Tenant context, memberships and server-side permissions implemented | No complete authenticated role-aware product shell | BACKEND PRESENT; visible identity/role experience incomplete |
| Units / Reception Hours | Persisted and exposed by API | Central consumes active Unit and timezone | IMPLEMENTED; administration exposure remains narrow |
| Resources / Categories | Persisted; physical integrity tied to ResourceOccupancy | Central, Agenda and Availability expose operational resources | OPERATIONAL EXPOSURE PRESENT; administration surface incomplete |
| Professionals | Persisted with tenant and own-scope rules | Central/Agenda use professionals; dedicated `/profissional` exists | OWN-SCOPE PORTAL EXPOSED; broader administration remains separate |
| Availability | ResourceOccupancy remains physical authority; preventive availability API exists | Dedicated `/disponibilidade` explores a unit/time window, reports canonical resource availability and hands an available resource/time window to `/agenda` | VISIBLE AVAILABILITY WORKFLOW IMPLEMENTED |
| Booking | Booking distinct from Usage; pricing snapshot preserved | `/agenda` creates and confirms reservations, accepts Availability handoff and routes confirmed bookings to check-in | CORE VISIBLE JOURNEY IMPLEMENTED |
| Usage / Check-in / Check-out | Usage lifecycle and transactional USAGE_COMPLETED Outbox implemented | `/check-in` starts real Usage; `/operacao` exposes active professional/resource/times and check-out | CORE VISIBLE JOURNEY IMPLEMENTED |
| Reception OS | Canonical Reception now/agenda read models materialized | `/` is operational Central; Agenda, Availability, Check-in and active Operation are routed surfaces | MATERIALIZED; continue product polish without changing domain authority |
| Pricing | Frozen PricingRule definition consumed from Booking snapshot | No Pricing administration UI | ENGINE IMPLEMENTED; administration exposure incomplete |
| Billing / Invoice | PER_USAGE/ACCUMULATED materialization plus list/detail and MANUAL close implemented | `/financeiro` shows professional, total, confirmed amount, remaining amount, item composition and manual close when authorized; checkout handoff represents asynchronous materialization and refreshes while pending | OPERATIONAL FINANCE SURFACE IMPLEMENTED |
| Payments | Confirmed PIX service implemented with idempotency and Invoice status recomputation | `/financeiro` exposes PIX confirmation on receivable invoices | OPERATIONAL PIX SURFACE IMPLEMENTED; static/runtime contract reconciliation remains controlled separately |
| Outbox Worker | Claim/retry/recovery and USAGE_COMPLETED dispatch implemented | Billing handoff exposes only business-facing processing state; Worker/Outbox internals remain server-side | IMPLEMENTED; T27 terminal threshold remains authority-blocked/fail-closed |
| Professional Portal | Own-scope booking/invoice reads implemented | `/profissional` exposes own reservations, own invoices and business-facing statuses | VISIBLE OWN-SCOPE SURFACE IMPLEMENTED |
| Owner Dashboard | Supporting operational/financial data exists; no authoritative dedicated aggregation implementation verified | No dedicated Owner Dashboard route | NOT IMPLEMENTED AS PRODUCT SURFACE; do not invent period semantics |
| Production | Health/quality/deployment foundation exists | Next.js production build is proven by Quality Gate; deployment configuration remains separate | ENGINEERING FOUNDATION PRESENT; production delivery gate still open |

## Current verified visible journey

`Central da Recepção → Disponibilidade → Agenda/Reserva → Confirmação → Check-in → Uso real → Check-out → processamento assíncrono do Billing → Financeiro → PIX`

This journey is now materially represented by routed product surfaces. The checkout-to-finance handoff preserves asynchronous Billing: the browser does not create invoices, invoke Worker/Outbox internals or force synchronous financial processing. Human homologation is still required for visible business behavior after production delivery; technical internals are not delegated to human homologation.

## Controlled unresolved gaps

1. **T27** — terminal Outbox `FAILED` / maximum-attempt threshold remains blocked until traceable authority exists. No threshold is invented.
2. **Identity / role-aware shell** — server-side RBAC exists, but a complete authenticated role-aware navigation experience is not yet exposed.
3. **Pricing administration** — engine exists; administration surface is not exposed.
4. **Owner Dashboard** — no dedicated surface/aggregation is implemented; financial period attribution semantics must not be invented.
5. **Payments static/runtime reconciliation** — deliberate runtime PIX behavior and static OpenAPI divergence require authority-backed reconciliation rather than implementation-by-guess.
6. **Production delivery** — deployment configuration must respect the monorepo and organizational repository model; deployment is not evidence of product completeness by itself.

## Reconciliation guardrails

- PRD MASTER v1.0 and Architecture Freeze v1.2 remain immutable.
- Booking remains distinct from Usage.
- ResourceOccupancy remains canonical physical occupancy authority.
- Pricing, Billing and Payment remain distinct boundaries.
- No financial lifecycle semantics are invented by frontend work.
- Frontend changes and their tests move together.
- A technical Quality Gate is not a substitute for human homologation of visible business behavior.

> "Quem pede um, pede bis."
