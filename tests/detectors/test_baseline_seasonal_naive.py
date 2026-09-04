"""
RevPilot AI — Unit and Contract Tests for Seasonal Naive Baseline (Phase 02)
Verifies Y_t = Y_{t-7} lag prediction, empty series corner cases, and latency budgets.
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.1, TASK-P02-002, and AC-P02-002-01, AC-P02-002-04.
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
# AC-P02-002-01: Seasonal Naive Lag Output Verification
# =============================================================================

def test_seasonal_naive_exact_lag_prediction():
    """AC-P02-002-01: SeasonalNaiveBaseline predicts exactly Y_{t-7} on 14-day series."""
    from revpilot.modules.analytics.baselines import SeasonalNaiveBaseline

    # 14-day test vector
    # Day 1..7 (Cycle 1): 10, 12, 11, 13, 15, 14, 16
    # Day 8..14 (Cycle 2): 11, 13, 12, 14, 16, 15, 17
    # For predicting Day 15 (next day): Y_{14 - 7} = Day 8 = 11.0
    series = [10.0, 12.0, 11.0, 13.0, 15.0, 14.0, 16.0, 11.0, 13.0, 12.0, 14.0, 16.0, 15.0, 17.0]

    baseline = SeasonalNaiveBaseline(season_length=7, alpha=0.05)
    pred = baseline.predict(series)

    # series[-7] is Day 8 = 11.0
    expected_lag = series[-7]
    assert pred.point_estimate == expected_lag
    assert pred.baseline_id == "BASE-SEASONAL-NAIVE-001"
    assert pred.baseline_version == "1.0.0"
    assert pred.lower_bound <= pred.point_estimate <= pred.upper_bound


def test_seasonal_naive_empty_series():
    """Empty series returns point_estimate = 0.0 with [0.0, 0.0] bounds without exception."""
    from revpilot.modules.analytics.baselines import SeasonalNaiveBaseline

    baseline = SeasonalNaiveBaseline(season_length=7)
    pred = baseline.predict([])

    assert pred.point_estimate == 0.0
    assert pred.lower_bound == 0.0
    assert pred.upper_bound == 0.0
    assert pred.baseline_id == "BASE-SEASONAL-NAIVE-001"


def test_seasonal_naive_insufficient_history():
    """Series with fewer observations than season_length raises InsufficientHistoryError (HTTP 422)."""
    from revpilot.modules.analytics.baselines import (
        SeasonalNaiveBaseline,
        InsufficientHistoryError,
    )

    baseline = SeasonalNaiveBaseline(season_length=7)
    # Only 5 elements provided
    with pytest.raises(InsufficientHistoryError) as exc_info:
        baseline.predict([10.0, 20.0, 30.0, 40.0, 50.0])

    err = exc_info.value
    assert err.code == "INSUFFICIENT_HISTORY"
    assert err.http_status == 422


# =============================================================================
# AC-P02-002-04: Latency Budget Verification (< 5ms per series)
# =============================================================================

def test_seasonal_naive_latency_budget():
    """AC-P02-002-04: Baseline prediction completes in < 5ms per series."""
    from revpilot.modules.analytics.baselines import SeasonalNaiveBaseline

    series = [float(i % 7) for i in range(100)]
    baseline = SeasonalNaiveBaseline(season_length=7)

    # Measure execution time
    t0 = time.perf_counter()
    for _ in range(100):
        baseline.predict(series)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0 / 100.0

    assert elapsed_ms < 5.0, f"Execution latency {elapsed_ms:.3f}ms exceeded 5.0ms budget"
