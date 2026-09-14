# BCOS — Product Reconciliation Gate

> "Quem pede um, pede bis."

**Status:** ACTIVE AUDIT / NOT A HOMOLOGATION RECORD

This matrix reconciles the product surface against the actual repository. It does not promote milestones independently; homologation authority remains in each gate/ADR and explicit human decisions.

| CAPACIDADE | DOMÍNIO | BANCO | API | FRONTEND | TESTES | DOCUMENTAÇÃO | STATUS / GAP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Identity / Tenant / RBAC | Implemented tenant context, memberships and server-side permissions | Baseline schema contains tenancy/identity structures | Authentication/tenant authorization is used by application services | No dedicated authenticated product shell/role navigation is exposed in the current App Router | API authentication/RBAC tests exist | M1 baseline and project status | BACKEND BASELINE PRESENT; frontend product exposure incomplete |
| Units / Reception Hours | Implemented | Persisted | `/api/v1/units` and unit services | Current home consumes Units | API tests present | M2 + reception contracts | IMPLEMENTED; UI exposure narrow |
| Resources / Categories | Implemented; physical integrity tied to occupancy model | Persisted | Resource/category routers included | Current home consumes Resources | API tests present | M2/M3 | IMPLEMENTED; UI exposure narrow |
| Professionals | Implemented with tenant/own-scope rules | Persisted | Professionals router included | Current home consumes Professionals | API tests present | M1/M2 | IMPLEMENTED; no dedicated Professional Portal |
| Availability | `ResourceOccupancy` remains physical authority; Availability is preventive query | PostgreSQL exclusion/integrity baseline | Availability router included | No dedicated availability workflow/page | API availability tests present | M3 | BACKEND IMPLEMENTED; product workflow incomplete in frontend |
| Booking | Booking distinct from Usage; frozen pricing snapshot | Persisted with occupancy integrity | Bookings router included | Current home consumes Bookings; no complete management route set | Router/domain/service tests present | M4 | BACKEND IMPLEMENTED; frontend management surface incomplete |
| Usage / Check-in / Check-out | Usage lifecycle implemented; checkout emits `USAGE_COMPLETED` transactionally | Persisted + Outbox | Usages router included | No complete check-in/check-out routed workflow | API/worker tests present | M6/M7 | BACKEND IMPLEMENTED; Reception OS exposure incomplete |
| Pricing | Frozen PricingRule definition consumed from Booking snapshot | Pricing structures persisted | Pricing router included | No Pricing administration UI | API/worker pricing tests present | M4/M7-A3 | ENGINE IMPLEMENTED; administration intentionally not yet reconciled |
| Billing / Invoice | PER_USAGE and ACCUMULATED_OPEN_INVOICE materialization implemented; T25/T28/T29/T30 locked | Invoice, InvoiceItem, billing contract/cycle schema through migration 0007; MANUAL lifecycle uses `manual_closed_at` | Invoice list/detail plus tenant-scoped MANUAL close command implemented; close requires `OPERATIONS` | No Financeiro/Billing route | Worker materialization plus Billing read/lifecycle/audit regression tests | M7-A1/A2/A3/T25/T28/T29/T30 | CORE + OPERATIONAL READ + MANUAL CLOSE API IMPLEMENTED; Financeiro UI remains separate gap |
| Payments | Confirmed PIX service implemented with idempotency and Invoice status recomputation | Payments persisted | Payments router included | No payment/receivables UI | API payment tests exist | M7 contracts contain historical non-goal wording in places | API IMPLEMENTED; frontend exposure/document reconciliation incomplete |
| Outbox Worker | Claim/retry/recovery/runtime and USAGE_COMPLETED dispatch implemented | Outbox persisted with processing recovery fields; `FAILED` exists physically | Internal worker concern | No UI required for processing itself | Worker suite + consumer rollback/retry regression | M7-A3; T27 proposed | IMPLEMENTED RETRY/RECOVERY; terminal FAILED policy awaits T27 human approval |
| Reception OS | Domain building blocks exist across bookings/usages/resources/professionals and Billing | Existing operational/financial schema | Multiple operational routers exist | Current frontend remains a narrow reception summary | Frontend page test plus backend suites | Product framing documented | PARTIAL PRODUCT SURFACE — largest visible delivery gap |
| Professional Portal | Own-scope authorization exists in backend | Uses tenant/professional records | Supporting APIs exist; Billing coworking-wide operations remain role-protected | No dedicated portal route/shell | Backend authorization tests exist | PRD/M1/T28/T29 | NOT EXPOSED IN FRONTEND |
| Owner Dashboard | Supporting operational/financial data exists | Existing schema | Billing operational APIs available; no dedicated dashboard aggregation API | No Owner Dashboard route | No dedicated dashboard test surface identified | PRD/product intent | NOT IMPLEMENTED AS PRODUCT SURFACE |
| Production | Health endpoint, quality workflow and deployment stack documented | Neon baseline documented | FastAPI executable | Next.js executable | Quality Gate covers API/Worker/Web | PROJECT_STATUS/README | ENGINEERING FOUNDATION PRESENT; production-readiness/deployment gate remains separate |

## Reconciliation findings

1. The repository is not a skeleton: substantial operational, pricing, billing, payment and Outbox behavior exists in backend/domain/database layers.
2. The Next.js product surface remains materially narrower than the implemented backend.
3. T28 closed the Invoice read API asymmetry with tenant-scoped list/detail endpoints and is HUMAN HOMOLOGATED / LOCKED.
4. T29/T30 close the approved V1 MANUAL Invoice lifecycle gap: explicit MANUAL accumulated Invoice close is implemented with row locking, `OPERATIONS`, immutable idempotent UTC `manual_closed_at`, financial-state/identity validation and transactional `INVOICE_MANUAL_CLOSED` audit evidence. T29 and T30 are HUMAN HOMOLOGATED / LOCKED.
5. Automatic WEEKLY/BIWEEKLY/MONTHLY accumulated Invoices and PER_USAGE do not gain an explicit close operation from T29. Reopen/cancel/adjustment/discount/due-date/issuance semantics remain outside the locked boundary.
6. Payments remain separate from lifecycle closure: confirmed PIX settlement exists and a closed MANUAL Invoice may still receive valid Payment when financial state permits.
7. The canonical T26 Reception Closing Authority Reconciliation remains **TECHNICALLY RECONCILED / AWAITING HUMAN HOMOLOGATION**. Its protected implementation follows M7-A2-T1.
8. T27 Terminal Outbox Failure Policy remains **PROPOSED / AWAITING HUMAN APPROVAL**. No terminal behavior is authorized until that separate approval.
9. Consumer atomicity remains regression-protected.
10. Static OpenAPI V1 remains independently locked and was not modified by T28-T30; reconciliation against runtime Billing routes remains a controlled contract/documentation gap.

## Controlled next gaps

Current verified boundaries are:

- T26 reception-closing reconciliation — technical reconciliation complete; human homologation pending;
- T27 terminal Outbox `FAILED` / maximum-attempt policy — proposal exists; implementation blocked on human approval;
- static OpenAPI reconciliation — runtime Billing read/MANUAL-close surface must be compared to the independently locked V1 contract without silent mutation;
- Financeiro frontend — technically able to consume the Billing backend but remains a separate product/navigation gate and is not silently authorized by T28-T30.

Frontend expansion must follow reconciled product architecture and existing API/domain authority. It must not invent missing financial lifecycle semantics.

> "Quem pede um, pede bis."
