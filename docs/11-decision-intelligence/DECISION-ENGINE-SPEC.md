# Decision Intelligence Engine Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 05 — Churn, Uplift, and Decision Optimization (Rails 13, 14)
Owner: Decision Intelligence Architecture
Traceability: `BR-002`, `BR-005`, `FR-DEC-001`, `INV-AI-001`, `INV-ACT-001`, `INV-COST-001`, `INV-TEN-001..003`, `INV-DATA-001`, `NFR-AI-006..007`, `NFR-COST-001`, `AC-007`, `AC-014`, `ADR-0003`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Principles of Governed Decision Optimization

The Decision Intelligence Engine optimizes business interventions (e.g. proactive outreach, priority logistics routing, service credit vouchers) to mitigate revenue loss. It acts as a deterministic mathematical optimizer over validated predictive, causal, and constraint inputs (`FR-DEC-001`).

### 1.1 Non-Negotiable Invariants
1. **Strict Ontological Separation (`INV-AI-001`)**:
   - *Prediction / Churn Risk*: $P(\text{churn} \mid X)$, calibrated probability of future customer attrition without intervention.
   - *Local Explanation (SHAP)*: Feature attribution values describing model scoring mechanics; strictly NOT causal evidence.
   - *Treatment Effect / Uplift (CATE)*: $\mathbb{E}[Y(1) - Y(0) \mid X]$, the incremental change in outcome caused by the intervention.
   - *Eligibility*: Boolean determination based on customer contract, consent, and frequency limits.
   - *Expected Utility*: Net monetary payoff balancing incremental benefit against intervention cost, risk penalty, and uncertainty.
   - *Recommendation*: Ranked list of eligible candidate interventions with stated utility and limitations.
   - *Approval*: Human or governed policy sign-off (Phase 06 scope).
   - *Action*: Physical tool execution against external APIs (Phase 06 scope).
2. **Hard Constraints Precede Utility Ranking (`AC-007`)**: The engine MUST evaluate and enforce all tenant isolation, eligibility, frequency, budget, capacity, and blast-radius constraints before calculating or ranking expected utility. Ineligible candidates cannot be ranked or recommended.
3. **No External Side Effects in Phase 05 (`INV-ACT-001`)**: Phase 05 execution is purely analytical and computational. It creates `Recommendation` and `Decision` artifacts. It is prohibited from sending customer emails, modifying CRM/ERP/WMS records, executing payments, or calling external action adapters.
4. **Deterministic Optimization and Abstention**: When expected utility is negative ($\mathbb{E}[U(a)] \le 0$) or no candidate satisfies constraints, the engine abstains by returning `NO_RECOMMENDATION` or `NEED_MORE_EVIDENCE`. It is forbidden to force an unsafe or uneconomic intervention.
5. **No Model Authority Escalation**: LLMs may summarize or explain decision manifests but cannot determine candidate eligibility, alter utility weights, or approve interventions.

---

## 2. The 12-Step Decision Pipeline

Every decision execution follows a deterministic, non-bypassable 12-step sequence:

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Step 1: Validate TenantContext, PrincipalContext, and Request Auth    │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 2: Validate Versioned Data Snapshot and As-Of Watermark (INV-DATA)│
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 3: Validate Candidate Interventions and Cost Parameters           │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 4: Apply Hard Eligibility Constraints (Contract / Consent)        │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 5: Apply Policy and Cooldown Constraints (Frequency Caps)         │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 6: Apply Budget Constraints (Monetary Budget Ceiling)             │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 7: Apply Operational Capacity and Blast-Radius Constraints        │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 8: Compute Expected Utility for Eligible Candidates               │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 9: Rank Eligible Candidates using Deterministic Tie-Breaking      │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 10: Attach Uncertainty Interval, Risk Penalties, and Limitations  │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 11: Format Recommendation Record or Return NEED_MORE_EVIDENCE     │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Step 12: Seal Reproducibility Manifest (SHA-256 Digest) and Emit Audit │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Mathematical Formulation of Expected Utility

For an eligible candidate intervention $a \in \mathcal{A}_{\text{eligible}}$ applied to target unit $i$:

$$\mathbb{E}[U(a_i)] = \underbrace{\tau(X_i, a) \cdot V_{\text{customer}}}_{\text{Expected Incremental Gain}} - \underbrace{C(a)}_{\text{Direct Intervention Cost}} - \underbrace{\lambda_{\text{risk}} \cdot \text{RiskPenalty}(a)}_{\text{Operational Risk Penalty}} - \underbrace{\lambda_{\text{unc}} \cdot \sigma_{\tau}(X_i, a)}_{\text{Uncertainty Penalty}}$$

Where:
- $\tau(X_i, a) = \mathbb{E}[Y_i(a) - Y_i(0) \mid X_i]$ is the Conditional Average Treatment Effect (CATE) / Uplift score estimated by a validated causal model.
- $V_{\text{customer}}$ is the customer baseline annualized contract value (ARR) or order gross merchandise value (GMV).
- $C(a)$ is the monetary cost of executing intervention $a$ (e.g. shipping surcharge absorption, voucher credit amount).
- $\text{RiskPenalty}(a)$ penalizes high-blast-radius actions or sensitive customer segments.
- $\sigma_{\tau}(X_i, a)$ is the half-width of the 95% confidence interval on the CATE estimate.
- $\lambda_{\text{risk}} \ge 0, \lambda_{\text{unc}} \ge 0$ are governance-configured risk-aversion hyper-parameters.

### Optimization Rules:
1. **Economic Viability Rule**: If $\mathbb{E}[U(a_i)] \le 0$ for all $a \in \mathcal{A}$, the optimizer selects the null action $a_{\emptyset}$ (Abstain).
2. **Deterministic Tie-Breaking**: If two candidates have identical utility within $|\Delta U| < 0.001$, ties are resolved by:
   1. Lower direct intervention cost $C(a)$.
   2. Lower uncertainty $\sigma_{\tau}(a)$.
   3. Lexicographical order of `candidate_id`.

---

## 4. Canonical Decision Data Contracts

```python
class CandidateIntervention(BaseModel):
    candidate_id: str                      # E.g. "int_priority_reship_01"
    name: str                              # "Priority Air Reshipment"
    action_type: str                       # "LOGISTICS_EXPEDITE"
    estimated_cost_usd: Decimal            # E.g. Decimal("45.00")
    eligible_tiers: List[str]              # E.g. ["ENTERPRISE", "GROWTH"]
    max_frequency_days: int                # Cooldown period (e.g. 14 days)
    risk_tier: Literal["LOW", "MEDIUM", "HIGH"]

class ConstraintEvaluationResult(BaseModel):
    is_eligible: bool
    rejection_reasons: List[str]           # E.g. ["ERR_COOLDOWN_ACTIVE", "ERR_BUDGET_EXCEEDED"]
    checked_constraints: List[str]

class DecisionRequest(BaseModel):
    request_id: UUIDv7
    tenant_id: TenantId
    customer_id: str
    investigation_id: Optional[UUIDv7] = None
    as_of_time: UtcDateTime
    candidates: List[CandidateIntervention]
    customer_arr_usd: Decimal
    allocated_budget_usd: Decimal
    remaining_capacity: int
    risk_aversion_lambda: float = 0.50
    uncertainty_lambda: float = 0.50

class RecommendationRecord(BaseModel):
    recommendation_id: UUIDv7
    request_id: UUIDv7
    tenant_id: TenantId
    selected_candidate_id: Optional[str]   # None if abstained
    expected_utility_usd: Decimal
    expected_incremental_retention_rate: float # CATE estimate
    direct_cost_usd: Decimal
    risk_penalty_usd: Decimal
    uncertainty_penalty_usd: Decimal
    confidence_interval_95: Tuple[float, float]
    ranked_alternatives: List[Dict[str, Any]]
    ineligible_candidates: Dict[str, List[str]] # candidate_id -> reasons
    status: Literal["RECOMMENDED", "ABSTAINED", "NEED_MORE_EVIDENCE", "BLOCKED"]
    decision_digest: str                   # SHA-256 over canonical inputs and outputs
    created_at: UtcDateTime
```

---

## 5. Security, Tenancy, and Blast-Radius Constraints

| Constraint Domain | Invariant Enforcement | Failure Mode |
|---|---|---|
| **Multi-Tenancy** | Composite primary key `(tenant_id, id)` and PostgreSQL RLS on all decision tables (`INV-TEN-001`) | `ERR_TENANT_MISMATCH` (HTTP 403) |
| **Budget Ceiling** | Total daily recommended expenditure cannot exceed tenant budget allocation (`INV-COST-001`) | Candidate excluded from ranking |
| **Blast Radius** | Max treated customers per anomaly incident $\le 500$ accounts (`NFR-COST-001`) | Truncates cohort or flags `REQUIRES_HUMAN_APPROVAL` |
| **Read-Only Barrier**| Output is an immutable recommendation artifact; zero tool write dispatch (`INV-ACT-001`) | External tool execution physically barred |
