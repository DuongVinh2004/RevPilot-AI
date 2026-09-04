"""
RevPilot AI — Unit Tests for Sensitivity Analysis & Falsification Engine
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §2, §3, §5 Step 5
Conforms to BR-001, BR-002, FR-ML-004, AC-006, and GATE-CAUSAL-SENSITIVITY.
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


def test_calculate_e_value_known_values(causal_module):
    """Verify E-value matches analytical VanderWeele & Ding formula."""
    assert causal_module.calculate_e_value(1.0) == 1.0
    assert causal_module.calculate_e_value(0.8) == 1.0

    # RR = 2.0 -> 2.0 + sqrt(2.0 * 1.0) = 3.4142
    assert pytest.approx(causal_module.calculate_e_value(2.0), 0.001) == 3.4142

    # RR = 3.0 -> 3.0 + sqrt(3.0 * 2.0) = 5.4495
    assert pytest.approx(causal_module.calculate_e_value(3.0), 0.001) == 5.4495


def test_compute_e_value_from_ate(causal_module):
    """Verify conversion of additive ATE to Risk Ratio scale E-value."""
    # ATE = 0.066, baseline_risk = 0.04 -> RR = 0.106 / 0.04 = 2.65
    # E-value = 2.65 + sqrt(2.65 * 1.65) = 2.65 + 2.0911 = 4.7411
    e_est, e_ci = causal_module.compute_e_value_from_ate(
        ate=0.066,
        ci_lower=0.030,
        baseline_risk=0.04,
    )

    assert pytest.approx(e_est, 0.05) == 4.74
    # ci_lower = 0.030 -> RR_ci = 0.070 / 0.04 = 1.75
    # E_ci = 1.75 + sqrt(1.75 * 0.75) = 1.75 + 1.1456 = 2.8956
    assert pytest.approx(e_ci, 0.05) == 2.90


def test_sensitivity_analysis_robust_midwest_scenario(causal_module):
    """Strong causal effect remains robust against unobserved confounding."""
    analysis = causal_module.conduct_sensitivity_analysis(
        ate=0.0660,
        ci_lower=0.0425,
        baseline_risk=0.04,
        sensitivity_threshold=1.50,
    )

    assert analysis.e_value_estimate >= 1.80
    assert analysis.e_value_ci >= 1.80
    assert analysis.is_sensitive_to_unobserved_confounding is False


def test_sensitivity_analysis_fragile_effect_flagged(causal_module):
    """Fragile or null-spanning effect is flagged as sensitive."""
    # Marginal ATE with CI spanning zero
    analysis = causal_module.conduct_sensitivity_analysis(
        ate=0.002,
        ci_lower=-0.005,
        baseline_risk=0.04,
        sensitivity_threshold=1.50,
    )

    assert analysis.is_sensitive_to_unobserved_confounding is True
    assert analysis.e_value_ci == 1.0


def test_oster_delta_calculation(causal_module):
    """Verify Oster (2019) bounding delta calculation."""
    delta = causal_module.calculate_oster_delta(
        r_squared_controlled=0.45,
        r_squared_max=0.60,
        beta_controlled=0.066,
        beta_uncontrolled=0.080,
    )

    assert delta > 0.0
    assert isinstance(delta, float)
