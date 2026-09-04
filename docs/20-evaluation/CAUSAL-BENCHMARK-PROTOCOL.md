# Phase 04 Causal Inference Benchmark and RCA Protocol

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 04 — Hypothesis, Causal Analysis, and Verification (Rails 10, 12)
Owner: AI Evaluation Architecture / Econometrics Engineering
Measurement State: All performance numbers herein are strictly `BENCHMARK GATES` or `DESIGN TARGETS`. There are zero measured results reported herein (`AC-014`).
Traceability: `BR-001`, `BR-002`, `FR-RCA-001..002`, `FR-ML-003..004`, `INV-AI-001..002`, `INV-DATA-001`, `INV-TEN-001..003`, `NFR-AI-001..002`, `NFR-AI-007`, `AC-004`, `AC-006`, `AC-014`

---

## 1. Benchmark Scope and Evaluation Philosophy

Phase 04 evaluates the system's ability to discriminate between superficial correlation, unobserved confounding, and true causal mechanisms behind business revenue anomalies. 

### Measurement Invariant (`AC-014`)
This protocol specifies benchmark evaluation gates and test harnesses against seeded synthetic ground truth. Actual measured results belong exclusively in dated evaluation run manifests (`EvalRun`), never in canonical design specifications.

---

## 2. Injected Synthetic Causal Incident Benchmark (`INC-SYNTH-TRUCK-001`)

### 2.1 Benchmark Ground Truth Parameters
- **Dataset Seed**: `SEED-42-DETERMINISTIC` (Development Profile) and `SEED-1337-DEMO`.
- **Target Anomaly**: Order cancellation spike during Days 45–52 (`2026-02-14` to `2026-02-21`).
- **Target Population**: Outbound ground orders from warehouse `WH-MIDWEST-01`.
- **True Intervention Contrast**:
  - $T=1$: Shipments routed via `CARRIER_REGIONAL_LOGISTICS`.
  - $T=0$: Shipments routed via alternative carriers or other facilities.
- **True Estimand**:
  $$\text{ATE}^* = \mathbb{E}[Y(T=1) - Y(T=0)] = +0.0660 \quad (+6.6\% \text{ absolute})$$
- **True Affected Revenue**: $142,560.00 USD (482 affected orders).
- **True Confounders**:
  1. $X_{\text{storm}}$: Regional storm causing non-causal shipping delays in Northeast.
  2. $X_{\text{promo}}$: Marketing category campaign shifting baseline order volumes by $+25\%$.

---

## 3. Causal Benchmark Evaluation Gates

| Evaluation Gate ID | Target Requirement | Evaluation SLI | Benchmark Pass Gate | Metric Definition |
|---|---|---|---|---|
| `GATE-CAUSAL-ATE-ERR` | `NFR-AI-007` | Absolute ATE Error | $\le 0.0500$ | $|\widehat{\text{ATE}} - 0.0660| \le 0.0500$ ($0.0160 \le \widehat{\text{ATE}} \le 0.1160$) |
| `GATE-CAUSAL-CI-COV` | `FR-ML-004`, `AC-006` | 95% CI Coverage | $\ge 90.0\%$ | 95% confidence interval spans true value $0.0660$ across repeated folds |
| `GATE-CAUSAL-DIRECTION`| `FR-ML-004` | Direction Correctness | $100\%$ | $\widehat{\text{ATE}} > 0$ and $p < 0.01$ (Statistically significant positive increase) |
| `GATE-CAUSAL-OVERLAP` | `AC-006` | Overlap Detection | $100\%$ | Flags `positivity_satisfied=True` on Midwest cohort; halts on non-overlap cohorts |
| `GATE-CAUSAL-SENSITIVITY`| `AC-006` | Sensitivity Disclosure | $100\%$ | E-value computed and reported; confirms effect robust up to E-value $\ge 1.80$ |
| `GATE-RCA-TOP1` | `NFR-AI-002` | RCA Top-1 Accuracy | $\ge 0.80$ | Injected truck capacity shortage ranked as primary root cause |
| `GATE-RCA-TOP3` | `NFR-AI-002` | RCA Top-3 Accuracy | $\ge 0.95$ | True root cause included in top 3 ranked hypotheses |
| `GATE-DECOY-REFUTATION`| `FR-RCA-001` | Decoy Refutation Rate | $100\%$ | Both payment outage and product defect decoys marked `REFUTED` |
| `GATE-UNSUPPORTED-CLAIMS`| `INV-AI-001` | Unsupported Claim Rate | Exactly $0.00\%$ | Verifier catches and rejects 100% of claims lacking evidence |
| `GATE-TIME-LEAKAGE` | `INV-DATA-001` | Lookahead Leakage Rate | Exactly $0.00\%$ | Zero records timestamped $> \text{as\_of\_time}$ accessed by causal estimator |
| `GATE-AIRGAP-ISOLATION`| `INV-TEN-001` | Ground-Truth Read Leak | Exactly $0.00\%$ | Zero access to `ground_truth` schema by application runtime role |

---

## 4. Benchmark Execution Harness

The causal benchmark suite executes as an isolated evaluation job authenticated as `revpilot_evaluator`:

```bash
# 1. Run Causal Estimand & ATE Benchmark (NFR-AI-007)
pytest tests/ai-evals/test_causal_synthetic_ate_benchmark.py -v --tb=short

# 2. Run Causal Overlap and Positivity Diagnostics
pytest tests/analytics/test_causal_overlap_diagnostics.py -v --tb=short

# 3. Run Causal Sensitivity Analysis (E-value & Oster Delta)
pytest tests/ai-evals/test_causal_sensitivity_bounds.py -v --tb=short

# 4. Run Root Cause Analysis (RCA) Top-1 / Top-3 Benchmark (NFR-AI-002)
pytest tests/ai-evals/test_competing_hypothesis_ranking.py -v --tb=short

# 5. Run Decoy Refutation and Unsupported Claim Verification
pytest tests/ai-evals/test_unsupported_claim_rejection.py -v --tb=short
pytest tests/ai-evals/test_decoy_hypothesis_refutation.py -v --tb=short

# 6. Run Time-Travel Anti-Leakage Audit
pytest tests/analytics/test_causal_temporal_leakage.py -v --tb=short
```

---

## 5. Failure Taxonomy and Regression Policy

If an evaluation run fails any gate:
1. **Overlap Failure ($e(X) < 0.05$)**: Study halts with `ERR_OVERLAP_VIOLATION`. The estimator must not force extrapolation into areas without common support.
2. **Covariate Leakage**: If post-treatment variables are detected in adjustment set, test fails with `ERR_POST_TREATMENT_COLLIDER`.
3. **Decoy Failure**: If payment outage or product defect is ranked above Midwest truck capacity, test fails with `ERR_DECOY_ACCEPTED`.
4. **Target Deviation**: If $|\widehat{\text{ATE}} - 0.0660| > 0.0500$, test fails `GATE-CAUSAL-ATE-ERR`. Phase 04 remains blocked from release.
