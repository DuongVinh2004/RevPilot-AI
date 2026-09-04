# Anomaly Detection Benchmark Protocol

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 02 — Detection and Analytics
Owner: AI/ML Architecture + Evaluation Engineering
Traceability: `BR-001`, `FR-DET-002`, `FR-ML-001`, `INV-DATA-001`, `NFR-AI-002`, `NFR-AI-004`, `AC-001`, `AC-002`, `AC-014`

---

## 1. Objectives and Protocol Principles

This protocol governs the offline evaluation, baseline benchmarking, and detector model selection for Phase 02 (Detection and Analytics).

### Protocol Invariants
1. **No LLM in Core Detection Loop (`NFR-AI-004`)**: Statistical baselines and anomaly detectors MUST execute deterministically without dependency on large language models.
2. **Anti-Fabrication Policy (`AC-014`)**: Numeric performance metrics are design targets or expected fixture values until recorded by an automated evaluation run. No benchmark result may be declared PASS without machine test evidence.
3. **Strict Rolling Time-Split (`INV-DATA-001`)**: All model fitting and baseline calibrations use historical data relative to the evaluation cut-off watermark. Zero future data leakage into past features is permitted.
4. **Air-Gapped Ground-Truth Access**: The benchmark harness accesses hidden scenario annotations in `ground_truth.incidents` strictly offline during scoring. Detectors and baselines have zero access to ground truth.

---

## 2. Baselines and Detector Algorithms

### 2.1. Statistical Baselines Catalog

| Baseline ID | Method Name | Formulation / Logic | Primary Purpose |
|---|---|---|---|
| `BASE-SEASONAL-NAIVE-001` | Seasonal Naive | $\hat{Y}_t = Y_{t - s}$ (where $s=7$ days for daily grain, $s=24$ for hourly) | Primary benchmark baseline. Captures weekly recurring cycles. |
| `BASE-ROLLING-STATS-001` | Rolling Mean / Median | Median of trailing $W=14$ days, with Interquartile Range (IQR) bounds | Robust to transient outliers. |
| `BASE-EWMA-001` | Exponentially Weighted Moving Average | $S_t = \alpha Y_t + (1 - \alpha) S_{t-1}$ with $\alpha = 0.2$ | Smooth trend tracking with low memory footprint. |
| `BASE-STL-001` | STL Decomposition | Seasonal-Trend decomposition using LOESS ($Y_t = T_t + S_t + R_t$) | Separates cyclic seasonality from secular trend. |

### 2.2. Candidate Detection Methods

1. **STL Residual Detector (`DET-STL-RESIDUAL-001`)**:
   - Algorithm: Extracts remainder component $R_t = Y_t - \hat{T}_t - \hat{S}_t$.
   - Anomaly Condition: $|R_t| > k \cdot \sigma_R$ (where default $k = 3.0$ tuned on calibration split).
   - Strengths: Highly interpretable, low computational latency (< 5ms per series), handles strong seasonality.
2. **Change-Point Detector (`DET-CHANGEPOINT-PELT-001`)**:
   - Algorithm: Pruned Exact Linear Time (PELT) change-point detection on mean and variance.
   - Anomaly Condition: Structural shift detected within observation window with penalty $\beta$.
   - Strengths: Accurately localizes step-level operational disruptions (such as carrier capacity collapse).
3. **Isolation Forest (`DET-ISOLATION-FOREST-001`)**:
   - Algorithm: Non-parametric multi-dimensional tree isolation on feature vectors (metric value, lag-1, lag-7, moving variance).
   - Anomaly Condition: Anomaly score $s(x, n) > 0.65$.
   - Strengths: Captures multi-variate interactions across metrics and dimensional slices.

### 2.3. Model Selection and Promotion Criteria
A candidate detector is approved for production deployment ONLY IF:
1. It statistically beats `BASE-SEASONAL-NAIVE-001` on F1-score by >= 15% on the benchmark validation split.
2. Its False Positive Rate (FPR) remains <= 0.05 on normal operational baseline windows.
3. It detects the injected Midwest truck disruption (`INC-SYNTH-TRUCK-001`) within <= 48 hours of causal disruption onset (Lead-Time Target).
4. Execution time is < 50ms per series to honor synchronous API latency targets (`NFR-LAT-001`).

---

## 3. Benchmark Evaluation Metrics

Every evaluation run records the following machine-verifiable metrics:

| Metric | Definition | Minimum Acceptance Target |
|---|---|---:|
| **Precision** | $TP / (TP + FP)$ on injected incident windows | >= 0.80 |
| **Recall** | $TP / (TP + FN)$ on known injected incidents | >= 0.85 |
| **F1-Score** | $2 \cdot (Precision \cdot Recall) / (Precision + Recall)$ | >= 0.82 |
| **False Positive Rate (FPR)** | $FP / (FP + TN)$ during clean control windows | <= 0.05 |
| **Detection Lead Time** | Hours elapsed between causal disruption start and first anomaly alarm | <= 48 hours |
| **Alert Volume** | Average alarms per tenant per week during normal operation | <= 2.0 alerts/week |
| **Localization Accuracy** | Fraction of anomalies whose top-1 localized dimension matches true cause scope | >= 0.85 |
| **Prediction Interval Coverage**| Percentage of baseline observations falling within estimated 95% interval | 93.0% to 97.0% |

---

## 4. Evaluation Protocol and Rolling Time-Split

```text
Day 1                    Day 30        Day 44             Day 52          Day 60
  ├────────────────────────┼─────────────┼──────────────────┼───────────────┤
  │    Train (Fitting)     │ Calibration │ Incident Active  │ Post-Incident │
  │    30-day baseline     │ 14-day hold │ (Midwest Truck)  │ Recovery      │
  └────────────────────────┴─────────────┴──────────────────┴───────────────┘
  ▲                        ▲             ▲                  ▲
  T0                       T_calib       T_eval_start       T_eval_end
```

### 4.1. Step-by-Step Evaluation Procedure
1. **Data Load**: Load generated dataset from pinned seed (Seed `42` for DEVELOPMENT, `1337` for DEMO) verified against `manifest.json`.
2. **Train/Calibration Partition**: Fit baseline models on Days 1 to 30. Tune detector threshold $k$ on Days 31 to 44 to satisfy FPR <= 0.05.
3. **Simulated Real-Time Rolling Step**:
   - For each day $t$ from Day 45 to Day 60:
   - Set as-of watermark $:as\_of\_time = t$.
   - Execute Metric Service query strictly filtering `event_time <= t`.
   - Feed time-series slice to detector.
   - Record alarm output, timestamp, actual value, expected interval, and score.
4. **Scoring against Ground Truth**:
   - Authenticate evaluation runner as `revpilot_evaluator`.
   - Read `ground_truth.incidents`.
   - Score Precision, Recall, Lead Time, and Localization Accuracy.
5. **Report Emission**: Write immutable `EvalRun` record to evaluation catalog.
