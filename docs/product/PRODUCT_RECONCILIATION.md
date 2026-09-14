# BCOS — Product Reconciliation Gate

> "Quem pede um, pede bis."

**Status:** ACTIVE AUDIT / NOT A HOMOLOGATION RECORD

This matrix reconciles the product surface against the actual repository. It does not promote any milestone to HUMAN HOMOLOGATED / LOCKED and does not reopen locked baselines.

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
| Billing / Invoice | PER_USAGE and ACCUMULATED_OPEN_INVOICE materialization implemented; T25 locked; T28 read boundary locked | Invoice, InvoiceItem, billing contract/cycle schema through migration 0007 | `GET /api/v1/invoices` and `GET /api/v1/invoices/{invoice_id}` implemented tenant-scoped/read-only | No Financeiro/Billing route | Worker materialization plus T28 service/router regression tests | M7-A1/A2/A3/T25/T28 | CORE + OPERATIONAL READ API IMPLEMENTED; Financeiro UI and lifecycle writes remain separate gaps |
| Payments | Confirmed PIX service implemented with idempotency and Invoice status recomputation | Payments persisted | Payments router included | No payment/receivables UI | API payment tests exist | M7 contracts contain historical non-goal wording in places | API IMPLEMENTED; frontend exposure/document reconciliation incomplete |
| Outbox Worker | Claim/retry/recovery/runtime and USAGE_COMPLETED dispatch implemented | Outbox persisted with processing recovery fields; `FAILED` exists physically | Internal worker concern | No UI required for processing itself | Worker suite + consumer rollback/retry regression | M7-A3; T27 proposed | IMPLEMENTED RETRY/RECOVERY; terminal FAILED policy awaits T27 human approval |
| Reception OS | Domain building blocks exist across bookings/usages/resources/professionals and Billing read | Existing operational/financial schema | Multiple operational routers exist | Current frontend remains a narrow reception summary | Frontend page test plus backend suites | Product framing documented | PARTIAL PRODUCT SURFACE — largest visible delivery gap |
| Professional Portal | Own-scope authorization exists in backend | Uses tenant/professional records | Supporting APIs exist; T28 correctly denies coworking-wide Billing read | No dedicated portal route/shell | Backend authorization tests exist | PRD/M1/T28 | NOT EXPOSED IN FRONTEND |
| Owner Dashboard | Supporting operational/financial data exists | Existing schema | Billing read now available; no dedicated dashboard aggregation API | No Owner Dashboard route | No dedicated dashboard test surface identified | PRD/product intent/T28 | NOT IMPLEMENTED AS PRODUCT SURFACE |
| Production | Health endpoint, quality workflow and deployment stack documented | Neon baseline documented | FastAPI executable | Next.js executable | Quality Gate covers API/Worker/Web | PROJECT_STATUS/README | ENGINEERING FOUNDATION PRESENT; production-readiness/deployment gate remains separate |

## Reconciliation findings

1. The repository is not a skeleton: substantial operational, pricing, billing, payment and Outbox behavior exists in backend/domain/database layers.
2. The Next.js product surface remains materially narrower than the implemented backend.
3. The Billing API asymmetry identified by the earlier audit was closed by T28: the FastAPI application now exposes tenant-scoped, read-only Invoice list/detail endpoints. T28 is HUMAN HOMOLOGATED / LOCKED. No Financeiro frontend was authorized or implemented by T28.
4. T28 intentionally did not define Invoice lifecycle writes. `manual_closed_at` exists physically, while T25 deliberately leaves MANUAL close/rotate/reopen outside worker authority. That lifecycle remains a genuine separate contract boundary.
5. Payments are further ahead than some historical contract non-goal wording suggests: confirmed PIX settlement exists. Historical ADR text remains historical unless explicitly superseded.
6. The canonical `M7-A3-T26 — Reception Closing Authority Reconciliation` remains **TECHNICALLY RECONCILED / AWAITING HUMAN HOMOLOGATION**. Its protected implementation follows M7-A2-T1: overtime strictly after reception closing remains auditable temporal evidence but does not materialize financial `OVERTIME`.
7. `M7-A3-T27 — Terminal Outbox Failure Policy Contract` remains **PROPOSED / AWAITING HUMAN APPROVAL**. No terminal behavior is authorized until that separate approval.
8. Consumer atomicity is regression-protected: processing failure rolls back processing and persists retry separately; no duplicate lifecycle change is required.

## Controlled next gaps

The next M7-A3 implementation decision must come from an approved contract, not generic product expectations. Current verified boundaries are:

- T26 reception-closing reconciliation — technical reconciliation complete; human homologation pending;
- T27 terminal Outbox `FAILED` / maximum-attempt policy — proposal exists; implementation blocked on human approval;
- Invoice lifecycle authority — manual closing and any explicit automatic-cycle close/issue semantics remain unresolved and require a separate traceable contract before write APIs;
- Financeiro frontend — now technically possible to consume the locked T28 read boundary, but remains a separate product/navigation gate and is not silently authorized by T28.

Frontend expansion must follow reconciled product architecture and existing API/domain authority. It must not invent missing financial lifecycle semantics.

> "Quem pede um, pede bis."
