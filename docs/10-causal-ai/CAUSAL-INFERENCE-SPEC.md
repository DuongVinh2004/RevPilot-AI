# Causal Inference and Estimand Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 04 — Hypothesis, Causal Analysis, and Verification (Rails 10, 12)
Owner: Causal AI Architecture / Econometrics Engineering
Traceability: `BR-001`, `BR-002`, `FR-ML-003`, `FR-ML-004`, `INV-AI-001`, `INV-DATA-001`, `INV-TEN-001..003`, `NFR-AI-007`, `AC-006`, `AC-014`, `ADR-0011`

---

## 1. Principles of Causal Identification and Estimation

Causal inference in RevPilot AI answers counterfactual questions regarding revenue loss, fulfillment disruptions, and candidate interventions. Causal assertions cannot be established by large language models, regression correlations, or naive observational comparisons (`INV-AI-001`, `FR-ML-004`).

### 1.1 Non-Negotiable Invariants
1. **Explicit Causal Estimand (`FR-ML-004`, `AC-006`)**: A causal statement is valid only when tied to an explicitly registered `CausalStudy` defining target population, treatment contrast, outcome, identifying assumptions, overlap verification, statistical estimator, confidence interval, and sensitivity analysis.
2. **Correlation vs Causation Distinction (`INV-AI-001`)**: Observational correlations ($r \ne 0$) and churn risk scores are not causal effects. They cannot be used as evidence of an intervention's expected impact.
3. **Temporal Ordering & No Lookahead (`INV-DATA-001`)**: Covariates must strictly precede treatment assignment in time. Post-treatment variables (mediators, colliders, downstream outcomes) cannot be used as adjustment controls. No information timestamped after `:as_of_time` may enter estimation.
4. **Positivity and Overlap Requirement**: If treatment assignment is deterministic or probability of treatment given covariates $e(X) = P(T=1|X)$ approaches 0 or 1, the study must halt with `ERR_OVERLAP_VIOLATION`. Truncating or hiding lack of support is prohibited.
5. **No Direct Model Computation**: LLMs may explain or format validated causal study outputs, but the numerical estimation and sensitivity analysis are executed strictly by deterministic statistical estimators.
6. **No Automated Action Execution (`INV-ACT-001`)**: Causal estimates quantify past or hypothetical effects. They do not constitute an authorization or automated trigger for business actions.

### 1.2 Non-Goals (MVP / v1 Scope)
- **Automated Causal Discovery Over Arbitrary Raw Schemas**: Unconstrained structure learning (e.g. PC algorithm, FCI) across arbitrary uncurated tables without expert DAG specification is out of scope.
- **Unvalidated Counterfactual Extrapolations**: Projecting counterfactual outcomes in regions of zero covariate support without overlap validation is strictly prohibited.
- **Direct Autonomous Action Triggering**: Causal estimations produce analytical insights only; they cannot self-trigger transactional mutations without human approval (`INV-ACT-001`, `INV-ACT-003`).

---

## 2. Canonical Causal Study Data Contract

Every causal investigation instantiates an immutable `CausalStudy` record:

```python
class EstimandType(str, Enum):
    ATE = "ATE"   # Average Treatment Effect: E[Y(1) - Y(0)]
    ATT = "ATT"   # Average Treatment Effect on the Treated: E[Y(1) - Y(0) | T=1]
    ATC = "ATC"   # Average Treatment Effect on the Controls: E[Y(1) - Y(0) | T=0]
    CATE = "CATE" # Conditional Average Treatment Effect: E[Y(1) - Y(0) | X=x]

class IdentificationStrategy(str, Enum):
    BACKDOOR_ADJUSTMENT = "BACKDOOR_ADJUSTMENT"
    DIFFERENCE_IN_DIFFERENCES = "DIFFERENCE_IN_DIFFERENCES"
    INSTRUMENTAL_VARIABLES = "INSTRUMENTAL_VARIABLES"
    SYNTHETIC_CONTROL = "SYNTHETIC_CONTROL"

class EstimatorType(str, Enum):
    DOUBLY_ROBUST_AIPW = "DOUBLY_ROBUST_AIPW"     # Augmented Inverse Probability Weighting
    TMLE = "TMLE"                                 # Targeted Maximum Likelihood Estimation
    TWO_STAGE_LEAST_SQUARES = "TWO_STAGE_LEAST_SQUARES"
    LINEAR_DID = "LINEAR_DID"

class OverlapDiagnostics(BaseModel):
    min_propensity: float = Field(ge=0.0, le=1.0)
    max_propensity: float = Field(ge=0.0, le=1.0)
    positivity_satisfied: bool
    common_support_ratio: float = Field(ge=0.0, le=1.0)
    trimmed_sample_count: int

class SensitivityAnalysis(BaseModel):
    method: Literal["ROSENBAUM_BOUNDS", "OSTER_DELTA", "E_VALUE"]
    robustness_value: float                      # E.g. minimum unobserved confounder strength needed to nullify effect
    e_value_estimate: float
    e_value_ci: float
    is_sensitive_to_unobserved_confounding: bool

class CausalStudy(BaseModel):
    study_id: UUIDv7
    investigation_id: UUIDv7
    tenant_id: TenantId
    causal_question: str                         # E.g. "What was the causal impact of carrier truck capacity shortage on cancellation rate?"
    treatment_variable: str                      # E.g. "carrier_truck_shortage" (Binary 0/1)
    outcome_variable: str                        # E.g. "order_cancelled" (Binary 0/1)
    unit_of_analysis: str                        # E.g. "order_id"
    target_population: str                       # E.g. "Orders originating at WH-MIDWEST-01 during Days 45–52"
    treatment_window_start: UtcDateTime
    treatment_window_end: UtcDateTime
    outcome_window_start: UtcDateTime
    outcome_window_end: UtcDateTime
    as_of_time: UtcDateTime
    pre_treatment_covariates: List[str]          # Confounders: customer_tenure, order_value, historical_frequency
    post_treatment_exclusions: List[str]         # Mediators/colliders: delivery_delay_hours, support_ticket_count
    estimand_type: EstimandType
    identification_strategy: IdentificationStrategy
    causal_dag_ref: str                          # Path or identifier of causal DAG
    explicit_assumptions: List[str]              # E.g. ["Exchangeability", "Positivity", "SUTVA", "No Unobserved Confounding"]
    estimator: EstimatorType
    overlap: OverlapDiagnostics
    point_estimate: float
    standard_error: float
    confidence_interval_95: Tuple[float, float]
    p_value: float
    sensitivity: SensitivityAnalysis
    subgroup_estimates: Dict[str, Tuple[float, float]] # E.g. {"TIER_ENTERPRISE": (0.042, 0.088)}
    limitations: List[str]
    reproducibility_seed: int
    study_digest: str                            # SHA-256 over study specification and dataset hash
    created_at: UtcDateTime
```

---

## 3. Mandatory Reporting Contract for Every Causal Result

Under `FR-ML-004` and `AC-006`, every causal evaluation or presentation to users/analysts must state:
1. **The Exact Causal Question**: What intervention contrast is being evaluated?
2. **Treatment Definition**: Explicit operationalization of treatment and control conditions.
3. **Outcome Definition**: Authoritative metric and observation window.
4. **Target Population & Scope**: Which cohorts the effect applies to, and explicitly which cohorts it does NOT apply to.
5. **Identification Assumptions**: Stated clearly (e.g. SUTVA, positivity, ignorability).
6. **Overlap Diagnostics**: Common support visualization/metrics; confirmation that propensity scores satisfy $0.05 \le e(X) \le 0.95$.
7. **Statistical Uncertainty**: 95% confidence interval and standard error—never a single raw scalar.
8. **Sensitivity to Unobserved Confounders**: E-value or Oster $\delta$ stating the magnitude of unobserved confounding required to reduce the effect to zero.
9. **Action Barrier**: Explicit statement: *"This causal estimate describes past or scenario-specific attribution and does not constitute authorization for operational action."*

---

## 4. Midwest Truck-Capacity Incident Causal Estimand

Under `SYNTHETIC-DATASET-SPEC.md` §6:
- **Causal Question**: What was the average treatment effect of the regional truck capacity shortage at `WH-MIDWEST-01` on the cancellation rate of outbound customer orders?
- **Unit of Analysis**: `order_id`.
- **Treatment ($T$)**:
  - $T=1$: Outbound shipments from `WH-MIDWEST-01` assigned to `CARRIER_REGIONAL_LOGISTICS` during Days 45–52.
  - $T=0$: Outbound shipments from internal control warehouses (`WH-WEST-01`) or expedited carriers (`CARRIER_AIR_EXPRESS`) during the identical window.
- **Outcome ($Y$)**: Binary order cancellation (`1 = CANCELLED`, `0 = COMPLETED`).
- **Confounders Adjusted**: `customer_tier`, `order_subtotal`, `shipping_service_level`, `product_category`.
- **Excluded Post-Treatment Variables**: `actual_dispatch_delay` (Mediator), `support_ticket_created` (Mediator).
- **Target Estimand**:
  $$\text{ATE} = \mathbb{E}[Y(T=1) - Y(T=0)]$$
- **Ground-Truth True ATE**: $+0.0660$ (+6.6% absolute increase).
- **Phase 04 Engineering Benchmark Gate (`NFR-AI-007`)**:
  $$|\widehat{\text{ATE}} - 0.0660| \le 0.0500$$
  The estimated ATE must fall within $[0.0160, 0.1160]$, and the nominal 95% confidence interval must cover the true value $0.0660$.

---

## 5. Causal Workflow and Failure Modes

```text
 [CausalStudy Proposed]
           │
           ▼
 [1. Pre-Treatment Covariate Audit] ──(Post-Treatment Found)──► REJECT (ERR_POST_TREATMENT_COLLIDER)
           │
           ▼
 [2. Temporal As-Of Audit] ─────────(Future Data Leak)────────► REJECT (ERR_TEMPORAL_LEAKAGE)
           │
           ▼
 [3. Positivity & Overlap Gate] ────(No Support / e(X)<0.05)──► HALT (ERR_OVERLAP_VIOLATION)
           │
           ▼
 [4. Deterministic Estimator] ──────(AIPW / TMLE)─────────────► Point Estimate + 95% CI
           │
           ▼
 [5. Sensitivity & Falsification] ──(Fragile to Confounders)──► FLAG SENSITIVE
           │
           ▼
 [6. Sealed CausalStudy Record] ────(SHA-256 Digest)──────────► Ingested as EvidenceRecord
```

---

## 6. Verification and Test Suite Mapping

- `tests/analytics/test_causal_study_contract.py`: Validates schema parsing, required fields, and enum validation.
- `tests/analytics/test_causal_overlap_diagnostics.py`: Injects complete non-overlap; verifies estimator halts with `ERR_OVERLAP_VIOLATION`.
- `tests/analytics/test_causal_temporal_leakage.py`: Injects post-treatment outcomes into covariate set; verifies rejection (`INV-DATA-001`).
- `tests/ai-evals/test_causal_synthetic_ate_benchmark.py`: Evaluates estimator against seeded Midwest scenario; verifies $|\widehat{\text{ATE}} - 0.0660| \le 0.05$ (`NFR-AI-007`).
- `tests/ai-evals/test_causal_sensitivity_bounds.py`: Computes E-value and Oster delta on synthetic benchmark.
