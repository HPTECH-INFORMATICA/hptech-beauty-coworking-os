# HPTECH Beauty Coworking OS — Project Status

> "Quem pede um, pede bis."

## Projeto

HPTECH Beauty Coworking OS

## Repositório local

`C:\HudsonPedro\hptech-beauty-coworking-os`

Projeto independente do `hptech-platform`.

Integração futura com a HPTECH Platform somente por contratos explícitos, sem acoplamento estrutural prematuro.

## Product Baseline

- PRD MASTER v1.0 — HUMAN HOMOLOGATED / LOCKED

## Architecture Baseline

- Architecture Freeze v1.2 — HUMAN HOMOLOGATED / LOCKED

## Database Baseline

- PostgreSQL DDL v1.2.1 — HOMOLOGADO
- Database Integrity Test Suite v1.1 — HOMOLOGADA
- Migration executável inicial — materializada
- PostgreSQL real / Neon BCOS — VALIDADO
- Alembic revision — `0001_initial_bcos_schema`
- Database Integrity Test Suite contra PostgreSQL real — PASS
- Alembic downgrade → upgrade — PASS

## API Baseline

- OpenAPI V1 — MATERIALIZADO / VALIDADO / LOCKED
- Arquivo: `docs/api/openapi.yaml`
- Foundation commit: `cc1bf4a`
- Prettier — PASS
- Redocly — 0 errors
- Warnings recomendados não bloqueantes permanecem registrados

## Technology Baseline

BCOS-M0.2 — HUMAN HOMOLOGATED / LOCKED

Stack homologada:

- Frontend: Next.js + React + TypeScript
- Workspace: pnpm + Turborepo
- Backend: Python 3.12 + FastAPI
- Validation: Pydantic
- Persistence: SQLAlchemy 2.x
- Migrations: Alembic + PostgreSQL SQL explícito para invariantes críticas
- Database: PostgreSQL / Neon
- Worker: processo Python separado
- Frontend Deploy: Vercel
- API / Worker Deploy: Render
- E-mail: Resend
- Source Control: Git + GitHub

## Princípios não negociáveis

- Zero overlap físico.
- Isolamento multi-tenant.
- ResourceOccupancy como fonte canônica de indisponibilidade.
- Booking e Usage são entidades distintas.
- Pricing, Billing e Payment são domínios distintos.
- Pricing Snapshot é imutável.
- Billing e Payments devem ser idempotentes.
- Transactional Outbox para eventos financeiros críticos.
- RBAC e autorização server-side.
- Professional opera sob escopo own.
- Regras críticas nunca dependem somente do frontend.
- Zero Vendor Lock-in.

## Estado oficial das etapas

### BCOS-M0.1 — Repository Foundation

Status: HUMAN HOMOLOGATED / LOCKED

Fundação independente do repositório estabelecida e homologada.

### BCOS-M0.2 — Technical Foundation

Status: HUMAN HOMOLOGATED / LOCKED

Inclui:

- Technology Decision Gate
- Repository Toolchain Policy
- Node / pnpm / Turbo Workspace
- Python Virtual Environment
- Backend Toolchain
- Frontend Quality Toolchain
- Backend Quality Toolchain
- Dependency Lock Strategy
- Application Skeleton
- Database Executable Baseline
- Real PostgreSQL Validation
- OpenAPI V1

Marcos Git relevantes:

- `52ba61a` — BCOS-M0.2-F: establish database executable baseline
- `f022133` — BCOS-M0.2-G: validate real PostgreSQL baseline
- `cc1bf4a` — BCOS-M0.2-H: establish OpenAPI v1 contract

### BCOS-M1 — Identity / Tenancy / RBAC

Status: HUMAN HOMOLOGATED / LOCKED

Commit:

- `19e0c28` — BCOS-M1: establish identity tenancy and RBAC foundation

Baseline:

- identidade autenticada representada por contrato interno;
- integração criptográfica HPTECH Identity ainda não acoplada;
- configuração sem adapter real permanece fail-closed;
- tenant context validado server-side;
- memberships tenant-scoped;
- RBAC server-side;
- OWNER / ADMIN / RECEPTION / PROFESSIONAL;
- Professional own-scope estabelecido;
- isolamento tenant preservado.

### BCOS-M2 — Units / Resources / Professionals

Status: HUMAN HOMOLOGATED / LOCKED

Commits:

- `800b16e` — BCOS-M2: implement units resources and professionals
- `f160a47` — BCOS-M2: align HTTP API with frozen OpenAPI contract

Baseline:

- Units;
- Reception Hours;
- Resource Categories;
- Resources;
- Professionals;
- serviços tenant-scoped;
- autorização OPERATIONS;
- integração HTTP;
- alinhamento com OpenAPI congelado;
- erros padronizados;
- testes de regressão.

Validação final:

- API suite — 87 passed
- Ruff — PASS
- mypy — PASS
- OpenAPI M2 response map — PASS
- ErrorResponse — PASS
- Professional PATCH IntegrityError regression — PASS
- secret audit — PASS

### BCOS-M3 — ResourceOccupancy / Availability

Status: HUMAN HOMOLOGATED / LOCKED

Commit:

- `96bdfe5` — BCOS-M3: implement resource availability foundation

Baseline:

- ResourceOccupancy permanece autoridade física definitiva;
- intervalo canônico `[)`;
- ACTIVE occupancy bloqueia disponibilidade;
- RELEASED occupancy não bloqueia;
- PostgreSQL EXCLUDE USING gist permanece autoridade contra overlap;
- Availability é consulta preventiva para UX;
- Availability não reserva recurso;
- filtros tenant/unit/resource/category;
- validação de relações tenant-safe;
- nenhuma escrita de ResourceOccupancy exposta pelo M3.

Validação final:

- PostgreSQL M3 Availability Test Suite — PASS
- API regression — 109 passed
- Ruff — PASS
- mypy — PASS
- secret audit — PASS
- Git checkpoint — committed / pushed / synchronized

## Estado atual

```text
BCOS-M0.1 ........ HUMAN HOMOLOGATED / LOCKED
BCOS-M0.2 ........ HUMAN HOMOLOGATED / LOCKED
BCOS-M1 .......... HUMAN HOMOLOGATED / LOCKED
BCOS-M2 .......... HUMAN HOMOLOGATED / LOCKED
BCOS-M3 .......... HUMAN HOMOLOGATED / LOCKED
BCOS-M4 .......... PRE-IMPLEMENTATION AUDIT IN PROGRESS / IMPLEMENTATION NOT AUTHORIZED
BCOS-M5+ ......... NOT AUTHORIZED
```

## BCOS-M4 — Booking / Recurrence / Extension

Status:

PRE-IMPLEMENTATION AUDIT IN PROGRESS / IMPLEMENTATION NOT AUTHORIZED

Auditoria concluída até o momento:

M4-A1 — Physical Booking Baseline — PASS / LOCKED
M4-A2 — Booking Status Enum — PASS / LOCKED
M4-A3 — Frozen Booking API Contract — PASS / LOCKED
M4-A4 — Pricing Snapshot Dependency — PASS / LOCKED
M4-A5 — Pricing Contract Boundary — PASS / LOCKED
M4-A6 — Existing Architecture Audit — PASS / LOCKED

Constatações:

BookingCreate não recebe pricing_snapshot do cliente.
bookings.pricing_snapshot é obrigatório no banco.
Pricing Snapshot é imutável após criação.
Pricing é domínio distinto de Booking.
PricingRule.rule_definition possui estrutura aberta no OpenAPI.
A semântica do Pricing Engine não está definida pelo contrato OpenAPI.
M4 não deve inventar cálculo financeiro nem antecipar silenciosamente M6.
ResourceOccupancy continua sendo a autoridade definitiva contra overlap.
PENDING não adquire ocupação física definitiva.
CONFIRMED deve adquirir ResourceOccupancy de forma transacional.
confirmação concorrente deve depender da constraint EXCLUDE como autoridade final.
M4 ainda não possui autorização de implementação.
## Banco de dados

Projeto Neon independente:

hptech-beauty-coworking-os

Baseline validada:

Branch Neon: production
Database: neondb
Role: neondb_owner
conexão BCOS validada
PostgreSQL real validado
migration inicial aplicada
integridade física validada

Regra permanente:

Nunca reutilizar, inspecionar ou assumir banco, projeto, branch, credencial ou connection string da HPTECH Platform para BCOS.

## Git
Branch: main
HEAD homologado atual: 96bdfe55823060d0d2c853cae485ab02f8f934e5
Short SHA: 96bdfe5
Commit: BCOS-M3: implement resource availability foundation
origin/main: configurado
main sincronizada com origin/main
Working tree confirmado limpo antes desta reconciliação documental
Repositório remoto: GitHub / HPTECH-INFORMATICA / hptech-beauty-coworking-os
## Ambientes e ferramentas
Ambiente Python canônico: <repo>\.venv
Não usar services/api/.venv
Não usar uv run --project services/api
PowerShell atual não utiliza && como separador
CODEX: temporariamente indisponível por limite de uso
ChatGPT: arquitetura, engenharia, desenvolvimento orientado, auditoria e validação
## Débitos controlados
README.md permanece documentalmente defasado em relação ao estado M1–M3 e deverá ser reconciliado separadamente.
Adapter criptográfico real da HPTECH Identity permanece fora da baseline implementada do M1.
Questões registradas das baselines locked não devem ser alteradas silenciosamente em M4.
Semântica do Pricing Engine permanece pertencente ao estágio de Pricing; M4 não deve inventá-la.
## Próxima atividade autorizada

Continuar exclusivamente a auditoria pré-implementação do BCOS-M4.

Implementação de M4 permanece não autorizada até fechamento do Gate correspondente.

## Regra de Governança

Antes de qualquer implementação:

revisar;
analisar;
verificar;
investigar;
diagnosticar;
comparar com as baselines;
avaliar impacto;
implementar somente depois do Gate aprovado.

Nenhuma etapa implementada torna-se baseline sem Gate de homologação.

Etapa homologada não é reaberta silenciosamente.

Qualquer alteração estrutural exige novo ID, análise de impacto e atualização das baselines afetadas.

"Quem pede um, pede bis."
