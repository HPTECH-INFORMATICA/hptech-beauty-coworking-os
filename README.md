# HPTECH Beauty Coworking OS

SaaS B2B multi-tenant para gestão operacional e financeira de coworkings de beleza, estética, saúde e bem-estar.

> "Quem pede um, pede bis."

## Status

Projeto em fase de fundação técnica.

Nenhuma implementação funcional do produto foi iniciada nesta baseline.

## Baselines homologadas

- PRD MASTER v1.0
- Architecture Freeze v1.2
- PostgreSQL DDL v1.2.1
- Database Integrity Test Suite v1.1

O contrato OpenAPI ainda não é uma baseline congelada.

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

## Estrutura

- `apps/web` — frontend web.
- `services/api` — backend/API.
- `packages/domain` — tipos e conceitos compartilhados quando aplicável.
- `packages/contracts` — contratos compartilhados.
- `packages/ui` — componentes/design system.
- `database/migrations` — migrations versionadas.
- `database/tests` — testes de integridade do banco.
- `database/seeds` — dados de desenvolvimento.
- `docs/product` — documentação do produto.
- `docs/architecture` — arquitetura e baselines.
- `docs/api` — contratos de API.
- `docs/adr` — Architecture Decision Records.
- `infra` — infraestrutura.
- `scripts` — automações do projeto.
- `tests` — testes de nível sistêmico.

## Governança

Antes de qualquer implementação:

1. revisar;
2. analisar;
3. verificar;
4. investigar;
5. diagnosticar;
6. comparar com as baselines;
7. avaliar impacto;
8. implementar somente depois do Gate aprovado.

Etapas homologadas não são reabertas silenciosamente.

Mudanças estruturais exigem nova versão, migration ou ADR conforme o impacto.

## Repositório

Este projeto é independente do `hptech-platform`.

A integração futura com a HPTECH Platform deverá ocorrer por contratos explícitos e não por acoplamento estrutural prematuro.

---

"Quem pede um, pede bis."
