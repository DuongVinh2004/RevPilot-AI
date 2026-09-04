"""
RevPilot AI — Unit and Contract Tests for STL Residual Detector (Phase 02)
Verifies STL decomposition, 3-sigma anomaly thresholding, and latency budgets.
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.2, TASK-P02-003, and AC-P02-003-01.
"""

from __future__ import annotations
import sys
import time
import pytest


@pytest.fixture(autouse=True)
def _isolate_analytics_module():
    """Ensure analytics module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.analytics"):
            sys.modules.pop(mod, None)


def test_stl_detector_detects_severe_spike():
    """StlResidualDetector flags a 3-sigma divergence as an anomaly."""
    from revpilot.modules.analytics.detectors import StlResidualDetector

    # 30 days of baseline cancellation rate ~ 1.8% (0.0180) with weekly seasonality
    base_pattern = [0.018, 0.019, 0.017, 0.018, 0.020, 0.021, 0.018]
    series = [base_pattern[i % 7] for i in range(30)]

    # Inject severe spike at Day 31: 0.084 (8.4%)
    series.append(0.084)

    detector = StlResidualDetector(seasonal_period=7, sigma_threshold=3.0)
    res = detector.detect(series)

    assert res.is_anomaly is True
    assert res.deviation_sigma > 3.0
    assert res.anomaly_score > 0.65
    assert res.detector_id == "DET-STL-RESIDUAL-001"
    assert res.detector_version == "1.0.0"


def test_stl_detector_clean_series_not_anomalous():
    """Normal seasonal observations remain below threshold (is_anomaly = False)."""
    from revpilot.modules.analytics.detectors import StlResidualDetector

    base_pattern = [0.018, 0.019, 0.017, 0.018, 0.020, 0.021, 0.018]
    series = [base_pattern[i % 7] for i in range(35)]

    detector = StlResidualDetector(seasonal_period=7, sigma_threshold=3.0)
    res = detector.detect(series)

    assert res.is_anomaly is False
    assert res.deviation_sigma < 3.0


def test_stl_detector_empty_and_short_series_safe():
    """Empty series and short series return non-anomalous results without raising exceptions."""
    from revpilot.modules.analytics.detectors import StlResidualDetector

    detector = StlResidualDetector(seasonal_period=7, sigma_threshold=3.0)

    # Empty
    res_empty = detector.detect([])
    assert res_empty.is_anomaly is False
    assert res_empty.anomaly_score == 0.0

    # Short (< 14)
    res_short = detector.detect([0.01, 0.02, 0.01, 0.03])
    assert isinstance(res_short.is_anomaly, bool)


def test_stl_detector_latency_budget():
    """StlResidualDetector execution completes in < 5ms per series."""
    from revpilot.modules.analytics.detectors import StlResidualDetector

    series = [0.02 + 0.005 * (i % 7) for i in range(60)]
    detector = StlResidualDetector(seasonal_period=7)

    t0 = time.perf_counter()
    for _ in range(100):
        detector.detect(series)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0 / 100.0

    assert elapsed_ms < 5.0, f"Execution latency {elapsed_ms:.3f}ms exceeded 5.0ms budget"
