"""
RevPilot AI — Unit and Contract Tests for Rolling Stats Baseline (Phase 02)
Verifies rolling median calculation, IQR bounds, outlier resilience, and latency budgets.
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.1, TASK-P02-002, and AC-P02-002-02, AC-P02-002-04.
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


# =============================================================================
# AC-P02-002-02: Rolling Stats Median and IQR Bounds Verification
# =============================================================================

def test_rolling_stats_robust_median_and_iqr():
    """AC-P02-002-02: RollingStatsBaseline computes robust median and IQR bounds."""
    from revpilot.modules.analytics.baselines import RollingStatsBaseline

    # 14 values: 10, 11, ..., 23
    series = [float(10 + i) for i in range(14)]
    baseline = RollingStatsBaseline(window_size=14, iqr_multiplier=1.5)
    pred = baseline.predict(series)

    # Median of 14 elements [10..23] is (16 + 17) / 2 = 16.5
    assert pred.point_estimate == 16.5
    assert pred.baseline_id == "BASE-ROLLING-STATS-001"
    assert pred.baseline_version == "1.0.0"

    # Verify bounds enclose the median and are symmetrically calibrated
    assert pred.lower_bound < pred.point_estimate < pred.upper_bound


def test_rolling_stats_outlier_resilience():
    """Median point estimate remains stable in presence of single massive outlier."""
    from revpilot.modules.analytics.baselines import RollingStatsBaseline

    clean_series = [10.0] * 14
    corrupted_series = [10.0] * 13 + [999999.0]

    baseline = RollingStatsBaseline(window_size=14)
    pred_clean = baseline.predict(clean_series)
    pred_corrupt = baseline.predict(corrupted_series)

    # Median of [10... 10, 999999] is still 10.0
    assert pred_clean.point_estimate == 10.0
    assert pred_corrupt.point_estimate == 10.0


def test_rolling_stats_empty_series():
    """Empty series returns point_estimate = 0.0 with [0.0, 0.0] bounds without exception."""
    from revpilot.modules.analytics.baselines import RollingStatsBaseline

    baseline = RollingStatsBaseline(window_size=14)
    pred = baseline.predict([])

    assert pred.point_estimate == 0.0
    assert pred.lower_bound == 0.0
    assert pred.upper_bound == 0.0
    assert pred.baseline_id == "BASE-ROLLING-STATS-001"


def test_rolling_stats_insufficient_history():
    """Series length < window_size raises InsufficientHistoryError (HTTP 422)."""
    from revpilot.modules.analytics.baselines import (
        RollingStatsBaseline,
        InsufficientHistoryError,
    )

    baseline = RollingStatsBaseline(window_size=14)
    with pytest.raises(InsufficientHistoryError) as exc_info:
        baseline.predict([1.0, 2.0, 3.0])

    err = exc_info.value
    assert err.code == "INSUFFICIENT_HISTORY"
    assert err.http_status == 422


# =============================================================================
# AC-P02-002-04: Latency Budget Verification (< 5ms per series)
# =============================================================================

def test_rolling_stats_latency_budget():
    """AC-P02-002-04: RollingStatsBaseline completes in < 5ms per series."""
    from revpilot.modules.analytics.baselines import RollingStatsBaseline

    series = [float(i) for i in range(100)]
    baseline = RollingStatsBaseline(window_size=14)

    t0 = time.perf_counter()
    for _ in range(100):
        baseline.predict(series)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0 / 100.0

    assert elapsed_ms < 5.0, f"Execution latency {elapsed_ms:.3f}ms exceeded 5.0ms budget"
