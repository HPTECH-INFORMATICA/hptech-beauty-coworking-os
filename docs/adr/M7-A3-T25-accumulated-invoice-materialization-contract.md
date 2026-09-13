# ADR — M7-A3-T25 Accumulated Invoice Materialization Contract

**Status:** IMPLEMENTED / QUALITY GATE PASS / AWAITING HUMAN HOMOLOGATION

> Quem pede um, pede bis.

## Purpose

Freeze how the BCOS worker materializes `ACCUMULATED_OPEN_INVOICE` Billing for a completed Usage without reopening the previously approved M7-A3 contracts.

T25 is the implementation contract that closes the gap intentionally left by T24 between accumulated Invoice identity and executable worker materialization.

## Authority

1. T14 remains authoritative for `invoice_mode`.
2. T15-T17 remain authoritative for historical `ProfessionalBillingContract` persistence and resolution.
3. T19-T22 remain authoritative for accumulated Invoice lifecycle configuration.
4. T22.1 remains authoritative for `cycle_allocation_policy` semantics.
5. T22.2-T22.5 remain authoritative for InvoiceItem segmentation, specific-charge discount linkage, physical allocation-policy representation and migration boundaries.
6. T23 remains authoritative for materialization behavior and transactional atomicity.
7. T24 remains authoritative for accumulated Invoice logical identity and MANUAL lifecycle selection semantics.
8. Migration `0007_invoice_cycle_identity` remains authoritative for the already-materialized accumulated Invoice physical identity.

## Entry condition

9. T25 applies only when `ProfessionalBillingContract.invoice_mode = ACCUMULATED_OPEN_INVOICE`.
10. The worker MUST use the `ProfessionalBillingContract` already resolved inside `UsagePricingContext`.
11. The materializer MUST NOT perform a second independent historical contract resolution.
12. The Usage MUST be `COMPLETED` and continue to be processed through the existing `USAGE_COMPLETED` Outbox transaction.
13. Tenant, professional, Usage and historical Billing-contract identity MUST match the hydrated authoritative context.

## Lifecycle modes

14. V1 accumulated materialization supports exactly:
    - `WEEKLY`;
    - `BIWEEKLY`;
    - `MONTHLY`;
    - `MANUAL`.
15. Unsupported lifecycle modes MUST fail closed.
16. Missing lifecycle configuration required by the selected mode MUST fail closed.

## Timezone and cycle-boundary authority

17. Automatic lifecycle cycle boundaries MUST be derived in the Unit IANA timezone already present in `UsagePricingContext`.
18. Persisted `billing_cycle_start` and `billing_cycle_end` MUST be canonical timezone-aware UTC instants.
19. Automatic cycle identity MUST satisfy `billing_cycle_start < billing_cycle_end`.
20. Processing time, Invoice creation time and current server timezone MUST NOT determine the financial cycle.
21. Reception closing and Billing lifecycle closing remain separate concepts.

## WEEKLY lifecycle

22. `lifecycle_weekday` and `lifecycle_closing_time` define the recurring weekly cutoff in Unit local time.
23. The cycle containing an authoritative financial instant is the half-open interval between the immediately previous applicable cutoff and the immediately following applicable cutoff.
24. A local instant exactly at a weekly cutoff belongs to the cycle beginning at that cutoff.

## BIWEEKLY lifecycle

25. `lifecycle_biweekly_anchor` and `lifecycle_closing_time` define the recurring 14-day cutoff series in Unit local time.
26. The anchor date is part of the cutoff series and MUST NOT be shifted by processing time.
27. The applicable cycle is the half-open interval between consecutive 14-day cutoffs.
28. A local instant exactly at a biweekly cutoff belongs to the cycle beginning at that cutoff.

## MONTHLY lifecycle

29. `lifecycle_month_day` and `lifecycle_closing_time` define the contractual monthly cutoff in Unit local time.
30. When `lifecycle_month_day` is greater than the number of days in a calendar month, the cutoff for that month MUST occur on that month's final calendar day at `lifecycle_closing_time`.
31. The applicable cycle is the half-open interval between consecutive contractual monthly cutoffs.
32. A local instant exactly at a monthly cutoff belongs to the cycle beginning at that cutoff.

## MANUAL lifecycle

33. MANUAL has no automatic calendar cycle boundaries.
34. MANUAL accumulated Invoices MUST persist `billing_cycle_start IS NULL` and `billing_cycle_end IS NULL`.
35. The worker MAY reuse exactly one eligible MANUAL accumulated Invoice for the same tenant, professional and historical Billing contract when `manual_closed_at IS NULL` and the Invoice is in a materializable state.
36. If no eligible MANUAL Invoice exists, the worker MAY create one.
37. More than one eligible MANUAL Invoice for the same historical contract MUST fail closed.
38. The worker MUST NOT close, rotate, reopen or assign `manual_closed_at` to a MANUAL Invoice.

## Materializable Invoice state

39. V1 worker materialization may write only to an Invoice whose status is `OPEN`.
40. `PARTIALLY_PAID`, `PAID` and `CANCELLED` accumulated Invoices MUST NOT receive new automatic financial effects.
41. Status alone does not establish identity or eligibility; all tenant, professional, historical contract and cycle/lifecycle identity checks remain mandatory.

## Automatic-cycle Invoice identity

42. For `WEEKLY`, `BIWEEKLY` and `MONTHLY`, the exact physical identity is:

    `tenant_id + professional_billing_contract_id + billing_cycle_start + billing_cycle_end`.

43. `source_usage_id` MUST remain NULL for accumulated Invoices.
44. A matching Invoice for another professional MUST fail closed.
45. A matching Invoice for another historical Billing contract MUST fail closed.
46. More than one row representing the same logical cycle MUST fail closed.
47. Concurrent creation MUST rely on the existing database uniqueness guarantee and MUST resolve the same persisted Invoice after conflict rather than create a duplicate.

## USAGE_COMPLETION allocation policy

48. Under `USAGE_COMPLETION`, the authoritative allocation instant is `Usage.checked_out_at`.
49. Nominal cutoff crossing during the Usage MUST NOT by itself split the Usage financial effects.
50. All Usage-derived financial effects produced by the approved V1 Pricing/Billing calculation belong to the accumulated Invoice cycle containing `checked_out_at`.
51. Non-segmented Usage-derived InvoiceItem idempotency remains governed by the approved non-segmented identity.

## FIXED_CUTOFF_SPLIT allocation policy

52. Under `FIXED_CUTOFF_SPLIT`, a financial effect whose approved temporal interval crosses exactly one contractual lifecycle cutoff MUST be partitioned into pre-cutoff and post-cutoff financial segments according to the approved Pricing/Billing semantics.
53. Each persisted segment MUST carry `billing_period_start` and `billing_period_end`.
54. Each segment MUST be materialized into the accumulated Invoice identified by the Billing cycle containing that segment.
55. Segment idempotency MUST use:

    `tenant_id + usage_id + item_type + billing_period_start + billing_period_end`.

56. Reprocessing the same segment MUST resolve the existing logical financial evidence rather than create another InvoiceItem.
57. T25 MUST NOT invent a new monetary proration formula.
58. `BASE_LEASE` MUST NOT be automatically prorated or split merely because a Usage crosses a Billing cutoff.
59. `OVERTIME` MAY be split only when an already-approved temporal financial effect actually spans the cutoff and the required monetary segmentation is deterministically available from the Pricing/Billing calculation.
60. If the approved calculation cannot deterministically produce the monetary segments required for `FIXED_CUTOFF_SPLIT`, materialization MUST fail closed rather than approximate or infer values.
61. More than one lifecycle cutoff crossed by a single materializable temporal effect is outside V1 T25 and MUST fail closed until separately approved.

## InvoiceItem materialization

62. The materializer MUST preserve the original immutable Usage-derived financial evidence.
63. Existing compatible InvoiceItems MUST be reused on retry.
64. An existing InvoiceItem whose Invoice, amount, quantity, description, metadata or segment identity conflicts with the expected financial evidence MUST fail closed.
65. A Usage-derived item MUST NOT be silently moved between Invoices after materialization.
66. Specific-charge DISCOUNT behavior remains governed by T22.2-T23 and is not expanded by T25.

## Invoice totals

67. After materialization, Invoice totals MUST be derived from the persisted InvoiceItems belonging to that Invoice, not from unrelated Usage state.
68. `subtotal_amount`, `discount_amount` and `total_amount` MUST remain internally consistent with the existing Billing model.
69. Retry MUST produce the same totals for unchanged financial evidence.
70. T25 does not define automatic Invoice closing or due-date calculation.

## Transactional atomicity

71. Cycle resolution, Invoice selection or creation, InvoiceItem materialization, Invoice total update and successful Outbox transition to `PROCESSED` MUST remain inside the existing M7-A3-T5 financial transaction.
72. Any failure in accumulated materialization MUST roll back the complete financial transaction.
73. The Outbox event MUST NOT be marked `PROCESSED` when accumulated Billing materialization fails.
74. Retry scheduling remains governed by the previously approved Outbox contracts.

## Concurrency and locking

75. Resolution of an existing eligible accumulated Invoice MUST lock the selected Invoice row before mutating its financial contents.
76. Automatic-cycle create races MUST depend on `uq_invoices_accumulated_cycle` as the final physical uniqueness authority.
77. MANUAL create races MUST depend on `uq_invoices_manual_active_contract` as the final physical uniqueness authority.
78. A uniqueness conflict MUST be followed by deterministic re-resolution of the one expected Invoice.
79. A conflicting row that does not match the expected tenant, professional, historical contract, lifecycle identity or materializable state MUST fail closed.

## Fail-closed conditions

80. Missing historical professional Billing contract MUST fail closed.
81. Ambiguous historical professional Billing contract resolution MUST fail closed.
82. Invalid Unit IANA timezone MUST fail closed.
83. Missing or invalid lifecycle configuration MUST fail closed.
84. Missing or unsupported `cycle_allocation_policy` MUST fail closed.
85. Indeterminate automatic Billing-cycle boundaries MUST fail closed.
86. Invalid cycle interval MUST fail closed.
87. Multiple eligible accumulated Invoices MUST fail closed.
88. Non-OPEN accumulated Invoice selected for automatic materialization MUST fail closed.
89. Cross-tenant, cross-professional or cross-contract materialization MUST fail closed.
90. Incompatible InvoiceItem idempotency evidence MUST fail closed.
91. Unsupported FIXED_CUTOFF_SPLIT segmentation MUST fail closed.

## Implementation boundary

92. T25 authorizes implementation in the worker layer only after this contract is persisted.
93. No new Alembic migration is authorized by T25; migration `0007_invoice_cycle_identity` already provides the required accumulated Invoice identity fields and uniqueness boundaries for this implementation.
94. The existing PER_USAGE implementation MUST remain behaviorally unchanged except for shared internal helpers whose regression is fully covered by tests.
95. `usage_completed_handler.py` MAY dispatch `ACCUMULATED_OPEN_INVOICE` to the new accumulated materializer after the worker implementation passes its gate.

## Required implementation tests

96. Tests MUST cover deterministic WEEKLY cycle resolution.
97. Tests MUST cover deterministic BIWEEKLY cycle resolution.
98. Tests MUST cover MONTHLY day overflow to the final day of short months.
99. Tests MUST cover timezone conversion and persisted UTC cycle boundaries.
100. Tests MUST cover exact-cutoff boundary semantics.
101. Tests MUST cover MANUAL reuse, creation and ambiguity failure.
102. Tests MUST cover automatic-cycle Invoice reuse and concurrent-create resolution.
103. Tests MUST cover rejection of non-OPEN accumulated Invoices.
104. Tests MUST cover `USAGE_COMPLETION` without cutoff splitting.
105. Tests MUST cover `FIXED_CUTOFF_SPLIT` supported segmentation and fail-closed unsupported segmentation.
106. Tests MUST cover InvoiceItem retry idempotency and incompatible-evidence failure.
107. Tests MUST cover tenant/professional/historical-contract isolation.
108. Tests MUST cover `usage_completed_handler.py` dispatching both PER_USAGE and ACCUMULATED modes without regressing PER_USAGE.

## Non-goals

T25 does not define or authorize:

- a new database migration;
- automatic accumulated Invoice closing;
- MANUAL closing API or UI;
- due-date calculation;
- general Invoice-level discount behavior;
- new Payment behavior;
- new Pricing formulas;
- BASE_LEASE proration;
- multiple-cutoff splitting in one temporal effect;
- administrative Billing UI;
- RBAC changes;
- Audit event names;
- changes to Outbox retry/backoff/recovery policy;
- changes to the frontend.

## Implementation verification

Implementation is present on `main` and has passed the repository-wide BCOS Quality Gate through run `34766462286` at commit `644b8b7fe0d9fa6e17be1460dce06d5abb63cf7a`.

Verified implementation evidence includes:

- deterministic WEEKLY, BIWEEKLY, MONTHLY and MANUAL cycle behavior;
- Unit IANA timezone conversion with UTC persisted cycle boundaries and exact-cutoff semantics;
- automatic and MANUAL accumulated Invoice reuse/create/race behavior and OPEN-state enforcement;
- `USAGE_COMPLETION` accumulated materialization;
- supported `FIXED_CUTOFF_SPLIT` OVERTIME segmentation with exact temporal boundaries;
- fail-closed sub-minute, multi-cutoff/non-materializable and non-additive monetary segmentation boundaries;
- immutable financial-evidence conservation across supported split segments;
- BASE_LEASE remains whole and nonsegmented under `FIXED_CUTOFF_SPLIT`;
- segmented InvoiceItem retry idempotency and incompatible-evidence rejection;
- PER_USAGE and ACCUMULATED handler dispatch coverage;
- Billing writes and Outbox `PROCESSED` transition remain within the existing processing transaction;
- API, Worker and Web repository quality gates all PASS.

This verification does not self-grant HUMAN HOMOLOGATION. Final human homologation remains a separate governance action.

## Approval

HUMAN APPROVED for implementation.

Implementation completed and technically verified; HUMAN HOMOLOGATION remains pending.

Quem pede um, pede bis.
