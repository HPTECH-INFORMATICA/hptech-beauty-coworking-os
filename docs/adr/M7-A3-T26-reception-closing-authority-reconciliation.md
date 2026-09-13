# ADR — M7-A3-T26 Reception Closing Authority Reconciliation

**Status:** TECHNICALLY RECONCILED / AWAITING HUMAN HOMOLOGATION

> Quem pede um, pede bis.

## Purpose

Resolve the documented contradiction between the locked M7-A2 reception-closing rule and the later M7-A3-T11 wording without changing the already implemented BCOS financial behavior.

This ADR is a reconciliation/supersession record. It does not introduce a new commercial pricing formula.

## Authoritative baseline

M7-A2-T1 — Reception Closing Temporal Contract remains authoritative for the V1 reception-closing financial boundary.

The authoritative rule is:

- `Unit.reception_hours.closes_at` is the maximum temporal instant at which overtime may remain chargeable;
- elapsed overtime strictly after `closes_at` MUST NOT generate a financial `OVERTIME` charge;
- an exact instant equal to `closes_at` belongs to the pre-closing interval;
- when the applicable reception day is closed, overtime on that day MUST NOT generate a financial `OVERTIME` charge;
- missing Reception Hours configuration remains fail-closed.

The M7-A3 Pricing Rule Definition contract already repeats this same rule: time after reception closing must not generate OVERTIME.

## Contradiction identified

M7-A3-T11 — Reception Closing Overtime Segmentation Contract contains later wording stating that overtime after reception closing may be charged or forgiven.

That wording conflicts with:

1. M7-A2-T1;
2. the M7-A3-T7/T8 reception-closing boundary;
3. the implementation currently present in `services/worker/src/bcos_worker/financial_effects.py`;
4. the current worker tests protecting reception-closing behavior.

## Reconciliation decision

For V1 Billing materialization, the conflicting financial interpretation in M7-A3-T11 is superseded by this T26 reconciliation.

The following T11 concepts remain valid only as temporal/audit concepts:

- overtime may be classified into before-reception-close and after-reception-close temporal portions;
- actual Usage time after reception close is not erased from operational history;
- temporal classification may remain available for observability/auditability.

However:

- the after-reception-close temporal portion MUST NOT materialize a financial `OVERTIME` InvoiceItem;
- the worker MUST NOT create an `OVERTIME` amount for that portion merely to later neutralize it through `DISCOUNT`;
- administrative forgiveness does not apply to a charge that is prohibited from existing by the reception-closing baseline;
- a `DISCOUNT` may still exist for other separately approved charge-forgiveness scenarios, but not as a mechanism to reintroduce a post-reception-close OVERTIME charge.

## Implementation alignment

The current implementation already follows this reconciled authority:

- `classify_overtime(...)` may preserve temporal evidence;
- `calculate_usage_financial_effects(...)` materializes only `before_reception_close` as financial OVERTIME;
- a closed reception day materializes no OVERTIME financial effect;
- financial item creation after reception close is therefore prevented before Invoice materialization.

No production code change is required by T26 unless a future regression is discovered.

## Required regression evidence

The worker test suite MUST continue to protect at least:

1. overtime entirely before reception close remains chargeable according to the approved Pricing rule;
2. overtime crossing reception close charges only the pre-close portion;
3. overtime strictly after reception close does not generate an additional OVERTIME financial effect;
4. a closed reception day generates no OVERTIME charge;
5. exact `closes_at` semantics remain consistent with M7-A2-T1;
6. PER_USAGE and ACCUMULATED materializers consume the same reconciled financial effects rather than implementing independent reception-closing interpretations.

## Non-goals

T26 does not define or authorize:

- new overtime formulas;
- new PricingRule fields;
- automatic or manual Invoice closing;
- due dates;
- new DISCOUNT behavior;
- Payment creation or settlement;
- RBAC or administrative forgiveness UI;
- Audit event names;
- a new Alembic migration;
- frontend changes.

## Governance

T26 does not rewrite historical ADR text silently. It records the supersession explicitly so that the repository preserves traceability of the prior contradiction.

M7-A2-T1 remains the authoritative V1 reception-closing financial rule.

T25 remains HUMAN HOMOLOGATED / LOCKED and is not reopened by this reconciliation.

Final HUMAN HOMOLOGATION of T26 remains a separate governance action.

> Quem pede um, pede bis.
