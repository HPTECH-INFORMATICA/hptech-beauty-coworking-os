# M7-A2-T1 — Reception Closing Temporal Contract

## Status

HUMAN APPROVED

## Context

O contrato OpenAPI V1 determina que:

- o check-out finaliza o Usage;
- a mesma transação deve registrar `USAGE_COMPLETED` na Transactional Outbox;
- o worker processará posteriormente Pricing/Billing de forma idempotente;
- excedente ocorrido após o encerramento da recepção não deve gerar cobrança de `OVERTIME`.

A auditoria do repositório confirmou que:

- `USAGE_COMPLETED` contém `usage_id` e `checked_out_at`;
- o consumer pode hidratar Usage, Booking, Unit e Reception Hours de forma tenant-safe;
- `Booking.pricing_snapshot` é persistido e fisicamente imutável;
- `Unit.timezone` é um timezone IANA válido;
- Reception Hours possui `day_of_week`, `opens_at`, `closes_at` e `is_closed`;
- não existia contrato persistido definindo a interpretação temporal necessária para aplicar a regra V1 de encerramento da recepção.

Este contrato congela somente essa semântica temporal. Ele não define fórmulas, preços, tarifas ou demais regras do Pricing Engine.

## Decision

### 1. Weekday convention

`unit_reception_hours.day_of_week` segue:

- `0` = segunda-feira
- `1` = terça-feira
- `2` = quarta-feira
- `3` = quinta-feira
- `4` = sexta-feira
- `5` = sábado
- `6` = domingo

### 2. Local time

`Usage.checked_out_at` deve ser convertido para o timezone IANA da `Unit` antes da avaliação de Reception Hours.

### 3. Applicable reception day

A linha de `unit_reception_hours` aplicável é aquela correspondente ao `day_of_week` da data local resultante do check-out.

### 4. Closed reception day

Quando `is_closed = true`, a recepção é considerada fechada durante todo o dia local.

Consequentemente, período excedente ocorrido nesse dia não deve gerar item de cobrança `OVERTIME`.

### 5. Missing reception-hours configuration

Quando não existir configuração de Reception Hours para o `day_of_week` local aplicável, o estado é considerado erro de configuração.

A ausência de configuração não autoriza implicitamente cobrança de `OVERTIME`.

O processamento financeiro não deve fabricar uma decisão de cobrança nessa situação.

### 6. Reception closing cutoff

Em dia aberto, `closes_at` representa o limite máximo temporal para cobrança de overtime.

Tempo posterior a `closes_at` deve ser excluído da cobrança de `OVERTIME`.

### 7. Exact closing instant

O instante exatamente igual a `closes_at` não é considerado posterior ao encerramento.

Portanto, o corte temporal ocorre em `closes_at`.

### 8. Cross-midnight reception windows

Horários de recepção atravessando meia-noite permanecem fora do contrato V1.

A baseline física vigente exige `opens_at < closes_at`.

## Boundary

Este contrato não altera o boundary já estabelecido:

`check-out`
→ `USAGE_COMPLETED`
→ Transactional Outbox
→ worker assíncrono/idempotente
→ hidratação tenant-safe
→ Usage
→ Booking
→ `pricing_snapshot` imutável + contexto
→ Unit timezone + Reception Hours
→ Pricing/Billing
→ Invoice / InvoiceItem
→ Payment

O evento `USAGE_COMPLETED` permanece mínimo.

Informações adicionais necessárias ao processamento devem ser obtidas da fonte autoritativa no banco e não adicionadas ao evento sem nova decisão arquitetural.

## Non-goals

Este contrato não define:

- fórmula de overtime;
- valor por minuto, hora ou período;
- arredondamento financeiro;
- franquias ou tolerâncias;
- descontos;
- regras de `BASE_LEASE`;
- semântica interna de `PricingRule.rule_definition`;
- estratégia técnica de polling, locking ou retry do worker;
- criação ou liquidação de Payment.

Esses comportamentos permanecem sob seus respectivos boundaries de Pricing/Billing.

## Governance

Decision: M7-A2-T1 — Reception Closing Temporal Contract

Approval: HUMAN APPROVED
