"""
RevPilot AI — Unit and Contract Tests for Detector False Positive Rate (Phase 02)
Verifies AC-P02-003-02: False Positive Rate (FPR) <= 0.05 during normal operational baseline windows.
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §3 and TASK-P02-003.
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
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta")


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


def test_false_positive_rate_on_baseline_window_days_1_to_44(
    tenant_alpha,
    midwest_incident,
    base_date,
):
    """AC-P02-003-02: False positive rate remains <= 0.05 during normal baseline windows (Days 1–44)."""
    from revpilot.modules.analytics.detectors import StlResidualDetector
    from revpilot.modules.benchmark.detector_evaluator import RollingTimeSplitEvaluator

    # 44 days of clean baseline cancellation rate ~ 1.8%
    seasonal_noise = [0.000, 0.001, -0.001, 0.002, 0.001, -0.002, 0.000]
    baseline_series = [round(0.0180 + seasonal_noise[(d - 1) % 7], 4) for d in range(1, 45)]

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
            end_day=44,
            ground_truth_path=gt_file,
            series_data=baseline_series,
            base_date=base_date,
        )

        assert metrics.false_positive_rate <= 0.05, (
            f"FPR {metrics.false_positive_rate} exceeded 0.05 target during baseline period"
        )


def test_false_positive_rate_on_control_tenant_across_60_days(
    tenant_beta,
    midwest_incident,
    base_date,
):
    """AC-P02-003-02: Control tenant (tnt_beta) unaffected by disruption maintains FPR <= 0.05 across all 60 days."""
    from revpilot.modules.analytics.detectors import StlResidualDetector
    from revpilot.modules.benchmark.detector_evaluator import RollingTimeSplitEvaluator

    # 60 days of clean control cancellation rate
    seasonal_noise = [0.000, 0.001, -0.001, 0.002, 0.001, -0.002, 0.000]
    control_series = [round(0.0180 + seasonal_noise[(d - 1) % 7], 4) for d in range(1, 61)]

    with tempfile.TemporaryDirectory() as tmp_dir:
        gt_file = os.path.join(tmp_dir, "ground_truth_incident.json")
        EvaluationGroundTruthStore.save_ground_truth(midwest_incident, gt_file)

        detector = StlResidualDetector(seasonal_period=7, sigma_threshold=3.0)
        evaluator = RollingTimeSplitEvaluator()

        metrics = evaluator.run_backtest(
            tenant_id=tenant_beta,
            metric_id="METRIC-001",
            detector=detector,
            start_day=1,
            end_day=60,
            ground_truth_path=gt_file,
            series_data=control_series,
            base_date=base_date,
        )

        assert metrics.false_positive_rate <= 0.05, (
            f"Control tenant FPR {metrics.false_positive_rate} exceeded 0.05 target"
        )
