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
```

M4/M5 are not retroactively promoted without explicit evidence. M7-A3 remains IN PROGRESS despite locked sub-gates.

## M7-A3 — current financial baseline

### T25 — Accumulated Invoice Materialization

Status: HUMAN HOMOLOGATED / LOCKED.

Covers `ACCUMULATED_OPEN_INVOICE`, WEEKLY / BIWEEKLY / MONTHLY / MANUAL cycles, accumulated identity by historical professional billing contract/cycle, `USAGE_COMPLETION`, deterministic supported `FIXED_CUTOFF_SPLIT`, immutable persisted InvoiceItem evidence, and atomic financial writes + Outbox `PROCESSED`.

Reception-closing financial authority remains M7-A2-T1: overtime strictly after reception closing is auditable temporal evidence but is not materialized as financial OVERTIME.

### T26 — Reception Closing Authority Reconciliation

Status: TECHNICALLY RECONCILED / AWAITING HUMAN HOMOLOGATION.

The implementation/regressions are reconciled with M7-A2-T1. This status is intentionally not promoted by T28 homologation.

### T27 — Terminal Outbox Failure Policy

Status: PROPOSED / AWAITING HUMAN APPROVAL.

The physical Outbox enum already supports `FAILED`, but the terminal maximum-attempt transition remains unimplemented until explicit approval of T27.

### T28 — Billing Operational Read Boundary

Status: HUMAN HOMOLOGATED / LOCKED.

Contract: `docs/adr/M7-A3-T28-billing-operational-read-boundary-contract.md`.

Merged implementation baseline: `c5e7f01bdafefe7b502e6e88f1cb9ee7d7b5ce31`.

T28 provides tenant-scoped, read-only operational Billing endpoints:

- `GET /api/v1/invoices`;
- `GET /api/v1/invoices/{invoice_id}`.

The boundary requires existing `OPERATIONS` permission, exposes persisted Invoice/InvoiceItem evidence and deterministic confirmed-payment/remaining projections, uses deterministic pagination, and introduces no migration, frontend change or Billing write endpoint.

Human implementation approval and final human homologation were explicitly granted on 2026-09-14 after technical verification. T28 is locked and must not be silently reopened.

## Invoice lifecycle boundary

T28 deliberately leaves Billing writes unresolved. The schema contains `manual_closed_at`, while T25 does not authorize the worker to close/rotate/reopen MANUAL accumulated invoices. Who may close a MANUAL invoice, under what conditions, what mutations remain legal afterward, and whether automatic-cycle invoices need an explicit close/issue transition require a separate traceable contract before implementation.

## Banco de dados

Projeto Neon independente: `hptech-beauty-coworking-os`.

Baseline conhecida: production branch, `neondb`, role `neondb_owner`, PostgreSQL real validated, migrations/integrity according to the project baseline.

Regra permanente: nunca reutilizar, inspecionar ou assumir banco, projeto, branch, credencial ou connection string de outro produto como se pertencesse ao BCOS.

## Quality Gate

`.github/workflows/quality-gate.yml` protects:

- API: Ruff, mypy, pytest, Alembic single-head;
- Worker: Ruff, mypy, pytest;
- Web: strict lint, typecheck, tests, build.

T28 implementation passed the complete PR gate and the post-merge `main` gate before human homologation.

## Débitos controlados

- Frontend product exposure remains narrower than implemented backend/domain capability.
- Financeiro frontend is not part of T28 and remains a separate product/navigation gate.
- Invoice lifecycle writes remain unresolved by design.
- T26 awaits human homologation.
- T27 awaits human approval before implementation.
- Static/frozen API documentation must be reconciled carefully against T28 without silently reopening an independently locked OpenAPI baseline.

## Próxima atividade

Continue M7-A3 from the locked T25/T28 baselines without reopening them. Audit the static OpenAPI contract and Invoice lifecycle authority; documentary reconciliation may proceed where factual, while new lifecycle/write semantics require a separate proposed gate. T26/T27 retain their independent pending human decisions.

## Regra de Governança

Antes de alteração estrutural: revisar, analisar, verificar, investigar, diagnosticar, comparar com as baselines e avaliar impacto.

Nenhuma etapa implementada torna-se `HUMAN HOMOLOGATED / LOCKED` sem homologação humana explícita. Etapa homologada não é reaberta silenciosamente. Qualquer alteração estrutural exige rastreabilidade.

> "Quem pede um, pede bis."
