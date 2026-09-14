# HPTECH Beauty Coworking OS

Sistema operacional SaaS B2B multi-tenant para a operação de coworkings de beleza e estética, produto da HPTECH PLATFORM.

> "Quem pede um, pede bis."

## Status

O BCOS está em desenvolvimento funcional avançado. Identity/Tenancy/RBAC, Units/Resources/Professionals, Availability, Booking/Usage, Pricing, Billing materialization, Payments e Transactional Outbox possuem implementação relevante no repositório.

O trabalho ativo está em **BCOS-M7 — Outbox / Billing**. **M7-A3-T25 — Accumulated Invoice Materialization**, **T26 — Reception Closing Authority Reconciliation**, **T28 — Billing Operational Read Boundary**, **T29 — Invoice Lifecycle Write Boundary**, **T30 — MANUAL Invoice Closure Audit Contract** e **T31 — Static OpenAPI Billing Reconciliation** estão `HUMAN HOMOLOGATED / LOCKED`.

T28 disponibiliza leitura Billing operacional tenant-scoped. T29/T30 acrescentam a única mutação de lifecycle autorizada neste recorte: fechamento explícito de Invoice acumulada MANUAL, protegido por `OPERATIONS`, idempotente e auditado transacionalmente. T31 reconciliou esse runtime com o OpenAPI estático sem criar novas semânticas. Isso não autoriza generic Invoice CRUD.

**T27 — Terminal Outbox Failure Policy** permanece em `AUTHORITY GAP / IMPLEMENTATION BLOCKED`: o enum físico já possui `FAILED`, mas os contratos Outbox anteriormente aprovados deixaram deliberadamente indefinidos o máximo de tentativas e o threshold terminal. Nenhum valor será inventado fora da autoridade já aprovada.

O estado detalhado e rastreável está em `docs/product/PROJECT_STATUS.md`; a auditoria de superfície está em `docs/product/PRODUCT_RECONCILIATION.md`.

## Baselines homologadas

- PRD MASTER v1.0 — HUMAN HOMOLOGATED / LOCKED
- Architecture Freeze v1.2 — HUMAN HOMOLOGATED / LOCKED
- PostgreSQL DDL v1.2.1 — HOMOLOGADO
- Database Integrity Test Suite v1.1 — HOMOLOGADA
- OpenAPI V1 — MATERIALIZADO / VALIDADO / LOCKED
- BCOS-M0.2 Technical Foundation — HUMAN HOMOLOGATED / LOCKED
- M7-A3-T25 — HUMAN HOMOLOGATED / LOCKED
- M7-A3-T26 — HUMAN HOMOLOGATED / LOCKED
- M7-A3-T28 — HUMAN HOMOLOGATED / LOCKED
- M7-A3-T29 — HUMAN HOMOLOGATED / LOCKED
- M7-A3-T30 — HUMAN HOMOLOGATED / LOCKED
- M7-A3-T31 — HUMAN HOMOLOGATED / LOCKED

PRD MASTER v1.0 e Architecture Freeze v1.2 são autoridades imutáveis de implementação. Código, banco, API, testes e documentação devem ser reconciliados a elas; essas baselines não são reabertas ou alteradas durante o desenvolvimento.

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

A baseline T28 permite leitura tenant-scoped de Invoice/InvoiceItems e projeção determinística de pagamentos confirmados/saldo restante.

T29/T30 permitem explicitamente fechar somente uma Invoice acumulada MANUAL dentro da identidade e estados financeiros aprovados. O fechamento persiste `manual_closed_at`, não reescreve itens/totais, não liquida Payment e registra uma única auditoria `INVOICE_MANUAL_CLOSED` na primeira mutação. Repetição é idempotente e não duplica auditoria.

T31 mantém o OpenAPI estático reconciliado com essa superfície runtime. Automatic-cycle e PER_USAGE não recebem close explícito. Reopen, cancelamento, ajustes/descontos, vencimento/emissão e generic Invoice CRUD permanecem fora desse contrato.

## Outbox

O worker possui claim concorrente seguro, retry com backoff, sanitização de erro, recuperação de `PROCESSING` abandonado e runtime sequencial já implementados. O terminal `FAILED` permanece fail-closed enquanto o máximo de tentativas não estiver sustentado por autoridade previamente aprovada; a existência física do enum não autoriza inventar o threshold.

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

A reconciliação T26/T31 e de autoridade foi integrada no commit `a7a2a8c3894e0a7289df230c778fd637b33d01f7`; o Quality Gate pós-merge `#117` foi concluído com sucesso em 2026-09-14.

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

PRD MASTER v1.0 e Architecture Freeze v1.2 são imutáveis. Implementação deve conformar-se a elas. Etapas homologadas não são reabertas silenciosamente e decisões ausentes não são inventadas.

## Isolamento do produto

O BCOS é um produto da HPTECH PLATFORM, com repositório, banco e arquitetura próprios. Integrações com outros produtos/serviços ocorrem somente por contratos explícitos.

---

> "Quem pede um, pede bis."
