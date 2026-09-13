# HPTECH Beauty Coworking OS

Sistema operacional SaaS B2B multi-tenant para a operação de coworkings de beleza e estética, produto da HPTECH PLATFORM.

> "Quem pede um, pede bis."

## Status

O BCOS está em desenvolvimento funcional avançado. As fundações de identidade/tenancy/RBAC, unidades/recursos/profissionais, disponibilidade, Booking/Usage, Pricing e a infraestrutura de Billing/Transactional Outbox já possuem implementação no repositório.

O trabalho ativo está em **BCOS-M7 — Outbox / Billing**. O contrato **M7-A3-T25 — Accumulated Invoice Materialization** está `HUMAN HOMOLOGATED / LOCKED`. A reconciliação **M7-A3-T26 — Reception Closing Authority Reconciliation** está tecnicamente materializada e em validação/homologação, preservando M7-A2-T1 como autoridade V1: tempo de overtime estritamente posterior ao fechamento da recepção não gera cobrança financeira de `OVERTIME`.

O estado detalhado e rastreável do projeto está em `docs/product/PROJECT_STATUS.md`.

## Baselines homologadas

- PRD MASTER v1.0 — HUMAN HOMOLOGATED / LOCKED
- Architecture Freeze v1.2 — HUMAN HOMOLOGATED / LOCKED
- PostgreSQL DDL v1.2.1 — HOMOLOGADO
- Database Integrity Test Suite v1.1 — HOMOLOGADA
- OpenAPI V1 — MATERIALIZADO / VALIDADO / LOCKED
- BCOS-M0.2 Technical Foundation — HUMAN HOMOLOGATED / LOCKED

## Arquitetura central

- Multi-tenant rigoroso e autorização server-side.
- `ResourceOccupancy` é a autoridade física contra overlap.
- Booking e Usage são entidades distintas.
- Pricing, Billing e Payment permanecem domínios distintos.
- Pricing Snapshot é imutável.
- Billing e Payments são idempotentes.
- Transactional Outbox protege a continuidade financeira após `USAGE_COMPLETED`.
- Regras de recepção, uso real, overtime e ciclos de Billing são resolvidas no backend/worker, nunca somente no frontend.
- PostgreSQL é a autoridade final para invariantes físicas e identidades concorrentes críticas.
- Zero Vendor Lock-in permanece princípio de arquitetura.

## Fluxo operacional

O domínio implementado evolui pelo fluxo:

`Availability → Booking → Usage real → Checkout → USAGE_COMPLETED → Outbox → Pricing/Billing → Invoice/InvoiceItems → Payment`

A interface web ainda não expõe toda a amplitude funcional já existente no domínio/backend. Essa diferença é tratada pela Product Reconciliation Gate e não deve ser confundida com ausência dos módulos de domínio.

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

O workflow `.github/workflows/quality-gate.yml` valida o monorepo em três eixos:

- API: Ruff, mypy, pytest e Alembic single-head;
- Worker: Ruff, mypy e pytest;
- Web: lint estrito, typecheck, testes e build.

Mudanças funcionais e correções de arquitetura devem permanecer verdes nesse gate antes de promoção de baseline.

## Estrutura

- `apps/web` — frontend web.
- `services/api` — backend/API.
- `services/worker` — consumidor Outbox e processamento financeiro assíncrono.
- `packages/domain` — conceitos compartilhados quando aplicável.
- `packages/contracts` — contratos compartilhados.
- `packages/ui` — componentes/design system.
- `database/migrations` — migrations versionadas.
- `database/tests` — testes de integridade do banco.
- `database/seeds` — dados de desenvolvimento.
- `docs/product` — estado e documentação do produto.
- `docs/architecture` — arquitetura e baselines.
- `docs/api` — contratos de API.
- `docs/adr` — Architecture Decision Records.
- `infra` — infraestrutura.
- `scripts` — automações do projeto.
- `tests` — testes de nível sistêmico.

## Governança

Antes de alteração estrutural: revisar, analisar, verificar, investigar, diagnosticar, comparar com as baselines e avaliar impacto.

Nenhuma implementação se torna `HUMAN HOMOLOGATED / LOCKED` sem homologação humana explícita.

Etapas homologadas não são reabertas silenciosamente. Mudanças estruturais exigem rastreabilidade, migration ou ADR conforme o impacto.

## Isolamento do produto

O BCOS é um produto da HPTECH PLATFORM, mas mantém repositório, banco e arquitetura próprios. Integrações com outros produtos ou serviços devem ocorrer por contratos explícitos; bancos, credenciais e estado interno de outro produto nunca devem ser assumidos como pertencentes ao BCOS.

---

> "Quem pede um, pede bis."
