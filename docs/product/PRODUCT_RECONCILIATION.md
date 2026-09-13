# BCOS — Product Reconciliation Gate

> "Quem pede um, pede bis."

**Status:** ACTIVE AUDIT / NOT A HOMOLOGATION RECORD

This matrix reconciles the product surface against the actual repository. It does not promote any milestone to HUMAN HOMOLOGATED / LOCKED and does not reopen locked baselines.

| CAPACIDADE | DOMÍNIO | BANCO | API | FRONTEND | TESTES | DOCUMENTAÇÃO | STATUS / GAP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Identity / Tenant / RBAC | Implemented tenant context, memberships and server-side permissions | Baseline schema contains tenancy/identity structures | Authentication/tenant authorization is used by application services; auth is infrastructure rather than a product screen | No dedicated authenticated product shell/role navigation is exposed in the current App Router | API authentication/RBAC tests exist | M1 baseline and project status | BACKEND BASELINE PRESENT; frontend product exposure incomplete |
| Units / Reception Hours | Implemented | Persisted | `/api/v1/units` and unit services | Current home consumes Units | API tests present | M2 + reception contracts | IMPLEMENTED; UI exposure narrow |
| Resources / Categories | Implemented | Persisted; physical integrity tied to occupancy model | Resource and category routers included | Current home consumes Resources | API tests present | M2/M3 | IMPLEMENTED; UI exposure narrow |
| Professionals | Implemented with tenant/own-scope rules | Persisted | Professionals router included | Current home consumes Professionals | API tests present | M1/M2 | IMPLEMENTED; no dedicated Professional Portal |
| Availability | `ResourceOccupancy` remains physical authority; Availability is preventive query | PostgreSQL exclusion/integrity baseline | Availability router included | No dedicated availability workflow/page; current frontend centers reception summary | API availability tests present | M3 | BACKEND IMPLEMENTED; product workflow incomplete in frontend |
| Booking | Booking distinct from Usage; frozen pricing snapshot | Persisted with occupancy integrity | Bookings router included | Current home consumes Bookings; no complete booking management route set | Router/domain/service tests present | M4 | BACKEND IMPLEMENTED; frontend management surface incomplete |
| Usage / Check-in / Check-out | Usage lifecycle implemented; checkout emits `USAGE_COMPLETED` transactionally | Persisted + Outbox | Usages router included | No complete check-in/check-out operational workflow exposed as dedicated route | API/worker tests present | M6/M7 | BACKEND IMPLEMENTED; Reception OS exposure incomplete |
| Pricing | Frozen PricingRule definition consumed from Booking snapshot | Pricing structures persisted | Pricing router included | No Pricing administration UI | API/worker pricing tests present | M4/M7-A3 | ENGINE IMPLEMENTED; administration intentionally not yet reconciled |
| Billing / Invoice | PER_USAGE and ACCUMULATED_OPEN_INVOICE materialization implemented; T25 locked | Invoice, InvoiceItem, billing contract/cycle schema through migration 0007 | No Invoice/Billing router is included in current FastAPI application | No Financeiro/Billing route | Worker materialization/regression tests present | M7-A1/A2/A3/T25 | CORE MATERIALIZATION IMPLEMENTED; operational Billing API/UI is a real product gap |
| Payments | Confirmed PIX service is implemented with idempotency and Invoice status recomputation | Payments persisted | Payments router included | No payment/receivables UI | API payment tests exist | M7 contracts still contain older historical non-goal wording in places | API IMPLEMENTED; frontend exposure/document reconciliation incomplete |
| Outbox Worker | Claim/retry/recovery/runtime and USAGE_COMPLETED dispatch implemented | Outbox persisted with processing recovery fields | Internal worker concern | No UI required for processing itself | Worker suite + repository Quality Gate | M7-A3 | IMPLEMENTED; terminal FAILED policy remains explicitly undefined |
| Reception OS | Domain building blocks exist across bookings/usages/resources/professionals | Uses existing operational schema | Multiple operational routers exist | Single current `app/page.tsx`; visible reception navigation is not a complete routed OS | One frontend page test plus backend suites | Product framing documented | PARTIAL PRODUCT SURFACE — largest visible delivery gap |
| Professional Portal | Own-scope authorization exists in backend | Uses tenant/professional records | Supporting APIs exist | No dedicated portal route/shell | Backend authorization tests exist | PRD/M1 | NOT EXPOSED IN FRONTEND |
| Owner Dashboard | Supporting operational/financial data exists in backend/database | Existing schema | No dedicated dashboard aggregation API identified in current app registration | No Owner Dashboard route | No dedicated dashboard test surface identified | PRD/product intent | NOT IMPLEMENTED AS PRODUCT SURFACE |
| Production | Health endpoint, quality workflow and deployment stack are documented | Neon baseline documented | FastAPI executable | Next.js executable | Quality Gate covers API/Worker/Web | PROJECT_STATUS/README | ENGINEERING FOUNDATION PRESENT; production-readiness/deployment gate remains separate |

## Reconciliation findings

1. The repository is not a skeleton: substantial operational, pricing, billing, payment and Outbox behavior exists in backend/domain/database layers.
2. The current Next.js App Router contains only the root page plus layout/styles. The frontend product surface is therefore materially narrower than the implemented backend.
3. Billing is a concrete asymmetry: worker/database materialization exists, but the FastAPI application currently registers no Billing/Invoice router and the frontend exposes no Financeiro workflow.
4. Payments are further ahead than some historical contract non-goal wording suggests: the current API registers a Payments router and contains confirmed PIX settlement behavior. Historical ADR text must remain historical unless explicitly superseded; live product/status documentation should reflect the actual implementation.
5. `M7-A3-T26` is a proposed reconciliation gate for the reception-closing contradiction. It is not HUMAN HOMOLOGATED / LOCKED until explicit human approval.

## Controlled next gaps

The next M7-A3 decision must be selected from actual unresolved contracts, not invented from generic product expectations. Current verified candidates are:

- terminal Outbox `FAILED` / maximum-attempt policy, repeatedly left undefined by M7-A3 contracts;
- Billing/Invoice operational boundary needed before exposing accumulated invoices to Reception/Owner workflows;
- explicit Invoice closing lifecycle for accumulated cycles/manual closing, if required by the frozen product rules.

Frontend expansion should follow the reconciled product architecture and existing API/domain authority. It must not create a generic ERP navigation or pretend missing backend contracts already exist.

> "Quem pede um, pede bis."
