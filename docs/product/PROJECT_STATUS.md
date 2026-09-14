# HPTECH Beauty Coworking OS — Project Status

> "Quem pede um, pede bis."

## Projeto

HPTECH Beauty Coworking OS (BCOS), produto da HPTECH PLATFORM.

Repositório local canônico: `C:\HudsonPedro\hptech-beauty-coworking-os`

Repositório remoto: `HPTECH-INFORMATICA/hptech-beauty-coworking-os`

O BCOS mantém isolamento técnico próprio. Integrações com outros produtos ou serviços da HPTECH PLATFORM devem ocorrer somente por contratos explícitos.

## Baselines homologadas

- PRD MASTER v1.0 — HUMAN HOMOLOGATED / LOCKED
- Architecture Freeze v1.2 — HUMAN HOMOLOGATED / LOCKED
- PostgreSQL DDL v1.2.1 — HOMOLOGADO
- Database Integrity Test Suite v1.1 — HOMOLOGADA
- OpenAPI V1 — MATERIALIZADO / VALIDADO / LOCKED
- BCOS-M0.2 Technical Foundation — HUMAN HOMOLOGATED / LOCKED

PRD MASTER v1.0 and Architecture Freeze v1.2 are immutable authorities for implementation. Later reconciliation work must conform code, database, API, tests and documentation to those authorities; it must not reopen or alter them.

## Stack canônica

- Frontend: Next.js + React + TypeScript
- Workspace: pnpm + Turborepo
- Backend: Python 3.12 + FastAPI
- Validation: Pydantic
- Persistence: SQLAlchemy 2.x
- Migrations: Alembic + PostgreSQL
- Database: PostgreSQL / Neon
- Worker: processo Python separado
- Frontend Deploy: Vercel
- API / Worker Deploy: Render
- E-mail: Resend
- Source Control: Git + GitHub

## Princípios não negociáveis

- Zero overlap físico.
- Isolamento multi-tenant rigoroso.
- `ResourceOccupancy` como autoridade física de indisponibilidade.
- Booking e Usage são entidades distintas.
- Pricing, Billing e Payment são domínios distintos.
- Pricing Snapshot é imutável.
- Billing e Payments são idempotentes.
- Transactional Outbox protege eventos financeiros críticos.
- RBAC e autorização são server-side.
- Professional opera sob escopo próprio autorizado.
- Regras críticas nunca dependem somente do frontend.
- Zero Vendor Lock-in.

## Estado oficial consolidado

```text
BCOS-M0.1 ........ HUMAN HOMOLOGATED / LOCKED
BCOS-M0.2 ........ HUMAN HOMOLOGATED / LOCKED
BCOS-M1 .......... HUMAN HOMOLOGATED / LOCKED
BCOS-M2 .......... HUMAN HOMOLOGATED / LOCKED
BCOS-M3 .......... HUMAN HOMOLOGATED / LOCKED
BCOS-M4 .......... IMPLEMENTED / GATES PREVIOUSLY APPROVED
BCOS-M5 .......... IMPLEMENTED / GATES PREVIOUSLY APPROVED
BCOS-M6 .......... HUMAN HOMOLOGATED / LOCKED
BCOS-M7 .......... IN PROGRESS
BCOS-M7-A1 ....... PASS
BCOS-M7-A2 ....... HUMAN HOMOLOGATED / LOCKED
BCOS-M7-A3 ....... IN PROGRESS
BCOS-M7-A3-T25 ... HUMAN HOMOLOGATED / LOCKED
BCOS-M7-A3-T26 ... HUMAN HOMOLOGATED / LOCKED
BCOS-M7-A3-T27 ... AUTHORITY GAP / IMPLEMENTATION BLOCKED
BCOS-M7-A3-T28 ... HUMAN HOMOLOGATED / LOCKED
BCOS-M7-A3-T29 ... HUMAN HOMOLOGATED / LOCKED
BCOS-M7-A3-T30 ... HUMAN HOMOLOGATED / LOCKED
BCOS-M7-A3-T31 ... HUMAN HOMOLOGATED / LOCKED
```

M4/M5 are not retroactively promoted without explicit evidence. M7-A3 remains IN PROGRESS despite locked sub-gates.

## M7-A3 — current financial baseline

### T25 — Accumulated Invoice Materialization

Status: HUMAN HOMOLOGATED / LOCKED.

Covers `ACCUMULATED_OPEN_INVOICE`, WEEKLY / BIWEEKLY / MONTHLY / MANUAL cycles, accumulated identity by historical professional billing contract/cycle, `USAGE_COMPLETION`, deterministic supported `FIXED_CUTOFF_SPLIT`, immutable persisted InvoiceItem evidence, and atomic financial writes + Outbox `PROCESSED`.

Reception-closing financial authority remains M7-A2-T1: overtime strictly after reception closing is auditable temporal evidence but is not materialized as financial OVERTIME.

### T26 — Reception Closing Authority Reconciliation

Status: HUMAN HOMOLOGATED / LOCKED.

T26 reconciles the repository to the immutable M7-A2-T1 reception-closing authority. The implementation/regressions already follow that authority: overtime strictly after reception closing is not financially materialized, a closed reception day generates no OVERTIME charge, and the conflicting later T11 wording is superseded only for this financial interpretation.

### T27 — Terminal Outbox Failure Policy

Status: AUTHORITY GAP / IMPLEMENTATION BLOCKED.

The physical Outbox enum already supports `FAILED`, and the earlier approved Outbox contracts intentionally reserve terminal retry/failure policy for a separate decision. The existing T27 proposal suggests a maximum of five processing attempts, but that threshold is not established by the earlier locked Outbox contracts. Because PRD/Architecture authorities are immutable and must not be invented or modified, no terminal threshold will be implemented until it can be traced to an already-approved authority.

### T28 — Billing Operational Read Boundary

Status: HUMAN HOMOLOGATED / LOCKED.

T28 provides tenant-scoped, read-only operational Billing endpoints `GET /api/v1/invoices` and `GET /api/v1/invoices/{invoice_id}`, protected by existing `OPERATIONS` permission.

### T29 — Invoice Lifecycle Write Boundary

Status: HUMAN HOMOLOGATED / LOCKED.

T29 defines and implements the explicit MANUAL accumulated Invoice closure boundary. Only MANUAL accumulated invoices with the approved identity are eligible; first closure is allowed from OPEN/PARTIALLY_PAID, uses tenant-scoped row locking and persists immutable UTC `manual_closed_at`. PAID/CANCELLED, automatic-cycle and PER_USAGE close requests fail closed. Closure does not rewrite InvoiceItems/totals, settle Payment, create successor Invoice, or introduce generic Invoice CRUD.

### T30 — MANUAL Invoice Closure Audit Contract

Status: HUMAN HOMOLOGATED / LOCKED.

T30 locks transactional audit evidence for first successful MANUAL close: `INVOICE_MANUAL_CLOSED` / `INVOICE`, tenant and actor from authenticated TenantContext, minimal metadata with persisted UTC close instant and financial status, no duplicate audit on idempotent retry and no new Outbox event.

T29/T30 implementation baseline: `f4a1ba22f5393173c7e8fda8d73663ddd0544095`. PR Quality Gate #91 and post-merge main Quality Gate #93 passed on 2026-09-14 before final homologation reconciliation.

### T31 — Static OpenAPI Billing Reconciliation

Status: HUMAN HOMOLOGATED / LOCKED.

T31 reconciles the independently locked static OpenAPI V1 with the already homologated runtime T28/T29/T30 Billing boundary, including the MANUAL close command and runtime Invoice projections. Implementation was integrated at `7be0ad8281ec583bbd768926b9ac11ac6c9c173b`; final homologation record was integrated at `4dea93f7fdd4d6ecab18cce1ada50636603c5868`, with post-merge Quality Gate #111 successful.

## Banco de dados

Projeto Neon independente: `hptech-beauty-coworking-os`.

Baseline conhecida: production branch, `neondb`, role `neondb_owner`, PostgreSQL real validated, migrations/integrity according to the project baseline.

Regra permanente: nunca reutilizar, inspecionar ou assumir banco, projeto, branch, credencial ou connection string de outro produto como se pertencesse ao BCOS.

## Quality Gate

`.github/workflows/quality-gate.yml` protects:

- API: Ruff, mypy, pytest, Alembic single-head;
- Worker: Ruff, mypy, pytest;
- Web: strict lint, typecheck, tests, build.

T31 final homologation record passed post-merge `main` Quality Gate #111 on 2026-09-14.

## Débitos controlados

- Frontend product exposure remains narrower than implemented backend/domain capability.
- Financeiro frontend remains a separate product/navigation gap to reconcile against the immutable product authority; T28-T31 do not themselves define a new product surface.
- T27 terminal Outbox policy remains blocked at the unresolved maximum-attempt authority boundary; no threshold may be invented.

## Próxima atividade

Continue M7-A3 reconciliation from locked T25/T26/T28/T29/T30/T31 baselines. Preserve PRD MASTER v1.0 and Architecture Freeze v1.2 unchanged. Audit remaining implementation/product-surface gaps against those immutable authorities. T27 must remain fail-closed at its unresolved authority boundary rather than receiving an invented terminal threshold.

## Regra de Governança

Antes de alteração estrutural: revisar, analisar, verificar, investigar, diagnosticar, comparar com as baselines e avaliar impacto.

PRD MASTER v1.0 and Architecture Freeze v1.2 are never reopened or altered. Implementation must conform to them. Etapa homologada não é reaberta silenciosamente. Qualquer alteração estrutural exige rastreabilidade.

> "Quem pede um, pede bis."
