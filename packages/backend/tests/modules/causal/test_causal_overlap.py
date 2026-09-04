"""
RevPilot AI — Unit Tests for Positivity and Propensity Overlap Diagnostics
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §1.1, §3, §5 Step 3
Conforms to BR-001, BR-002, FR-ML-004, INV-AI-001, AC-006, and GATE-CAUSAL-OVERLAP.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_causal_module():
    """Purge causal module between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.causal"):
            sys.modules.pop(mod, None)


@pytest.fixture
def causal_module():
    import revpilot.modules.causal as mod
    return mod


def test_propensity_score_deterministic_and_bounded(causal_module):
    """Verify propensity score estimation produces bounded and repeatable outputs."""
    X = [
        [1.0, 50.0],
        [2.0, 120.0],
        [1.0, 80.0],
        [3.0, 200.0],
        [2.0, 95.0],
        [3.0, 210.0],
    ]
    T = [0, 1, 0, 1, 0, 1]

    scores_1 = causal_module.calculate_propensity_scores(X, T)
    scores_2 = causal_module.calculate_propensity_scores(X, T)

    assert scores_1 == scores_2
    assert len(scores_1) == len(T)
    for score in scores_1:
        assert 0.0 <= score <= 1.0


def test_complete_separation_raises_overlap_violation(causal_module):
    """Deterministic treatment assignment (e(X) approaching 0 or 1) halts with ERR_OVERLAP_VIOLATION."""
    # Scores completely outside [0.05, 0.95]
    propensity_scores = [0.01, 0.02, 0.01, 0.99, 0.98, 0.99]
    T = [0, 0, 0, 1, 1, 1]

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.evaluate_overlap_diagnostics(
            propensity_scores=propensity_scores,
            T=T,
            min_cutoff=0.05,
            max_cutoff=0.95,
            required_common_support_ratio=0.80,
        )
    assert exc_info.value.code == "ERR_OVERLAP_VIOLATION"
    assert exc_info.value.details["common_support_ratio"] == 0.0


def test_insufficient_common_support_ratio_raises_violation(causal_module):
    """When common support ratio is below 80%, evaluation must halt."""
    # 4 units in support, 6 units outside -> ratio = 40% < 80%
    propensity_scores = [0.01, 0.02, 0.03, 0.15, 0.50, 0.70, 0.85, 0.98, 0.99, 0.99]
    T = [0, 0, 0, 0, 1, 0, 1, 1, 1, 1]

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.evaluate_overlap_diagnostics(
            propensity_scores=propensity_scores,
            T=T,
            min_cutoff=0.05,
            max_cutoff=0.95,
            required_common_support_ratio=0.80,
        )
    assert exc_info.value.code == "ERR_OVERLAP_VIOLATION"


def test_unilateral_cohort_in_support_raises_violation(causal_module):
    """Common support requires BOTH treated and control units to be present."""
    # Units in [0.05, 0.95] are all treated (T=1), no control (T=0)
    propensity_scores = [0.01, 0.02, 0.03, 0.20, 0.40, 0.60, 0.80]
    T = [0, 0, 0, 1, 1, 1, 1]

    with pytest.raises(causal_module.CausalInferenceError) as exc_info:
        causal_module.evaluate_overlap_diagnostics(
            propensity_scores=propensity_scores,
            T=T,
            min_cutoff=0.05,
            max_cutoff=0.95,
            required_common_support_ratio=0.50,
        )
    assert exc_info.value.code == "ERR_OVERLAP_VIOLATION"
    assert not exc_info.value.details["control_in_support"]


def test_midwest_truck_capacity_overlap_satisfied(causal_module):
    """Synthetic Midwest cohort satisfies positivity and common support."""
    # Simulated well-balanced propensity scores across treated and control
    propensity_scores = [
        0.18, 0.22, 0.35, 0.42, 0.55, 0.62, 0.70, 0.78, 0.82, 0.88,
        0.15, 0.25, 0.30, 0.48, 0.52, 0.60, 0.68, 0.75, 0.80, 0.84,
    ]
    T = [
        0, 0, 0, 0, 0, 1, 1, 1, 1, 1,
        0, 0, 0, 1, 1, 1, 1, 1, 1, 1,
    ]

    diagnostics = causal_module.evaluate_overlap_diagnostics(
        propensity_scores=propensity_scores,
        T=T,
        min_cutoff=0.05,
        max_cutoff=0.95,
        required_common_support_ratio=0.80,
    )

    assert diagnostics.positivity_satisfied is True
    assert diagnostics.common_support_ratio == 1.0
    assert diagnostics.trimmed_sample_count == 0
    assert 0.05 <= diagnostics.min_propensity <= diagnostics.max_propensity <= 0.95
