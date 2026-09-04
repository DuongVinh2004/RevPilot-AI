# Anomaly Localization and Dimensional Drill-Down Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 02 — Detection and Analytics
Owner: Analytics Architecture + Domain Architecture
Traceability: `BR-001`, `FR-DET-004`, `FR-INV-004`, `INV-TEN-001`, `INV-AI-001`, `NFR-AI-004`, `AC-002`

---

## 1. Scope and Analytical Guardrails

Anomaly localization isolates which dimensional slices (e.g., specific carrier, warehouse facility, region, customer segment) contribute disproportionately to an aggregate business metric anomaly.

### Guardrails and Invariants
1. **Association, Not Causation (`INV-AI-001`)**: Localization identifies statistical concentration and correlation in observed data. It DOES NOT prove that the isolated segment is the root cause. All localization outputs MUST use associative language (e.g., "concentrated in", "correlated with") and explicitly disclaim causal certainty.
2. **Strict Parameter Allowlists (`FR-INV-004`)**: Slicing executes strictly across dimensions defined in `docs/07-data-platform/METRIC-REGISTRY.md`. Ad-hoc or caller-supplied SQL expressions are prohibited.
3. **Tenant-Enforced Scoping (`INV-TEN-001`)**: Slicing queries inherit verified server-side `TenantContext`. Cross-tenant aggregations are impossible.
4. **Minimum Sample Size and Noise Suppression**: Slices with insufficient sample volume are suppressed or aggregated into an "OTHER_UNSTABLE" category to prevent small-sample volatility false alarms.

---

## 2. Localization Algorithm and Mathematical Framing

### 2.1. Segment Contribution Calculation
For an aggregate metric $M = \frac{N}{D}$ (e.g., cancellation rate):
- Let $k \in K$ represent discrete segments under dimension $D_i$ (e.g., `carrier_id`).
- For each segment $k$, observe actual numerator $n_k$, denominator $d_k$, and actual segment rate $m_k = \frac{n_k}{d_k}$.
- Let $\hat{m}_k$ be the expected baseline rate for segment $k$.
- Excess anomalous volume contributed by segment $k$:
  $$\Delta_k = n_k - (d_k \cdot \hat{m}_k)$$
- Percentage contribution to total aggregate excess:
  $$\text{ContributionPct}_k = \frac{\Delta_k}{\sum_{j \in K} \Delta_j} \times 100\%$$

### 2.2. Minimum Sample-Size Thresholds
To ensure statistical significance and avoid small-sample distortion:
- Ratio Metrics (e.g., `cancellation_rate`): Minimum denominator $d_k \ge 30$ observations in window. Slices with $d_k < 30$ are marked `INSUFFICIENT_SAMPLE_SIZE` and suppressed from top-contributor ranking.
- Volume Metrics (e.g., `revenue_at_risk`): Minimum total order count $d_k \ge 10$.

### 2.3. Multiple Testing Correction
When drilling down across dozens of dimensions simultaneously, false discovery risk increases. The localization engine applies Benjamini-Hochberg False Discovery Rate (FDR) control at $\alpha = 0.05$ across evaluated segments.

---

## 3. Localization Result Schema (`AnomalyLocalization`)

```json
{
  "$schema": "https://revpilot.ai/schemas/anomaly-localization.v1.json",
  "localization_id": "loc_01h8cdef1234567890",
  "anomaly_id": "anm_01h8abc1234567890",
  "tenant_id": "ten_01h7abcde123456789",
  "metric_id": "METRIC-001",
  "evaluated_at": "2026-02-15T00:00:00Z",
  "as_of_time": "2026-02-15T00:00:00Z",
  "dimension_evaluated": "carrier_id",
  "data_coverage_pct": 98.4,
  "top_contributing_segments": [
    {
      "rank": 1,
      "segment_value": "CARRIER_REGIONAL_LOGISTICS",
      "actual_value": 0.0842,
      "baseline_expected_value": 0.0180,
      "relative_lift": 4.67,
      "sample_size": 499,
      "excess_volume": 33.0,
      "contribution_pct": 78.5,
      "statistical_significance_pvalue": 0.00001,
      "fdr_rejected": true
    },
    {
      "rank": 2,
      "segment_value": "CARRIER_AIR_EXPRESS",
      "actual_value": 0.0191,
      "baseline_expected_value": 0.0175,
      "relative_lift": 1.09,
      "sample_size": 512,
      "excess_volume": 0.8,
      "contribution_pct": 1.9,
      "statistical_significance_pvalue": 0.6200,
      "fdr_rejected": false
    }
  ],
  "suppressed_segments_count": 4,
  "association_summary": "Cancellation rate spike is concentrated in CARRIER_REGIONAL_LOGISTICS, accounting for 78.5% of excess cancelled orders. This reflects an observed association; causal investigation is required to establish underlying root causes.",
  "diagnostic_status": "ACTIONABLE_FOR_INVESTIGATION",
  "lineage_trace_id": "lin_01h8abcdef9876543210"
}
```

---

## 4. Multi-Dimensional Interaction (Hierarchical Drill-Down)

When single-dimension drill-down reveals a leading segment, the engine supports conditional two-level drill-down:
1. Level 1: `carrier_id = 'CARRIER_REGIONAL_LOGISTICS'`
2. Level 2 (Conditional): Drill down on `warehouse_id` restricted to Level 1 slice:
   - Evaluates: `WH-MIDWEST-01` vs `WH-WEST-01` within `CARRIER_REGIONAL_LOGISTICS`.
   - In Midwest scenario: Pinpoints `WH-MIDWEST-01` as contributing 94% of the carrier's excess delay.
3. Stop Rule: Recursion stops at depth = 2 to prevent combinatorial explosion and overfitting to noise.
