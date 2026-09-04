"""
RevPilot AI — Unit Tests for Deterministic Causal Estimators (AIPW & DiD)
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §2, §4, §5 Step 4
Conforms to BR-001, BR-002, FR-ML-004, NFR-AI-007, and AC-006.
"""

from __future__ import annotations
import math
import sys
import pytest


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


def test_fit_ridge_linear_regression_accuracy(causal_module):
    """Verify linear regression recovers deterministic linear relationships."""
    # Y = 10.0 + 2.0 * X1 - 3.0 * X2
    X = [
        [1.0, 2.0],
        [2.0, 1.0],
        [3.0, 4.0],
        [4.0, 2.0],
        [5.0, 5.0],
        [6.0, 3.0],
    ]
    Y = [10.0 + 2.0 * row[0] - 3.0 * row[1] for row in X]

    beta = causal_module.fit_ridge_linear_regression(X, Y, lambda_ridge=1e-5)
    preds = causal_module.predict_linear(X, beta)

    assert pytest.approx(beta[0], 0.05) == 10.0
    assert pytest.approx(beta[1], 0.05) == 2.0
    assert pytest.approx(beta[2], 0.05) == -3.0
    for y_true, y_pred in zip(Y, preds):
        assert pytest.approx(y_true, 0.05) == y_pred


def test_p_value_calculation_standard_normal(causal_module):
    """Verify two-tailed p-value matches standard Gaussian critical points."""
    assert pytest.approx(causal_module.compute_p_value_two_tailed(0.0), 0.001) == 1.000
    assert pytest.approx(causal_module.compute_p_value_two_tailed(1.95996), 0.005) == 0.050
    assert pytest.approx(causal_module.compute_p_value_two_tailed(2.5758), 0.005) == 0.010
    assert causal_module.compute_p_value_two_tailed(6.0) < 1e-6


def test_linear_did_estimation(causal_module):
    """Verify Linear DiD computes unbiased parallel trends contrast."""
    # Pre: Control = 10.0, Treated = 15.0 (Baseline diff = 5.0)
    # Post: Control = 12.0 (+2.0 trend), Treated = 23.0 (+8.0 trend + effect)
    # DiD = (23 - 15) - (12 - 10) = 8.0 - 2.0 = +6.0
    y_pre_ctrl = [10.0, 9.8, 10.2, 10.0]
    y_post_ctrl = [12.0, 11.9, 12.1, 12.0]
    y_pre_treat = [15.0, 14.9, 15.1, 15.0]
    y_post_treat = [23.0, 22.9, 23.1, 23.0]

    ate, se, (ci_low, ci_high), p_val = causal_module.estimate_linear_did(
        Y_pre_treatment=y_pre_treat,
        Y_post_treatment=y_post_treat,
        Y_pre_control=y_pre_ctrl,
        Y_post_control=y_post_ctrl,
    )

    assert pytest.approx(ate, 0.05) == 6.0
    assert ci_low <= ate <= ci_high
    assert p_val < 0.001


def test_aipw_synthetic_doubly_robust_convergence(causal_module):
    """Verify AIPW recovers true treatment effect under confounding."""
    # Simulation: 20 units, True ATE = +0.060
    # Covariates: [X_severity, X_tier]
    X = [
        [0.5, 1.0], [0.8, 2.0], [0.2, 1.0], [0.9, 3.0],
        [0.4, 2.0], [0.7, 1.0], [0.3, 2.0], [0.6, 3.0],
        [0.5, 1.0], [0.8, 2.0], [0.2, 1.0], [0.9, 3.0],
        [0.4, 2.0], [0.7, 1.0], [0.3, 2.0], [0.6, 3.0],
        [0.5, 1.0], [0.8, 2.0], [0.2, 1.0], [0.9, 3.0],
    ]
    T = [1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0]
    # Y = 0.05 * X_severity + 0.02 * X_tier + 0.066 * T
    Y = [0.05 * row[0] + 0.02 * row[1] + (0.066 if t == 1 else 0.0) for row, t in zip(X, T)]

    ate, se, (ci_low, ci_high), p_val = causal_module.estimate_aipw_ate(X, T, Y)

    assert pytest.approx(ate, 0.02) == 0.066
    assert ci_low <= 0.066 <= ci_high
    assert ate > 0
    assert p_val < 0.01
