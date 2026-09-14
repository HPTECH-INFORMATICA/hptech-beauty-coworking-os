# HPTECH Beauty Coworking OS

Sistema operacional SaaS B2B multi-tenant para a operação de coworkings de beleza e estética, produto da HPTECH PLATFORM.

> "Quem pede um, pede bis."

## Status

O BCOS está em desenvolvimento funcional avançado. Identity/Tenancy/RBAC, Units/Resources/Professionals, Availability, Booking/Usage, Pricing, Billing materialization, Payments e Transactional Outbox possuem implementação relevante no repositório.

O trabalho ativo está em **BCOS-M7 — Outbox / Billing**. **M7-A3-T25 — Accumulated Invoice Materialization** e **M7-A3-T28 — Billing Operational Read Boundary** estão `HUMAN HOMOLOGATED / LOCKED`.

T28 disponibiliza a fronteira Billing operacional somente leitura por `GET /api/v1/invoices` e `GET /api/v1/invoices/{invoice_id}`, tenant-scoped e protegida por `OPERATIONS`. Isso fecha o gap de leitura API de Invoice sem autorizar Financeiro frontend ou novas mutações financeiras.

**T26 — Reception Closing Authority Reconciliation** permanece `TECHNICALLY RECONCILED / AWAITING HUMAN HOMOLOGATION`. **T27 — Terminal Outbox Failure Policy** permanece `PROPOSED / AWAITING HUMAN APPROVAL`.

O estado detalhado e rastreável está em `docs/product/PROJECT_STATUS.md`; a auditoria de superfície está em `docs/product/PRODUCT_RECONCILIATION.md`.

## Baselines homologadas

- PRD MASTER v1.0 — HUMAN HOMOLOGATED / LOCKED
- Architecture Freeze v1.2 — HUMAN HOMOLOGATED / LOCKED
- PostgreSQL DDL v1.2.1 — HOMOLOGADO
- Database Integrity Test Suite v1.1 — HOMOLOGADA
- OpenAPI V1 — MATERIALIZADO / VALIDADO / LOCKED
- BCOS-M0.2 Technical Foundation — HUMAN HOMOLOGATED / LOCKED
- M7-A3-T25 — HUMAN HOMOLOGATED / LOCKED
- M7-A3-T28 — HUMAN HOMOLOGATED / LOCKED

## Arquitetura central

- Multi-tenant rigoroso e autorização server-side.
- `ResourceOccupancy` é a autoridade física contra overlap.
- Booking e Usage são entidades distintas.
- Pricing, Billing e Payment permanecem domínios distintos.
- Pricing Snapshot é imutável.
- Billing e Payments são idempotentes.
- Transactional Outbox protege continuidade financeira após `USAGE_COMPLETED`.
- Regras de recepção, uso real, overtime e ciclos de Billing são resolvidas no backend/worker, nunca somente no frontend.
- PostgreSQL é autoridade final para invariantes físicas e identidades concorrentes críticas.
- Zero Vendor Lock-in permanece princípio de arquitetura.

## Fluxo operacional

`Availability → Booking → Usage real → Checkout → USAGE_COMPLETED → Outbox → Pricing/Billing → Invoice/InvoiceItems → Payment`

A interface web ainda não expõe toda a amplitude funcional do backend. A Product Reconciliation Gate trata essa diferença sem confundi-la com ausência dos domínios já implementados.

## Billing operacional

A baseline T28 homologada permite leitura tenant-scoped de Invoice/InvoiceItems e projeção determinística de pagamentos confirmados/saldo restante. Ela não autoriza fechar/reabrir/cancelar Invoice, definir `manual_closed_at`, editar itens, criar ajustes/descontos, definir vencimento ou contornar o fluxo de Payment.

O lifecycle de fechamento de Invoice acumulada continua sendo uma fronteira separada que exige contrato rastreável antes de qualquer write API.

## Stack

- Frontend: Next.js + React + TypeScript
- Workspace: pnpm + Turborepo
- Backend: Python 3.12 + FastAPI + Pydantic + SQLAlchemy
- Worker: Python
- Database: PostgreSQL / Neon
- Migrations: Alembic
- Frontend Deploy: Vercel
- API / Worker Deploy: Render
- E-mail: Resend
- Source Control: Git + GitHub

## Quality Gate

`.github/workflows/quality-gate.yml` valida:

- API: Ruff, mypy, pytest e Alembic single-head;
- Worker: Ruff, mypy e pytest;
- Web: lint estrito, typecheck, testes e build.

Mudanças funcionais e correções de arquitetura devem permanecer verdes antes de promoção de baseline.

## Estrutura

- `apps/web` — frontend web.
- `services/api` — backend/API.
- `services/worker` — consumidor Outbox e processamento financeiro assíncrono.
- `packages/domain` — domínio compartilhado quando aplicável.
- `packages/contracts` — contratos compartilhados.
- `packages/ui` — componentes/design system.
- `database/migrations` — migrations versionadas.
- `database/tests` — integridade do banco.
- `database/seeds` — dados de desenvolvimento.
- `docs/product` — estado e reconciliação do produto.
- `docs/architecture` — arquitetura/baselines.
- `docs/api` — contratos de API.
- `docs/adr` — decisões rastreáveis.
- `infra`, `scripts`, `tests` — infraestrutura, automação e testes sistêmicos.

## Governança

Antes de alteração estrutural: revisar, analisar, verificar, investigar, diagnosticar, comparar com baselines e avaliar impacto.

Nenhuma implementação se torna `HUMAN HOMOLOGATED / LOCKED` sem homologação humana explícita. Etapas homologadas não são reabertas silenciosamente.

## Isolamento do produto

O BCOS é um produto da HPTECH PLATFORM, com repositório, banco e arquitetura próprios. Integrações com outros produtos/serviços ocorrem somente por contratos explícitos.

---

> "Quem pede um, pede bis."
