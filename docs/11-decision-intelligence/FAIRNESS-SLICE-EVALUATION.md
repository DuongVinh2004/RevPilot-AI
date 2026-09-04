# Fairness, Subgroup Slices, and Disparity Evaluation Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 05 — Churn, Uplift, and Decision Optimization (Rails 10, 13)
Owner: AI Ethics and Governance / Evaluation Engineering
Measurement State: Slicing thresholds herein are `BENCHMARK GATES` and `DESIGN TARGETS`. There are zero compliance certifications or fabricated passes reported herein (`AC-014`).
Traceability: `BR-002`, `FR-ML-002..003`, `INV-AI-001`, `INV-PRV-001`, `NFR-AI-005..006`, `AC-014`

---

## 1. Scope and Objective

Machine learning models and decision optimizers must perform reliably and equitably across heterogeneous business segments. This specification defines slice-based evaluation protocols for churn calibration, uplift accuracy, and treatment allocation rates across operational and demographic cohorts.

### 1.1 Non-Negotiable Invariants
1. **No Unmeasured Compliance Claims (`AC-014`)**: The system must never assert "fairness certified", "bias-free", or "regulatory compliant". It only produces dated empirical disparity audits (`DisparityAuditReport`).
2. **Small-Sample Noise Suppression**: Any subgroup slice with sample size $N < 50$ is marked `INSUFFICIENT_SAMPLE`. Metrics on unstable small samples are suppressed to prevent noisy or misleading assertions.
3. **Privacy Minimization (`INV-PRV-001`)**: Slice definitions are based on business-operational dimensions (e.g. customer tier, geographic region, contract tenure, fulfillment carrier). Sensitive personal demographics are not collected or inferred.

---

## 2. Business-Relevant Slice Taxonomy

Models are audited across 4 standard operational slice families:

| Slice Dimension | Cohorts | Minimum Sample Size ($N_{\min}$) | Audit Target |
|---|---|---|---|
| **Customer Tier** | `ENTERPRISE`, `MID_MARKET`, `SMB` | 50 | Calibration disparity $\Delta \text{ECE} \le 0.030$ |
| **Geographic Region** | `US-MIDWEST`, `US-WEST`, `US-NORTHEAST`, `US-SOUTH` | 50 | Uplift parity ratio $0.80 \le \text{Ratio} \le 1.25$ |
| **Contract Tenure** | `< 12 \text{ months}`, `12–36 \text{ months}`, `> 36 \text{ months}` | 50 | Error rate parity |
| **Logistics Fulfillment**| Carrier tier (`REGIONAL`, `NATIONAL_GROUND`, `EXPEDITED`) | 50 | Detection and treatment coverage |

---

## 3. Disparity Metrics and Evaluation Thresholds

### 3.1. Calibration Disparity by Slice
The difference in Expected Calibration Error between any two qualified slices $s_1, s_2$:
$$\Delta \text{ECE}(s_1, s_2) = |\text{ECE}(s_1) - \text{ECE}(s_2)| \le 0.0300 \quad (3.0\%)$$

### 3.2. Treatment Allocation Disparity
For any two customer tiers with comparable uplift ($\tau(s_1) \approx \tau(s_2)$), the ratio of recommendation rates must satisfy:
$$0.80 \le \frac{P(\text{Recommend} \mid s_1, \tau \ge \tau_0)}{P(\text{Recommend} \mid s_2, \tau \ge \tau_0)} \le 1.25$$

---

## 4. Canonical Slice Audit Schema

```python
class SliceMetric(BaseModel):
    slice_dimension: str                   # E.g. "customer_tier"
    slice_value: str                       # E.g. "SMB"
    sample_size: int
    is_statistically_reliable: bool        # True if sample_size >= 50
    pr_auc: Optional[float] = None
    ece: Optional[float] = None
    mean_uplift_cate: Optional[float] = None
    treatment_recommendation_rate: Optional[float] = None
    evaluation_status: Literal["EVALUATED", "INSUFFICIENT_SAMPLE", "SUPPRESSED"]

class DisparityAuditReport(BaseModel):
    report_id: UUIDv7
    tenant_id: TenantId
    model_artifact_id: str
    decision_policy_id: str
    as_of_time: UtcDateTime
    evaluated_slices: List[SliceMetric]
    max_calibration_disparity: float
    max_allocation_disparity_ratio: float
    governance_status: Literal["PASS", "NEEDS_REVIEW", "INSUFFICIENT_DATA"]
    audit_digest: str
    created_at: UtcDateTime
```

---

## 5. Verification Commands

```bash
pytest tests/ai-evals/test_fairness_slice_evaluation.py -v --tb=short
pytest tests/analytics/test_small_sample_slice_suppression.py -v --tb=short
```
