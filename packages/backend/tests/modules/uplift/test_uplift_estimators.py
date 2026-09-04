"""
RevPilot AI — Unit Tests for CATE Estimators & Persuadability Classification
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md §1, §3, §4
Conforms to BR-002, BR-005, FR-ML-003, FR-ML-004, and GATE-SLEEPING-DOGS.
"""

from __future__ import annotations
import sys
import pytest


@pytest.fixture(autouse=True)
def _isolate_uplift_module():
    """Ensure uplift module is cleaned between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.uplift"):
            sys.modules.pop(mod, None)


@pytest.fixture
def uplift_module():
    import revpilot.modules.uplift as mod
    return mod


def test_classify_persuadability_4_quadrants(uplift_module):
    """
    Verify classification aligns with canonical 4-quadrant taxonomy:
    - PERSUADABLE: tau >= 0.05
    - SLEEPING_DOG: tau <= -0.05
    - LOST_CAUSE: |tau| < 0.05 and churn_risk >= 0.50
    - SURE_THING: |tau| < 0.05 and churn_risk < 0.50
    """
    seg = uplift_module.classify_persuadability

    # Persuadable
    assert seg(cate_estimate=0.12, churn_risk=0.80) == uplift_module.PersuadabilitySegment.PERSUADABLE
    assert seg(cate_estimate=0.05, churn_risk=0.30) == uplift_module.PersuadabilitySegment.PERSUADABLE

    # Sleeping Dog
    assert seg(cate_estimate=-0.08, churn_risk=0.10) == uplift_module.PersuadabilitySegment.SLEEPING_DOG
    assert seg(cate_estimate=-0.05, churn_risk=0.85) == uplift_module.PersuadabilitySegment.SLEEPING_DOG

    # Lost Cause (high churn risk, ineffective treatment)
    assert seg(cate_estimate=0.01, churn_risk=0.85) == uplift_module.PersuadabilitySegment.LOST_CAUSE
    assert seg(cate_estimate=-0.02, churn_risk=0.70) == uplift_module.PersuadabilitySegment.LOST_CAUSE

    # Sure Thing (low/moderate churn risk, stays without treatment)
    assert seg(cate_estimate=0.02, churn_risk=0.15) == uplift_module.PersuadabilitySegment.SURE_THING
    assert seg(cate_estimate=-0.01, churn_risk=0.05) == uplift_module.PersuadabilitySegment.SURE_THING


def test_fr_ml_003_risk_vs_uplift_separation(uplift_module):
    """
    FR-ML-003: Churn risk and uplift are distinct objects.
    A high-risk customer (churn_risk = 0.95) must NOT be targeted if tau <= 0.
    """
    # High churn risk, but treatment has zero impact -> LOST_CAUSE
    res_lost = uplift_module.classify_persuadability(cate_estimate=0.005, churn_risk=0.95)
    assert res_lost == uplift_module.PersuadabilitySegment.LOST_CAUSE

    # High churn risk, but treatment triggers churn annoyance -> SLEEPING_DOG
    res_dog = uplift_module.classify_persuadability(cate_estimate=-0.060, churn_risk=0.90)
    assert res_dog == uplift_module.PersuadabilitySegment.SLEEPING_DOG


def test_t_learner_cate_estimation_accuracy(uplift_module):
    """Verify T-Learner recovers synthetic heterogeneous treatment effects."""
    # Synthetic data: Y(0) = 0.20 + 0.10 * X, Y(1) = 0.35 + 0.10 * X -> tau = +0.15
    X_train = [
        [1.0], [2.0], [3.0], [4.0],
        [1.0], [2.0], [3.0], [4.0],
    ]
    T_train = [1, 1, 1, 1, 0, 0, 0, 0]
    Y_train = [
        0.35 + 0.10 * 1.0,
        0.35 + 0.10 * 2.0,
        0.35 + 0.10 * 3.0,
        0.35 + 0.10 * 4.0,
        0.20 + 0.10 * 1.0,
        0.20 + 0.10 * 2.0,
        0.20 + 0.10 * 3.0,
        0.20 + 0.10 * 4.0,
    ]

    X_test = [[2.5]]
    results = uplift_module.estimate_t_learner_cate(X_train, T_train, Y_train, X_test)

    assert len(results) == 1
    cate_est, se, (ci_low, ci_high) = results[0]

    assert pytest.approx(cate_est, 0.05) == 0.15
    assert ci_low <= 0.15 <= ci_high
    assert se > 0.0


def test_s_learner_cate_estimation_accuracy(uplift_module):
    """Verify S-Learner recovers synthetic treatment effect with interaction."""
    # Synthetic data: Y = 0.10 + 0.05 * X + 0.08 * T -> tau = +0.08
    X_train = [
        [1.0], [2.0], [3.0], [4.0],
        [1.0], [2.0], [3.0], [4.0],
    ]
    T_train = [1, 1, 1, 1, 0, 0, 0, 0]
    Y_train = [
        0.10 + 0.05 * 1.0 + 0.08 * 1.0,
        0.10 + 0.05 * 2.0 + 0.08 * 1.0,
        0.10 + 0.05 * 3.0 + 0.08 * 1.0,
        0.10 + 0.05 * 4.0 + 0.08 * 1.0,
        0.10 + 0.05 * 1.0 + 0.08 * 0.0,
        0.10 + 0.05 * 2.0 + 0.08 * 0.0,
        0.10 + 0.05 * 3.0 + 0.08 * 0.0,
        0.10 + 0.05 * 4.0 + 0.08 * 0.0,
    ]

    X_test = [[2.0]]
    results = uplift_module.estimate_s_learner_cate(X_train, T_train, Y_train, X_test)

    assert len(results) == 1
    cate_est, se, (ci_low, ci_high) = results[0]

    assert pytest.approx(cate_est, 0.02) == 0.08
    assert ci_low <= 0.08 <= ci_high
