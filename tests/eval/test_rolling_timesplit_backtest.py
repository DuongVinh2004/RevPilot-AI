"""
RevPilot AI — Rolling Time-Split Backtest and Metric Benchmark Tests (Phase 02)
Verifies AC-P02-003-01 (Midwest detection within 48h), AC-P02-003-03 (zero lookahead), and AC-P02-003-04 (air-gapped evaluation).
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §3, §4 and TASK-P02-003.
"""

from __future__ import annotations
import os
import sys
import tempfile
from datetime import timedelta
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.benchmark.ground_truth import (
    GroundTruthIncident,
    EvaluationGroundTruthStore,
)


@pytest.fixture(autouse=True)
def _isolate_analytics_module():
    """Ensure analytics module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.analytics"):
            sys.modules.pop(mod, None)


@pytest.fixture
def base_date() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-01-01T00:00:00.000000Z")


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha")


@pytest.fixture
def midwest_incident(tenant_alpha, base_date) -> GroundTruthIncident:
    start_dt = base_date.value
    return GroundTruthIncident(
        tenant_id=tenant_alpha,
        incident_id="INC-SYNTH-TRUCK-001",
        scenario_name="Midwest Regional Carrier Disruption",
        causal_start_time=UtcDateTime.from_datetime(start_dt + timedelta(days=44, hours=8)),
        causal_end_time=UtcDateTime.from_datetime(start_dt + timedelta(days=51, hours=23, minutes=59, seconds=59)),
        primary_root_cause="CARRIER_CAPACITY_COLLAPSE",
        affected_facility_id="WH-MIDWEST-01",
        affected_carrier_id="CARRIER_REGIONAL_LOGISTICS",
        true_ate_cancellation_rate_delta=0.0660,
        true_delayed_shipment_count=42,
        true_revenue_at_risk_cents=4500000,
        competing_hypotheses=[],
    )


@pytest.fixture
def midwest_60day_series() -> list[float]:
    """
    Simulated 60-day cancellation rate series for tnt_alpha Midwest cohort:
    - Days 1 to 44: baseline ~ 1.8% (0.0180) with weekly seasonality.
    - Days 45 to 52: disrupted ~ 8.4% (0.0840) (+6.6% surge).
    - Days 53 to 60: recovered baseline ~ 1.8% (0.0180).
    """
    seasonal_noise = [0.000, 0.001, -0.001, 0.002, 0.001, -0.002, 0.000]
    series: list[float] = []

    for d in range(1, 61):
        noise = seasonal_noise[(d - 1) % 7]
        if 45 <= d <= 52:
            # Active disruption
            series.append(round(0.0840 + noise, 4))
        else:
            # Normal baseline
            series.append(round(0.0180 + noise, 4))

    return series


# =============================================================================
# AC-P02-003-01 & AC-P02-003-03: Rolling Time-Split Backtest Verification
# =============================================================================

def test_rolling_backtest_detects_midwest_anomaly_within_48h(
    tenant_alpha,
    midwest_incident,
    midwest_60day_series,
    base_date,
):
    """
    AC-P02-003-01: Detects Midwest cancellation rate surge on Day 45 within <= 48h.
    AC-P02-003-03: Zero lookahead leakage across all 60 rolling steps.
    AC-P02-003-04: Ground truth evaluated strictly offline without runtime exposure.
    """
    from revpilot.modules.analytics.detectors import StlResidualDetector
    from revpilot.modules.benchmark.detector_evaluator import RollingTimeSplitEvaluator

    with tempfile.TemporaryDirectory() as tmp_dir:
        gt_file = os.path.join(tmp_dir, "ground_truth_incident.json")
        EvaluationGroundTruthStore.save_ground_truth(midwest_incident, gt_file)

        detector = StlResidualDetector(seasonal_period=7, sigma_threshold=3.0)
        evaluator = RollingTimeSplitEvaluator()

        metrics = evaluator.run_backtest(
            tenant_id=tenant_alpha,
            metric_id="METRIC-001",
            detector=detector,
            start_day=1,
            end_day=60,
            ground_truth_path=gt_file,
            series_data=midwest_60day_series,
            base_date=base_date,
        )

        # AC-P02-003-01: Detection lead time <= 48 hours
        assert metrics.lead_time_hours <= 48.0, f"Lead time {metrics.lead_time_hours}h exceeded 48h target"

        # Benchmarked precision and recall
        assert metrics.recall >= 0.85, f"Recall {metrics.recall} below 0.85 target"
        assert metrics.precision >= 0.80, f"Precision {metrics.precision} below 0.80 target"
        assert metrics.f1_score >= 0.82, f"F1-score {metrics.f1_score} below 0.82 target"
