# Phase 05 Uplift and Heterogeneous Treatment Effect Benchmark Protocol

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 05 — Churn, Uplift, and Decision Optimization (Rails 12, 13)
Owner: AI/ML Architecture / Econometrics
Measurement State: All figures herein are `BENCHMARK GATES` and `DESIGN TARGETS`. There are zero measured results reported herein (`AC-014`).
Traceability: `BR-002`, `BR-005`, `FR-ML-003`, `FR-ML-004`, `INV-AI-001`, `INV-DATA-001`, `INV-TEN-001..003`, `NFR-AI-006..007`, `NFR-COST-001`, `AC-006`, `AC-007`, `AC-014`

---

## 1. Principles of Heterogeneous Treatment Effect and Uplift Modeling

Uplift modeling in RevPilot AI isolates the **incremental causal benefit** of an intervention on an individual customer account:

$$\tau(X_i) = \mathbb{E}[Y_i(1) - Y_i(0) \mid X_i]$$

Targeting customers based purely on high baseline churn risk $P(Y=1 \mid X)$ wastes capital on accounts that would churn regardless of treatment ("lost causes") or disturbs accounts that would remain loyal without treatment ("sleeping dogs" / negative uplift). Uplift models isolate the "persuadables" where $\tau(X_i) > 0$.

### 1.1 Non-Negotiable Invariants
1. **Separation of Risk from Uplift (`FR-ML-003`)**: Churn risk and uplift score are distinct mathematical objects. A high-risk customer with zero or negative uplift cannot be targeted for intervention.
2. **Positivity and Overlap Requirement**: Uplift models require empirical overlap across covariates $X$ in historical or synthetic randomized trials ($0.05 \le e(X) \le 0.95$). If a subpopulation lacks common support, the model must output `ERR_OVERLAP_VIOLATION`.
3. **No Uncalibrated Gain Claims**: Uplift scores cannot be cited as guaranteed monetary savings without accounting for treatment cost, uncertainty intervals, and sensitivity bounds.

---

## 2. Canonical Uplift Model Contract

```python
class UpliftEstimatorType(str, Enum):
    T_LEARNER = "T_LEARNER"             # Two separate GBDTs for treatment and control
    S_LEARNER = "S_LEARNER"             # Single GBDT with treatment feature
    X_LEARNER = "X_LEARNER"             # Two-stage cross-learner for imbalanced treatment
    CAUSAL_FOREST = "CAUSAL_FOREST"     # Non-parametric recursive splitting on treatment effect

class UpliftScoreRecord(BaseModel):
    score_id: UUIDv7
    tenant_id: TenantId
    customer_id: str
    intervention_type: str             # E.g. "SERVICE_CREDIT_VOUCHER"
    as_of_time: UtcDateTime
    model_artifact_id: str
    cate_estimate: float               # Estimated incremental retention probability
    standard_error: float
    confidence_interval_95: Tuple[float, float]
    persuadability_segment: Literal["PERSUADABLE", "SURE_THING", "LOST_CAUSE", "SLEEPING_DOG"]
    overlap_satisfied: bool
    feature_snapshot_digest: str
    created_at: UtcDateTime
```

---

## 3. Uplift Evaluation Scenarios and Synthetic Benchmarks

The benchmark tests the uplift engine across 4 synthetic population cohorts:

1. **Cohort A — Persuadables ($\tau > 0$)**: Customers who stay if and only if treated ($Y(1) = 0, Y(0) = 1$). Target gate: CATE point estimate $> 0.1500$.
2. **Cohort B — Lost Causes ($\tau \approx 0, P(\text{churn}) \approx 1$)**: High-risk customers who churn regardless of treatment ($Y(1) = 1, Y(0) = 1$). Target gate: CATE point estimate $\le 0.0200$.
3. **Cohort C — Sure Things ($\tau \approx 0, P(\text{churn}) \approx 0$)**: Low-risk customers who stay regardless of treatment ($Y(1) = 0, Y(0) = 0$). Target gate: CATE point estimate $\le 0.0200$.
4. **Cohort D — Sleeping Dogs ($\tau < 0$)**: Customers annoyed by unsolicited outreach ($Y(1) = 1, Y(0) = 0$). Target gate: CATE point estimate $< -0.0500$.

---

## 4. Benchmark Evaluation Gates

| Evaluation Gate ID | Target Requirement | Evaluation SLI | Benchmark Pass Gate | Metric Definition |
|---|---|---|---|---|
| `GATE-UPLIFT-QINI` | `NFR-AI-006` | Normalized Qini Score | $> 0.2000$ | Normalized area between model uplift curve and random targeting |
| `GATE-UPLIFT-AUUC` | `NFR-AI-006` | Area Under Uplift Curve | Beats Random by $\ge 15\%$ | Cumulative incremental churn reduction across top 30% scored cohort |
| `GATE-UPLIFT-CATE-ERR`| `NFR-AI-007` | Mean Absolute CATE Error | $\le 0.0400$ | Mean $|\widehat{\tau}(X_i) - \tau^*(X_i)|$ against synthetic ground truth |
| `GATE-UPLIFT-OVERLAP`| `AC-006` | Common Support Audit | $100\%$ | Halts with `ERR_OVERLAP_VIOLATION` on unrepresented covariate regions |
| `GATE-SLEEPING-DOGS` | `FR-ML-003` | Negative Uplift Detection | $\ge 95\%$ | Identifies negative effect cohort and prevents treatment allocation |
| `GATE-POLICY-VALUE` | `BR-002` | Net Value per Treated | $> 0$ USD | Policy net utility $\mathbb{E}[U(\pi)] > \text{Cost}(\pi)$ |

---

## 5. Execution Commands for Offline Evaluation

```bash
# 1. Run Uplift Model Qini and Cumulative Gain Curve Benchmark (NFR-AI-006)
pytest tests/ai-evals/test_uplift_qini_benchmark.py -v --tb=short

# 2. Run Heterogeneous Treatment Effect Error Evaluation (NFR-AI-007)
pytest tests/ai-evals/test_uplift_cate_accuracy.py -v --tb=short

# 3. Run Sleeping Dog and Negative Effect Rejection Test
pytest tests/ai-evals/test_uplift_negative_effect_detection.py -v --tb=short

# 4. Run Overlap and Positivity Diagnostics
pytest tests/analytics/test_uplift_overlap_diagnostics.py -v --tb=short
```
