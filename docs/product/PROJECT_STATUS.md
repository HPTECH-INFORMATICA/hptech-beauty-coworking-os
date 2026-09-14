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
BCOS-M7-A3-T26 ... TECHNICALLY RECONCILED / AWAITING HUMAN HOMOLOGATION
BCOS-M7-A3-T27 ... PROPOSED / AWAITING HUMAN APPROVAL
BCOS-M7-A3-T28 ... HUMAN HOMOLOGATED / LOCKED
BCOS-M7-A3-T29 ... HUMAN HOMOLOGATED / LOCKED
BCOS-M7-A3-T30 ... HUMAN HOMOLOGATED / LOCKED
```

M4/M5 are not retroactively promoted without explicit evidence. M7-A3 remains IN PROGRESS despite locked sub-gates.

## M7-A3 — current financial baseline

### T25 — Accumulated Invoice Materialization

Status: HUMAN HOMOLOGATED / LOCKED.

Covers `ACCUMULATED_OPEN_INVOICE`, WEEKLY / BIWEEKLY / MONTHLY / MANUAL cycles, accumulated identity by historical professional billing contract/cycle, `USAGE_COMPLETION`, deterministic supported `FIXED_CUTOFF_SPLIT`, immutable persisted InvoiceItem evidence, and atomic financial writes + Outbox `PROCESSED`.

Reception-closing financial authority remains M7-A2-T1: overtime strictly after reception closing is auditable temporal evidence but is not materialized as financial OVERTIME.

### T26 — Reception Closing Authority Reconciliation

Status: TECHNICALLY RECONCILED / AWAITING HUMAN HOMOLOGATION.

The implementation/regressions are reconciled with M7-A2-T1. This status is intentionally not promoted by later Billing gates.

### T27 — Terminal Outbox Failure Policy

Status: PROPOSED / AWAITING HUMAN APPROVAL.

The physical Outbox enum already supports `FAILED`, but the terminal maximum-attempt transition remains unimplemented until explicit approval of T27.

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

## Banco de dados

Projeto Neon independente: `hptech-beauty-coworking-os`.

Baseline conhecida: production branch, `neondb`, role `neondb_owner`, PostgreSQL real validated, migrations/integrity according to the project baseline.

Regra permanente: nunca reutilizar, inspecionar ou assumir banco, projeto, branch, credencial ou connection string de outro produto como se pertencesse ao BCOS.

## Quality Gate

`.github/workflows/quality-gate.yml` protects:

- API: Ruff, mypy, pytest, Alembic single-head;
- Worker: Ruff, mypy, pytest;
- Web: strict lint, typecheck, tests, build.

T29/T30 implementation passed the complete implementation gate and the post-merge `main` gate before final homologation reconciliation.

## Débitos controlados

- Frontend product exposure remains narrower than implemented backend/domain capability.
- Financeiro frontend remains a separate product/navigation gate; T28-T30 do not authorize it.
- T26 awaits human homologation.
- T27 awaits human approval before implementation.
- Static/frozen API documentation must be reconciled carefully against implemented Billing runtime routes without silently reopening the independently locked OpenAPI baseline.

## Próxima atividade

Continue M7-A3 from locked T25/T28/T29/T30 baselines without reopening them. Remaining independent decisions are T26 human homologation and T27 terminal Outbox policy approval. Static OpenAPI reconciliation remains a controlled documentary/contract gap, and Financeiro frontend remains a separate product surface gate.

## Regra de Governança

Antes de alteração estrutural: revisar, analisar, verificar, investigar, diagnosticar, comparar com as baselines e avaliar impacto.

Nenhuma etapa implementada torna-se `HUMAN HOMOLOGATED / LOCKED` sem homologação humana explícita. Etapa homologada não é reaberta silenciosamente. Qualquer alteração estrutural exige rastreabilidade.

> "Quem pede um, pede bis."
