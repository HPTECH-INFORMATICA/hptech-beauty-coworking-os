# BCOS — Product Reconciliation Gate

> "Quem pede um, pede bis."

**Status:** ACTIVE AUDIT / NOT A HOMOLOGATION RECORD

This matrix reconciles the product surface against the actual repository. It does not promote milestones independently; homologation authority remains in each gate/ADR and explicit human decisions. PRD MASTER v1.0 and Architecture Freeze v1.2 are immutable implementation authorities and are never reopened by this matrix.

| CAPACIDADE | DOMÍNIO | BANCO | API | FRONTEND | TESTES | DOCUMENTAÇÃO | STATUS / GAP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Identity / Tenant / RBAC | Implemented tenant context, memberships and server-side permissions | Baseline schema contains tenancy/identity structures | Authentication/tenant authorization is used by application services | No dedicated authenticated product shell/role navigation is exposed in the current App Router | API authentication/RBAC tests exist | M1 baseline and project status | BACKEND BASELINE PRESENT; frontend product exposure incomplete |
| Units / Reception Hours | Implemented | Persisted | `/api/v1/units` and unit services | Current home consumes Units | API tests present | M2 + reception contracts | IMPLEMENTED; UI exposure narrow |
| Resources / Categories | Implemented; physical integrity tied to occupancy model | Persisted | Resource/category routers included | Current home consumes Resources | API tests present | M2/M3 | IMPLEMENTED; UI exposure narrow |
| Professionals | Implemented with tenant/own-scope rules | Persisted | Professionals router plus authenticated own-scope Professional Portal reads | Current reception surface consumes Professionals; no dedicated Professional Portal route/shell | API tests cover tenant and own-scope authorization | M1/M2 + static OpenAPI | BACKEND + OWN-SCOPE READ API IMPLEMENTED; dedicated portal frontend missing |
| Availability | `ResourceOccupancy` remains physical authority; Availability is preventive query | PostgreSQL exclusion/integrity baseline | Availability router included | No dedicated availability workflow/page | API availability tests present | M3 | BACKEND IMPLEMENTED; product workflow incomplete in frontend |
| Booking | Booking distinct from Usage; frozen pricing snapshot | Persisted with occupancy integrity | Bookings router included | `/agenda` exposes operational booking state; complete booking management remains incomplete | Router/domain/service and frontend tests present | M4 | BACKEND IMPLEMENTED; frontend management surface incomplete |
| Usage / Check-in / Check-out | Usage lifecycle implemented; checkout emits `USAGE_COMPLETED` transactionally | Persisted + Outbox | Usages router included | Routed `/check-in` and `/operacao` workflows are present and connect to server actions | API/worker/frontend tests present | M6/M7 | IMPLEMENTED OPERATIONAL FLOW; broader Reception OS exposure remains incomplete |
| Pricing | Frozen PricingRule definition consumed from Booking snapshot | Pricing structures persisted | Pricing router included | No Pricing administration UI | API/worker pricing tests present | M4/M7-A3 | ENGINE IMPLEMENTED; administration exposure incomplete |
| Billing / Invoice | PER_USAGE and ACCUMULATED_OPEN_INVOICE materialization implemented; T25/T28/T29/T30/T31 locked | Invoice, InvoiceItem, billing contract/cycle schema through migration 0007; MANUAL lifecycle uses `manual_closed_at` | Invoice list/detail plus tenant-scoped MANUAL close command implemented and reconciled to static OpenAPI; close requires `OPERATIONS` | `/financeiro` exposes operational Invoice/receivables actions | Worker materialization plus Billing read/lifecycle/audit and frontend regression tests | M7-A1/A2/A3/T25/T28/T29/T30/T31 | CORE + OPERATIONAL READ + MANUAL CLOSE + FINANCEIRO SURFACE PRESENT; broader financial administration remains incomplete |
| Payments | Confirmed PIX service implemented with idempotency and Invoice status recomputation | Payments persisted | Payments router included | `/financeiro` exposes confirmed PIX operational action | API payment and frontend tests exist | M7 contracts contain historical non-goal wording in places | API + OPERATIONAL FRONTEND EXPOSURE PRESENT; static/runtime contract reconciliation remains controlled work |
| Outbox Worker | Claim/retry/recovery/runtime and USAGE_COMPLETED dispatch implemented | Outbox persisted with processing recovery fields; `FAILED` exists physically | Internal worker concern | No UI required for processing itself | Worker suite + consumer rollback/retry regression | M7-A3; T27 proposal not authoritative for threshold | IMPLEMENTED RETRY/RECOVERY; terminal FAILED threshold has unresolved authority and remains fail-closed |
| Reception OS | Canonical operational read model composes bookings/usages/resources/professionals while preserving Booking ≠ Usage | Existing operational/financial schema | `/api/v1/reception/now` and `/api/v1/reception/agenda` are runtime routes | Central and `/agenda` consume Reception state; routed check-in/operation/finance flow exists | Reception API/OpenAPI and frontend regression tests | Static OpenAPI + Product Reconciliation | MATERIAL OPERATIONAL SURFACE PRESENT; complete Reception OS management still incomplete |
| Professional Portal | Authenticated professional is resolved server-side by tenant + external identity; client cannot select another professional | Uses tenant/professional, booking and invoice records | `/api/v1/professional/me/bookings` and `/api/v1/professional/me/invoices` are runtime own-scope reads | No dedicated portal route/shell | OpenAPI route and client-scope regression tests | Static OpenAPI + M1 | OWN-SCOPE API MATERIALIZED; dedicated product surface not exposed |
| Owner Dashboard | Supporting operational/financial data exists | Existing schema | Static OpenAPI declares dashboard aggregation, but runtime semantics for financial period aggregation are not independently defined in current traced authority | No Owner Dashboard route | No dedicated dashboard test surface identified | Static OpenAPI/product intent | CONTRACT SHAPE PRESENT; implementation remains blocked against inventing aggregation semantics |
| Production | Health endpoint, quality workflow and deployment stack documented | Neon baseline documented | FastAPI executable | Next.js executable | Quality Gate covers API/Worker/Web | PROJECT_STATUS/README | ENGINEERING FOUNDATION PRESENT; production-readiness/deployment gate remains separate |

## Reconciliation findings

1. The repository is not a skeleton: substantial operational, pricing, billing, payment and Outbox behavior exists in backend/domain/database layers.
2. The Next.js product surface remains narrower than the implemented backend, but Reception, Agenda, Check-in, Operation and Financeiro are now material routed surfaces rather than an isolated summary.
3. T26 is HUMAN HOMOLOGATED / LOCKED as a reconciliation to the immutable M7-A2-T1 reception-closing authority; it introduces no new pricing decision.
4. T28 closed the Invoice read API asymmetry with tenant-scoped list/detail endpoints and is HUMAN HOMOLOGATED / LOCKED.
5. T29/T30 close the approved V1 MANUAL Invoice lifecycle gap: explicit MANUAL accumulated Invoice close is implemented with row locking, `OPERATIONS`, immutable idempotent UTC `manual_closed_at`, financial-state/identity validation and transactional `INVOICE_MANUAL_CLOSED` audit evidence. T29 and T30 are HUMAN HOMOLOGATED / LOCKED.
6. T31 reconciled static OpenAPI V1 with the already homologated runtime Billing read/MANUAL-close surface and is HUMAN HOMOLOGATED / LOCKED.
7. Automatic WEEKLY/BIWEEKLY/MONTHLY accumulated Invoices and PER_USAGE do not gain an explicit close operation from T29. Reopen/cancel/adjustment/discount/due-date/issuance semantics remain outside the locked boundary.
8. Payments remain separate from lifecycle closure: confirmed PIX settlement exists and a closed MANUAL Invoice may still receive valid Payment when financial state permits.
9. T27 cannot be implemented from the current repository authority without inventing a maximum-attempt threshold. The earlier approved Outbox contract explicitly leaves retry limit/FAILED threshold undefined; the T27 document remains a proposal rather than authority.
10. Consumer atomicity remains regression-protected.
11. Reception `now`/`agenda` are now runtime-backed canonical operational reads and the web consumes them without collapsing Booking into Usage.
12. Professional Portal own-scope read contracts are now materialized in runtime; the remaining Professional Portal gap is a dedicated frontend surface.
13. T32 remains HUMAN APPROVED / IMPLEMENTATION AUTHORIZED and limited strictly to static OpenAPI Invoice `limit`/`offset` documentation reconciliation.
14. Owner Dashboard must not be implemented from schema shape alone where financial period aggregation semantics would have to be invented.

## Controlled next gaps

Current verified boundaries are:

- T27 terminal Outbox `FAILED` / maximum-attempt policy — implementation remains fail-closed until the threshold can be traced to already-approved immutable authority; no new PRD/Architecture decision will be invented;
- Reception OS frontend — material operational flow exists, but complete management exposure remains incomplete;
- Professional Portal — own-scope runtime API is implemented; dedicated frontend route/shell remains absent;
- Owner Dashboard — static response shape exists, but untraced aggregation semantics must not be invented;
- T32 static OpenAPI Invoice pagination — exact authorized documentation-only reconciliation remains pending implementation;
- production-readiness/deployment — remains a separate reconciliation gate.

Frontend expansion must follow the immutable PRD/Architecture authority and existing API/domain contracts. It must not invent missing financial lifecycle or aggregation semantics.

> "Quem pede um, pede bis."
