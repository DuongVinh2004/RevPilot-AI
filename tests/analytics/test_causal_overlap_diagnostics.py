"""
RevPilot AI — Benchmark Harness for Causal Overlap and Positivity Diagnostics
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §1.1, §6
Specification: docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md §3, §4
Verifies GATE-CAUSAL-OVERLAP: Positivity satisfied on compliant cohorts, halts with ERR_OVERLAP_VIOLATION on non-overlap cohorts.
"""

from __future__ import annotations
import sys
import pytest


@pytest.fixture(autouse=True)
def _isolate_causal_module():
    """Ensure modules are purged from sys.modules to prevent collection-time contract violations."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.causal"):
            sys.modules.pop(mod, None)


@pytest.fixture
def causal_module():
    import revpilot.modules.causal as mod
    return mod


def test_gate_causal_overlap_compliant_midwest_cohort(causal_module):
    """
    GATE-CAUSAL-OVERLAP: Compliant cohort with common support in [0.05, 0.95]
    must return positivity_satisfied=True without throwing errors.
    """
    # Balanced feature distribution between treated and untreated
    X = [
        [1.0, 100.0, 1.0],
        [1.0, 120.0, 2.0],
        [2.0, 150.0, 1.0],
        [2.0, 180.0, 2.0],
        [1.0, 110.0, 2.0],
        [2.0, 160.0, 1.0],
        [1.0, 130.0, 1.0],
        [2.0, 190.0, 2.0],
    ]
    T = [0, 0, 0, 0, 1, 1, 1, 1]

    scores = causal_module.calculate_propensity_scores(X, T)
    diagnostics = causal_module.evaluate_overlap_diagnostics(
        propensity_scores=scores,
        T=T,
        min_cutoff=0.05,
        max_cutoff=0.95,
        required_common_support_ratio=0.75,
    )

    assert diagnostics.positivity_satisfied is True
    assert diagnostics.common_support_ratio >= 0.75
    assert diagnostics.min_propensity >= 0.05
    assert diagnostics.max_propensity <= 0.95


def test_gate_causal_overlap_complete_separation_halt(causal_module):
    """
    GATE-CAUSAL-OVERLAP: When treatment is deterministic (complete separation),
    system must halt immediately with ERR_OVERLAP_VIOLATION.
    Extrapolation is strictly forbidden (INV-AI-001).
    """
    # Non-overlapping cohorts (e.g. perfect predictor separating treatment)
    separated_scores = [0.001, 0.002, 0.005, 0.008, 0.992, 0.995, 0.998, 0.999]
    T = [0, 0, 0, 0, 1, 1, 1, 1]

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.evaluate_overlap_diagnostics(
            propensity_scores=separated_scores,
            T=T,
            min_cutoff=0.05,
            max_cutoff=0.95,
            required_common_support_ratio=0.80,
        )

    assert exc_info.value.code == "ERR_OVERLAP_VIOLATION"
    assert "Positivity and overlap violation" in exc_info.value.message
