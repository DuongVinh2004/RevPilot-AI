"""
RevPilot AI — Benchmark Harness for Time-Travel and Lookahead Leakage Audit
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §1.1 Invariant 3, §6
Specification: docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md §3, §4
Verifies GATE-TIME-LEAKAGE: Lookahead leakage rate is exactly 0.00% (INV-DATA-001).
"""

from __future__ import annotations
import sys
from datetime import timedelta
import pytest

from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_modules():
    """Ensure modules are purged from sys.modules to prevent collection-time contract violations."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.causal"):
            sys.modules.pop(mod, None)


@pytest.fixture
def causal_module():
    import revpilot.modules.causal as mod
    return mod


def test_gate_time_leakage_zero_lookahead_tolerance(causal_module):
    """
    GATE-TIME-LEAKAGE: Strict enforcement that zero records timestamped
    after as_of_time may enter causal estimation (INV-DATA-001).
    """
    as_of = UtcDateTime.from_iso("2026-02-21T00:00:00Z")
    t_start = UtcDateTime.from_iso("2026-02-14T00:00:00Z")

    # Injected lookahead record: 1 second past as_of_time watermark
    future_record = {
        "order_id": "ord_leak_001",
        "timestamp": UtcDateTime(as_of.value + timedelta(seconds=1)).isoformat(),
        "cancelled": 1,
    }

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.audit_temporal_leakage(
            as_of_time=as_of,
            treatment_window_start=t_start,
            records=[future_record],
        )

    assert exc_info.value.code == "ERR_TEMPORAL_LEAKAGE"
    assert "INV-DATA-001" in exc_info.value.message


def test_gate_time_leakage_covariate_pre_treatment_enforced(causal_module):
    """
    GATE-TIME-LEAKAGE: Covariates must strictly precede treatment window start.
    Any covariate observed on or after treatment_window_start is rejected.
    """
    as_of = UtcDateTime.from_iso("2026-02-21T00:00:00Z")
    t_start = UtcDateTime.from_iso("2026-02-14T00:00:00Z")

    # Injected post-treatment covariate
    leaked_covariates = {
        "customer_tenure": UtcDateTime.from_iso("2026-02-01T00:00:00Z"),
        "delivery_delay_observed": t_start,  # Coincident with treatment start
    }

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.audit_temporal_leakage(
            as_of_time=as_of,
            treatment_window_start=t_start,
            covariate_timestamps=leaked_covariates,
        )

    assert exc_info.value.code == "ERR_TEMPORAL_LEAKAGE"
