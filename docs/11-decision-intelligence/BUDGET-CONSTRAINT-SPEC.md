# Budget, Capacity, and Policy Constraint Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 05 — Churn, Uplift, and Decision Optimization (Rails 13, 14, 15)
Owner: Decision Intelligence Architecture / FinOps Engineering
Traceability: `BR-005`, `FR-DEC-001`, `INV-COST-001`, `INV-ACT-001`, `INV-TEN-001..003`, `NFR-COST-001`, `AC-007`, `ADR-0001`

---

## 1. Principles of Hard Constraint Evaluation

In RevPilot AI, business constraints are not soft penalties or heuristic suggestions; they are **strict mathematical preconditions** that must be evaluated prior to utility optimization (`AC-007`). Any candidate intervention that violates a hard constraint is filtered out of the candidate pool before ranking.

### 1.1 Non-Negotiable Invariants
1. **Pre-Optimization Filtering (`AC-007`)**: Hard constraints are evaluated at Step 4–7 of the decision pipeline, strictly before expected utility computation (Step 8).
2. **Budget Inviolability (`INV-COST-001`, `NFR-COST-001`)**: Cumulative intervention expenditures cannot exceed the tenant's allocated monetary budget ceiling. If a proposed action would cause the budget ledger balance to become negative, it is immediately disqualified.
3. **Fail-Closed on Unknown State**: If tenant policy, IAM permissions, frequency caps, or customer consent status cannot be verified due to network timeout or missing data, the constraint evaluator rejects the candidate (`ERR_POLICY_UNKNOWN`). Fallback to unsafe permissive defaults is prohibited.
4. **Zero Action Execution (`INV-ACT-001`)**: Constraint validation evaluates eligibility for analytical recommendation only. It does not disburse funds or commit resources.

---

## 2. Taxonomy of Hard Constraints

| Constraint Class | Parameter | Verification Method | Rejection Error Code |
|---|---|---|---|
| **Tenant Scope** | `tenant_id` | Match authenticated JWT claim | `ERR_TENANT_MISMATCH` |
| **Monetary Budget** | `daily_budget_remaining_usd` | Inquire atomic Redis/PostgreSQL budget ledger | `ERR_BUDGET_EXCEEDED` |
| **Operational Capacity**| `max_concurrent_interventions`| Inquire active intervention count in pipeline | `ERR_CAPACITY_EXCEEDED` |
| **Customer Cooldown** | `cooldown_period_days` (e.g. 14d) | Check timestamp of last executed intervention | `ERR_COOLDOWN_ACTIVE` |
| **Frequency Cap** | `max_interventions_per_quarter`| Check count of interventions in trailing 90 days | `ERR_FREQUENCY_CAP_EXCEEDED` |
| **Customer Consent** | `opt_out_marketing_flag` | Check customer preferences table | `ERR_CUSTOMER_OPTED_OUT` |
| **Exclusion List** | `do_not_disturb_list` | Exact match against active exclusion IDs | `ERR_CUSTOMER_EXCLUDED` |
| **Blast-Radius Limit** | `max_treated_per_incident` (500)| Count accounts linked to target anomaly | `ERR_BLAST_RADIUS_EXCEEDED` |
| **Data Freshness** | `max_feature_staleness_hours` (24h)| Check `now() - feature_snapshot_time` | `ERR_STALE_FEATURES` |

---

## 3. Constraint Evaluator Contract

```python
class BudgetLedgerEntry(BaseModel):
    tenant_id: TenantId
    ledger_date: UtcDate
    total_allocated_usd: Decimal
    committed_expenditure_usd: Decimal
    remaining_balance_usd: Decimal
    version: int

class ConstraintEvaluatorRequest(BaseModel):
    tenant_id: TenantId
    customer_id: str
    intervention: CandidateIntervention
    current_time: UtcDateTime
    budget_ledger: BudgetLedgerEntry
    active_capacity_count: int
    customer_history_timestamps: List[UtcDateTime]
    customer_opt_out: bool
    is_excluded: bool
    feature_timestamp: UtcDateTime

class ConstraintEvaluationOutcome(BaseModel):
    is_eligible: bool
    passed_constraints: List[str]
    violated_constraints: List[str]        # Empty if is_eligible is True
    evaluated_at: UtcDateTime
```

---

## 4. Budget Ledger and Concurrency Management

1. **Atomic Reservation**: When a decision recommendation is generated, the required funds are temporarily reserved with a 2-hour TTL.
2. **Deterministic Ledger Reconciliation**: The budget ledger records every reservation and expiration with an incrementing `version` counter (`INV-COST-001`).
3. **No Overdraft**: Concurrent decision requests attempting to reserve the last remaining budget execute with optimistic concurrency control (`OCC`). The losing request fails closed with `ERR_BUDGET_EXCEEDED` and abstains from recommending costly interventions.

---

## 5. Automated Verification Suite Mapping

- `tests/domain/test_budget_constraint_evaluation.py`: Tests that exceeding budget by $0.01 immediately filters candidate.
- `tests/domain/test_cooldown_frequency_caps.py`: Tests that customers contacted within 14 days are excluded.
- `tests/domain/test_constraint_fail_closed.py`: Tests that null or missing policy data causes `ERR_POLICY_UNKNOWN`.
- `tests/security/test_constraint_tenant_isolation.py`: Tests that budget ledgers are strictly partitioned by tenant ID.
