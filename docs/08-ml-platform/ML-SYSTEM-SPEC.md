# ML System Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 02 — Detection and Analytics
Owner: AI/ML Architecture
Traceability: `BR-001`, `BR-002`, `FR-ML-001..004`, `INV-DATA-001`, `INV-AI-001..002`, `NFR-AI-001..007`, `NFR-COST-001`, `ADR-0011`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Scope, Model Families, and Anti-Conflation Rules

The RevPilot Machine Learning Platform segregates statistical and learning tasks into distinct, governed artifact families:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                 RevPilot ML Artifact Families                           │
├───────────────────┬──────────────────────┬──────────────────────┬───────────────────────┤
│ Model Family      │ Primary Algorithm    │ Evaluated Target     │ Governing Phase       │
├───────────────────┼──────────────────────┼──────────────────────┼───────────────────────┤
│ 1. Anomaly Detect │ STL / PELT / IsoFor  │ Residual Divergence  │ Phase 02 (Detection)  │
│ 2. Forecasting    │ ETS / Prophet / ARIMA│ Rolling Trajectory   │ Phase 02 (Baselines)  │
│ 3. Churn Scoring  │ Calibrated GBDT      │ Propensity to Churn  │ Phase 05 (Uplift)     │
│ 4. Causal Effect  │ DML / IPW / EconML   │ Incremental ATE/CATE │ Phase 04 (Causal AI)  │
│ 5. Decision Opt   │ Utility Linear Prog  │ Constrained Action   │ Phase 05 (Decisions)  │
└───────────────────┴──────────────────────┴──────────────────────┴───────────────────────┘
```

### Core Invariants
1. **No Churn-for-Uplift Substitution (`FR-ML-003`)**: Churn probability indicates baseline attrition risk; it DOES NOT measure whether an intervention will retain the customer. Churn models are strictly barred from recommending actions without causal uplift verification.
2. **Deterministic Baseline Fallback**: If an anomaly detector encounters a runtime failure, missing features, or timeout, the system automatically falls back to `BASE-SEASONAL-NAIVE-001` or `BASE-ROLLING-STATS-001`. Fallback outputs are explicitly flagged `is_fallback_baseline = true`.
3. **Strict Time-Split and Anti-Leakage (`INV-DATA-001`)**: No feature may use future observations relative to the model's `as_of` watermark.

---

## 2. Phase 02 Detection Model Specifications

### 2.1. Model Artifact Metadata Schema (`ModelArtifact`)
Every deployed detection model or baseline has an immutable versioned descriptor:
```json
{
  "artifact_id": "art_stl_residual_v1_0_0",
  "name": "STL Residual Detector",
  "version": "1.0.0",
  "family": "ANOMALY_DETECTION",
  "framework": "statsmodels_0.14.0",
  "code_digest": "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
  "trained_on_manifest_id": "mnf_01h8abc1234567890",
  "parameters": {
    "seasonal_period": 7,
    "robust_loess": true,
    "threshold_sigma_multiplier": 3.0
  },
  "evaluation_scores": {
    "f1_score": 0.884,
    "false_positive_rate": 0.031,
    "lead_time_hours": 36.0
  },
  "release_gate_status": "APPROVED_FOR_STAGING"
}
```

---

## 3. Serving Contract and Inference Runtime

### 3.1. Inference Request (`ModelInferenceRequest`)
```json
{
  "request_id": "inf_01h8bcde987654321",
  "tenant_id": "ten_01h7abcde123456789",
  "artifact_id": "art_stl_residual_v1_0_0",
  "as_of_time": "2026-02-15T00:00:00Z",
  "time_series_data": [
    {"timestamp": "2026-02-08T00:00:00Z", "value": 0.0182},
    {"timestamp": "2026-02-09T00:00:00Z", "value": 0.0179},
    {"timestamp": "2026-02-14T00:00:00Z", "value": 0.0842}
  ],
  "timeout_ms": 200
}
```

### 3.2. Inference Response (`ModelInferenceResponse`)
```json
{
  "request_id": "inf_01h8bcde987654321",
  "artifact_id": "art_stl_residual_v1_0_0",
  "is_anomaly": true,
  "anomaly_score": 0.8842,
  "expected_point_estimate": 0.0181,
  "expected_interval": [0.0112, 0.0250],
  "residual_deviation_sigma": 4.12,
  "status": "SUCCESS",
  "is_fallback_baseline": false,
  "executed_in_ms": 12.4
}
```

---

## 4. Model Drift, Calibration, and Monitoring

1. **Prediction Interval Calibration**: The platform evaluates empirical coverage of prediction intervals weekly. If observed coverage drops below 90% (for a nominal 95% interval), the model is flagged `NEEDS_RECALIBRATION`.
2. **Concept Drift Detection**: The distribution of detection scores is monitored using Kolmogorov-Smirnov tests against the calibration baseline. Statistically significant distribution shifts emit alerts to the ML platform owner.
3. **No Automatic Production Promotion (`NFR-AI-001`)**: Retrained models are never automatically deployed to live production inference without passing the release gates in `docs/20-evaluation/MODEL-RELEASE-PROCESS.md`.

---

## 5. Phase 05 Churn Prediction and Calibration Contract

### 5.1. Problem Formulation and Target Semantics
- **Target Label ($Y_i$)**: Binary indicator of account churn or contract non-renewal:
  $$Y_i = \mathbb{I}(\text{status}_i(t_{\text{as\_of}} + H) \in \{\text{CANCELLED}, \text{EXPIRED}, \text{NON\_RENEWED}\})$$
- **Prediction Horizon ($H$)**: 30 days forward-looking window.
- **Observation Window**: 90 days trailing behavioral data ($[t_{\text{as\_of}} - 90\text{d}, t_{\text{as\_of}}]$).
- **Censoring and Treatment Contamination Control**: Accounts that received promotional incentives or active retention treatment during the evaluation window are flagged and censored to avoid treatment contamination in baseline risk modeling.

### 5.2. Probability Calibration Standard (`NFR-AI-005`)
Raw GBDT margin outputs are uncalibrated and cannot be interpreted as empirical probabilities.
- **Calibration Methods**: Platt Scaling (Sigmoid logistic fit) or Isotonic Regression fit on a held-out calibration split (20% of training population).
- **Quality Gate**: Expected Calibration Error (ECE) with $M = 10$ equal-frequency probability bins:
  $$\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right| \le 0.0500 \quad (5.0\%)$$
- **Strict Prohibition**: A churn model with $\text{ECE} > 0.05$ fails verification and cannot be deployed (`ERR_UNCALIBRATED_PROBABILITY`).

### 5.3. Churn Scoring Contract Schema
```python
class ChurnPredictionRecord(BaseModel):
    prediction_id: UUIDv7
    tenant_id: TenantId
    customer_id: str
    as_of_time: UtcDateTime
    model_artifact_id: str                 # E.g. "art_gbdt_churn_v2_1_0"
    calibrated_probability: float = Field(ge=0.0, le=1.0)
    risk_tier: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ece_at_release: float
    feature_snapshot_digest: str           # SHA-256 over input feature vector
    is_treatment_contaminated: bool
    created_at: UtcDateTime
```

---

## 6. Local Feature Explanations (SHAP) and Safety Boundaries

### 6.1. Epistemic Limitation of SHAP Values
Feature attributions (TreeSHAP) quantify marginal contribution to the model's scoring function:
$$\phi_j(x) = \sum_{S \subseteq F \setminus \{j\}} \frac{|S|!(|F| - |S| - 1)!}{|F|!} \left[ f(S \cup \{j\}) - f(S) \right]$$
**Mandatory Epistemic Boundary (`INV-AI-001`)**:
- SHAP values quantify **statistical association within the model**, NOT causal mechanisms in reality.
- A high positive SHAP value for `support_tickets_count` means the model increased predicted risk when tickets were high; it does NOT prove that support tickets caused the churn, nor does it guarantee that resolving tickets will retain the customer.
- Using SHAP values as proof of treatment efficacy is strictly rejected (`ERR_SHAP_AS_CAUSATION`).

### 6.2. Local Explanation Schema
```python
class FeatureAttribution(BaseModel):
    feature_name: str
    observed_value: float
    baseline_value: float
    attribution_value: float               # SHAP value
    relative_importance: float             # Normalized absolute attribution

class LocalExplanationRecord(BaseModel):
    explanation_id: UUIDv7
    prediction_id: UUIDv7
    tenant_id: TenantId
    customer_id: str
    top_attributions: List[FeatureAttribution] # Top 5 factors
    epistemic_warning: str = "Feature attributions describe model statistical associations, not real-world causal mechanisms."
    created_at: UtcDateTime
```
