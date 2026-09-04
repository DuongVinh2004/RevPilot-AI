"""
RevPilot AI — Unit and Contract Tests for EWMA Baseline (Phase 02)
Verifies exponential smoothing with alpha = 0.2, variance tracking, and latency budgets.
Conforms to ANOMALY-BENCHMARK-PROTOCOL.md §2.1, TASK-P02-002, and AC-P02-002-03, AC-P02-002-04.
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
# AC-P02-002-03: EWMA Smoothing Calculation (alpha = 0.2)
# =============================================================================

def test_ewma_exact_smoothing_calculation():
    """AC-P02-002-03: EwmaBaseline applies exponential smoothing with alpha = 0.2."""
    from revpilot.modules.analytics.baselines import EwmaBaseline

    series = [10.0, 20.0, 15.0]
    # S_0 = 10.0
    # S_1 = 0.2 * 20.0 + 0.8 * 10.0 = 4.0 + 8.0 = 12.0
    # S_2 = 0.2 * 15.0 + 0.8 * 12.0 = 3.0 + 9.6 = 12.6
    baseline = EwmaBaseline(alpha=0.2, sigma_multiplier=3.0)
    pred = baseline.predict(series)

    assert abs(pred.point_estimate - 12.6) < 1e-9
    assert pred.baseline_id == "BASE-EWMA-001"
    assert pred.baseline_version == "1.0.0"
    assert pred.lower_bound <= pred.point_estimate <= pred.upper_bound


def test_ewma_empty_series():
    """Empty series returns point_estimate = 0.0 with [0.0, 0.0] bounds without exception."""
    from revpilot.modules.analytics.baselines import EwmaBaseline

    baseline = EwmaBaseline(alpha=0.2)
    pred = baseline.predict([])

    assert pred.point_estimate == 0.0
    assert pred.lower_bound == 0.0
    assert pred.upper_bound == 0.0
    assert pred.baseline_id == "BASE-EWMA-001"


def test_ewma_single_observation():
    """Single observation returns exact observation with zero-width interval."""
    from revpilot.modules.analytics.baselines import EwmaBaseline

    baseline = EwmaBaseline(alpha=0.2)
    pred = baseline.predict([42.5])

    assert pred.point_estimate == 42.5
    assert pred.lower_bound == 42.5
    assert pred.upper_bound == 42.5


# =============================================================================
# AC-P02-002-04: Latency Budget Verification (< 5ms per series)
# =============================================================================

def test_ewma_latency_budget():
    """AC-P02-002-04: EwmaBaseline completes in < 5ms per series."""
    from revpilot.modules.analytics.baselines import EwmaBaseline

    series = [float(i % 10) for i in range(100)]
    baseline = EwmaBaseline(alpha=0.2)

    t0 = time.perf_counter()
    for _ in range(100):
        baseline.predict(series)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0 / 100.0

    assert elapsed_ms < 5.0, f"Execution latency {elapsed_ms:.3f}ms exceeded 5.0ms budget"
