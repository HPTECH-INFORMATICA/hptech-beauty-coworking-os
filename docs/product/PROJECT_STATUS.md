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
BCOS-M7-A3-T25 ... IMPLEMENTED / QUALITY GATE PASS / AWAITING HUMAN HOMOLOGATION
```

Este documento não promove retroativamente M4 ou M5 a `HUMAN HOMOLOGATED / LOCKED` sem evidência explícita de homologação. Ele apenas remove o antigo estado documental que dizia que essas implementações ainda não estavam autorizadas, pois o repositório já avançou além delas.

## Marcos homologados relevantes

### BCOS-M0.1 — Repository Foundation

Status: HUMAN HOMOLOGATED / LOCKED.

Fundação independente do repositório estabelecida e homologada.

### BCOS-M0.2 — Technical Foundation

Status: HUMAN HOMOLOGATED / LOCKED.

Inclui toolchain Node/pnpm/Turbo, ambiente Python, qualidade backend/frontend, skeleton das aplicações, database executable baseline, PostgreSQL real e OpenAPI V1.

Marcos Git relevantes:

- `52ba61a` — database executable baseline
- `f022133` — real PostgreSQL baseline
- `cc1bf4a` — OpenAPI v1 contract

### BCOS-M1 — Identity / Tenancy / RBAC

Status: HUMAN HOMOLOGATED / LOCKED.

Marco Git: `19e0c28`.

Baseline inclui tenant context server-side, memberships tenant-scoped, RBAC OWNER / ADMIN / RECEPTION / PROFESSIONAL e own-scope de Professional.

### BCOS-M2 — Units / Resources / Professionals

Status: HUMAN HOMOLOGATED / LOCKED.

Marcos Git:

- `800b16e`
- `f160a47`

Baseline inclui Units, Reception Hours, Resource Categories, Resources, Professionals, serviços tenant-scoped e alinhamento HTTP/OpenAPI.

### BCOS-M3 — ResourceOccupancy / Availability

Status: HUMAN HOMOLOGATED / LOCKED.

Marco Git: `96bdfe5`.

`ResourceOccupancy` permanece a autoridade física definitiva; intervalo canônico `[)`; PostgreSQL `EXCLUDE USING gist` permanece a autoridade final contra overlap; Availability é consulta preventiva e não reserva recurso.

### BCOS-M4 — Booking / Pricing Contracts

Estado documental reconciliado: implementação existente no repositório; não está mais em fase de “implementação não autorizada”.

Gates registrados incluem M4-A1 a M4-A6 PASS/LOCKED. Booking não recebe Pricing Snapshot do cliente; snapshot é obrigatório e imutável; Pricing permanece domínio distinto; `ResourceOccupancy` continua autoridade contra overlap.

### BCOS-M6

Status: HUMAN HOMOLOGATED / LOCKED.

Marco Git homologado: `527acda53f5dc0f9fcf7b23aa8e4f2d9c444cb86`.

### BCOS-M7 — Outbox / Billing

Status geral: IN PROGRESS.

M7-A1 Physical Billing Baseline — PASS.

M7-A2 Frozen Contract / Billing Boundary — HUMAN HOMOLOGATED / LOCKED. Marco registrado: `3a65ba4`.

M7-A3 estabelece o consumidor Outbox e a materialização Billing. O contrato aprovado mantém claim curto e transacional, `FOR UPDATE SKIP LOCKED`, processamento de no máximo um evento por iteração, recuperação por `processing_started_at`, e processamento financeiro + `PROCESSED` atômicos na mesma transação.

## M7-A3-T25 — Accumulated Invoice Materialization

Status: IMPLEMENTED / QUALITY GATE PASS / AWAITING HUMAN HOMOLOGATION.

Contrato: `docs/adr/M7-A3-T25-accumulated-invoice-materialization-contract.md`.

A implementação atual cobre `ACCUMULATED_OPEN_INVOICE`, ciclos WEEKLY / BIWEEKLY / MONTHLY / MANUAL, identidade acumulada por contrato/ciclo, `USAGE_COMPLETION`, e materialização determinística de `FIXED_CUTOFF_SPLIT` para efeitos temporais suportados.

Regras preservadas:

- Unit IANA timezone define fronteiras locais; persistência é UTC.
- Instante exatamente no cutoff pertence ao novo ciclo.
- MONTHLY faz clamp para o último dia do mês quando necessário.
- MANUAL não é fechado/rotacionado automaticamente pelo worker.
- `BASE_LEASE` não é automaticamente dividido ou rateado por cruzar cutoff.
- OVERTIME pode ser segmentado somente quando a evidência temporal e monetária aprovada permite segmentação determinística.
- Segmentação incompatível ou não determinística falha fechada.
- Mais de um cutoff por efeito temporal permanece fora do V1 T25.
- InvoiceItems segmentados preservam identidade temporal e idempotência.
- Totais são derivados dos InvoiceItems persistidos.
- Escritas financeiras e Outbox `PROCESSED` permanecem atômicos.

Quality Gate de implementação T25 verificado no run `34766462286`, commit `644b8b7fe0d9fa6e17be1460dce06d5abb63cf7a`:

- API — PASS
- Worker — PASS
- Web — PASS
- Ruff — PASS
- mypy — PASS
- pytest — PASS
- Alembic single-head — PASS
- frontend lint/typecheck/tests/build — PASS

O registro técnico do T25 foi atualizado após esse gate. A homologação humana continua separada e não é autodeclarada por este documento.

## Banco de dados

Projeto Neon independente: `hptech-beauty-coworking-os`.

Baseline conhecida:

- Branch Neon: production
- Database: neondb
- Role: neondb_owner
- PostgreSQL real validado
- migrations aplicadas conforme baseline do projeto
- integridade física validada

Regra permanente: nunca reutilizar, inspecionar ou assumir banco, projeto, branch, credencial ou connection string de outro produto como se pertencesse ao BCOS.

## Quality Gate do repositório

`.github/workflows/quality-gate.yml` protege os três eixos do monorepo:

- API: Ruff, mypy, pytest e Alembic single-head;
- Worker: Ruff, mypy e pytest;
- Web: lint estrito, typecheck, testes e build.

Correções de arquitetura e Billing devem permanecer cobertas por esse gate antes de promoção de baseline.

## Débitos controlados

- A exposição funcional do frontend ainda é menor do que a arquitetura/domínio já implementados no backend; isso deve ser tratado como reconciliação de produto, sem inventar módulos fora do PRD/Architecture Freeze.
- README e demais documentos antigos podem conter estado histórico defasado e devem ser reconciliados contra implementação real, ADRs e homologações antes de serem tratados como autoridade de estado.
- Integrações externas futuras continuam fora da baseline até contrato explícito.

## Próxima atividade

Fechar o gate de homologação humana do M7-A3-T25 somente após confirmação humana explícita. Até essa confirmação, o estado técnico permanece `IMPLEMENTED / QUALITY GATE PASS / AWAITING HUMAN HOMOLOGATION`.

Em paralelo, continuar a Product Reconciliation Gate para localizar e corrigir deriva documental/técnica sem reabrir silenciosamente baselines homologadas.

## Regra de Governança

Antes de alteração estrutural: revisar, analisar, verificar, investigar, diagnosticar, comparar com as baselines e avaliar impacto.

Nenhuma etapa implementada torna-se baseline `HUMAN HOMOLOGATED / LOCKED` sem homologação humana explícita.

Etapa homologada não é reaberta silenciosamente.

Qualquer alteração estrutural exige rastreabilidade e atualização das baselines afetadas.

> "Quem pede um, pede bis."
