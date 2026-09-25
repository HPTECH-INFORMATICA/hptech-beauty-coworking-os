# BCOS — MASTER SYSTEM BASELINE

> "Quem pede um, pede bis."

**Authority purpose:** single consolidated project-state authority for implementation recovery, audit and completion.  
**Audit date:** 2026-09-25  
**Repository:** `HPTECH-INFORMATICA/hptech-beauty-coworking-os`  
**Audited main baseline:** `6e632152917e010f34c398faf1b2b659a9e7b3e4`  
**Status:** SYSTEM AUDIT BASELINE — freeze after reconciliation gate.

## 1. Governance and immutable authorities

The following previously homologated authorities remain immutable and MUST NOT be silently reopened:

- PRD MASTER v1.0 — HUMAN HOMOLOGATED / LOCKED.
- Architecture Freeze v1.2 — HUMAN HOMOLOGATED / LOCKED.
- PostgreSQL DDL v1.2.1 — HOMOLOGATED.
- Database Integrity Test Suite v1.1 — HOMOLOGATED.
- OpenAPI V1 — MATERIALIZED / VALIDATED / LOCKED.
- BCOS-M0.2 Technical Foundation — HUMAN HOMOLOGATED / LOCKED.

Implementation must conform to those authorities. A later implementation, deployment, UI or documentation record cannot overwrite a locked authority.

**Repository evidence gap:** the current `docs/architecture/` directory does not contain the materialized Architecture Freeze v1.2 document, despite current status documents naming it as immutable authority. The complete PRD MASTER v1.0 is likewise not materialized as a canonical file in the current repository tree. This is a traceability defect, not permission to recreate or reinterpret either authority. Recovery must use the homologated historical source, preserving it verbatim.

## 2. Non-negotiable architecture

- Strict multi-tenancy.
- Server-side authentication and authorization.
- `ResourceOccupancy` is physical occupancy authority.
- Booking and Usage are distinct.
- Pricing, Billing and Payment are distinct domains.
- Pricing Snapshot is immutable.
- Billing and Payments are idempotent.
- Transactional Outbox protects critical financial continuity.
- Professional access is own-scope.
- Critical rules never rely only on browser/frontend state.
- PostgreSQL is final authority for critical persistence/invariants.
- BCOS remains technically isolated from other HPTECH PLATFORM products.

## 3. Beginning — foundation audit

### Completed / preserved

- M0.1 — HUMAN HOMOLOGATED / LOCKED.
- M0.2 — HUMAN HOMOLOGATED / LOCKED.
- M1 — HUMAN HOMOLOGATED / LOCKED.
- M2 — HUMAN HOMOLOGATED / LOCKED.
- M3 — HUMAN HOMOLOGATED / LOCKED.
- M4 — implemented; prior gates approved.
- M5 — implemented; prior gates approved.
- M6 — HUMAN HOMOLOGATED / LOCKED.
- Monorepo with Next.js/React/TypeScript, pnpm/Turbo, FastAPI/Python 3.12, SQLAlchemy/Alembic, PostgreSQL/Neon and separate Worker.
- Quality Gate covers API lint/type/tests/Alembic head, Worker lint/type/tests, Web lint/type/tests/build.

### Remaining foundation reconciliation

- Restore the exact historical PRD MASTER v1.0 and Architecture Freeze v1.2 into repository authority without rewriting them.
- Verify all later migrations, API contracts and UI behavior against those recovered immutable sources.
- Do not promote historical “implemented” stages to “human homologated” without explicit evidence.

## 4. Middle — operational product audit

### Implemented

The repository materially contains:

`Availability → Booking → Confirmation → Check-in → Usage → Check-out → USAGE_COMPLETED → Outbox/Worker → Billing → Invoice → PIX/Payment`.

Also present: Units/reception hours; resource categories/resources; professionals; Reception now/agenda; Availability; Booking; Usage/check-in/check-out; Professional own-scope; Billing list/detail; MANUAL accumulated invoice close; PIX confirmation; audit foundation; Transactional Outbox processing/recovery.

### M7 authority

- M7 — IN PROGRESS.
- M7-A1 — PASS.
- M7-A2 — HUMAN HOMOLOGATED / LOCKED.
- M7-A3 — IN PROGRESS.
- T25/T26/T28/T29/T30/T31 — HUMAN HOMOLOGATED / LOCKED.
- T27 — AUTHORITY GAP / IMPLEMENTATION BLOCKED.
- T32 has an ADR in the repository and must be reconciled with status authority before promotion.

T27 remains blocked: physical `FAILED` state does not authorize inventing a maximum retry threshold.

## 5. Commercial product audit — C1 through C7

Authoritative commercial target:

`HPTECH onboarding → tenant activation/configuration → professional access → availability/calendar + price → booking → check-in → usage → check-out → Billing → receipt/payment → tenant administrative finance`.

### C1 — Product authority and identity

**Materially implemented:** PlatformOperator; platform tenant onboarding APIs/UI; tenant lifecycle; first OWNER invitation; tenant membership administration; Neon Auth; JWT/JWKS/issuer verification; access resolver; HPTECH `/platform` console; Reception root authorization gate; `/platform` authentication/authorization layout.

**Current state after C1 security reconciliation:** Web route-family authorization is centralized for Platform, tenant administration, Reception operational surfaces, Finance and Professional portal. Under Neon production identity, tenant context is selected only from authenticated `/api/v1/access`, persisted server-side in an HTTP-only same-site cookie and revalidated before `X-Tenant-Id` is sent. `BCOS_HUMAN_TENANT_ID` remains only in the explicit homologation path. Complete login → access → tenant selection → role shell → logout/revocation production E2E is still not frozen.

### C2 — Tenant master data

Backend foundations exist for units/resources/professionals/users. Complete OWNER/ADMIN master-data UI is not proven. Current `/administracao` tree visibly contains user administration; company, units/hours, categories/resources, professionals and pricing administration require reconciliation before C2 completion.

### C3 — Pricing and commercial calendar

Availability and operational booking exist. Pricing engine/snapshot exists. Complete professional discovery of unit/resource type/calendar/slot/price/review/confirmation is not proven as frozen C3. Pricing administration remains a gap.

### C4 — Administrative finance foundation

Operational Billing/Invoice/Payment is not administrative finance. Financial accounts, cash registers, methods/terms, chart of accounts/costs, payables/receivables and financial movements/settlements are not proven complete.

### C5 — Finance views

Operational `/financeiro` exists for Billing/PIX. Administrative cash flow, reconciliation and audit views are not proven complete.

### C6 — Role-specific shells

HPTECH console, Reception and Professional surfaces exist materially. Tenant OWNER/ADMIN shell is partial. Uniform server-authoritative role/surface enforcement is not proven across every route.

### C7 — Production E2E / human homologation

NOT COMPLETE. Production deployment exists, but the complete commercial journey has not been frozen as end-to-end human-homologated evidence.

## 6. Security and route audit

### Public by design
- `/auth/*`.

### Authenticated resolver
- `/acesso` — authenticated identity entry/access resolution; fail closed.

### Platform authority
- `/platform/*` — current main has a layout requiring session and `platform_destination === "/platform"`.

### Reception root
- `/` — current main requires session plus an access tenant authorized to `/`.

### Route-family enforcement — IMPLEMENTED / awaiting production E2E freeze

Explicit server-side Web gates now cover Platform authority, tenant administration, Reception operational surfaces, Finance and Professional portal. `/auth/*` remains public by design and `/acesso` remains the authenticated access resolver. Tenant selection is revalidated against active access before tenant API calls.

Required invariant:

1. unauthenticated product navigation → `/auth/sign-in`;
2. authenticated unauthorized identity → `/acesso`;
3. platform surface → active PlatformOperator;
4. tenant administration → active OWNER/ADMIN membership for selected tenant;
5. reception operation → authorized operational membership for selected tenant;
6. professional portal → active PROFESSIONAL own-scope membership;
7. no static homologation tenant id as production tenant-selection authority.

## 7. Production audit

Known topology: Web/Vercel; API/Render; Neon PostgreSQL; separate Python Worker by architecture; Resend.

Deployment existence is not completion evidence.

Remaining closure: production E2E evidence for selected-tenant/session propagation and route guards; migration execution ownership; Worker/Outbox deployed-runtime evidence; Web → Auth → API → PostgreSQL → Worker/Outbox → Billing → Payment E2E; tenant isolation/role E2E; retirement of homologation-only production plumbing after the real path is proven.

## 8. TODO audit

Literal indexed repository search for `TODO`, `FIXME`, `XXX` and `HACK` returned no findings. That does NOT mean zero technical debt.

- [ ] Recover/materialize exact PRD MASTER v1.0.
- [ ] Recover/materialize exact Architecture Freeze v1.2.
- [ ] Reconcile T32 with milestone status.
- [ ] Keep T27 blocked until authority exists.
- [x] Centralize Web authentication/authorization guards.
- [x] Remove `BCOS_HUMAN_TENANT_ID` as production tenant-selection authority.
- [x] Implement authoritative tenant selection for multi-membership identities.
- [ ] Complete C2 tenant master-data surfaces.
- [ ] Complete C3 pricing administration and professional calendar/price journey.
- [ ] Complete C4 administrative-finance domain/surfaces without corrupting Billing.
- [ ] Complete C5 finance views/reconciliation.
- [ ] Complete C6 role-specific shells/navigation.
- [ ] Execute C7 production E2E + human homologation.
- [ ] Reconcile Payments runtime/static OpenAPI authority.
- [ ] Prove production migration ownership.
- [ ] Prove deployed Worker/Outbox/Billing continuity.
- [ ] Audit all API endpoints for auth, tenant context, permission and cross-tenant denial.
- [ ] Audit all server actions against destination API authority.
- [ ] Audit frontend authorization failure handling.
- [ ] Audit secrets/config boundaries without exposing values.
- [ ] Audit migrations for single head, tenant keys/FKs/indexes/frozen invariants.
- [ ] Audit tests against security/role matrices and commercial journeys.

## 9. Documentation consolidation rule

From this baseline forward:

- This file is the **single consolidated project-state authority**.
- PRD/Architecture/OpenAPI/ADRs remain immutable source authorities/evidence where applicable.
- Older status/reconciliation/audit documents are historical evidence and MUST NOT independently redefine current state.
- Do not create another competing status/reconciliation/audit/master-plan document.
- Update this file only when implementation evidence changes.
- A completed/homologated item is frozen here only with traceable evidence.
- Missing authority is BLOCKED/UNKNOWN; never invented.

## 10. Definition of finish

BCOS is launch-ready only when C1–C7 acceptance journeys are implemented; protected surfaces are server-authorized; tenant selection is real production authority; production E2E succeeds; tenant isolation/roles are proven; migrations/Worker/Outbox/Billing/Payment continuity is proven; visible business journeys are human-homologated; all non-blocked TODOs are closed; and this baseline is updated to **FINAL / HUMAN HOMOLOGATED / LOCKED**.

Until then:

**ADVANCED IMPLEMENTATION / PRODUCTION DEPLOYED / NOT YET LAUNCH-HOMOLOGATED.**

> "Quem pede um, pede bis."
