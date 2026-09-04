"""
RevPilot AI — Benchmark Harness for Causal Sensitivity Bounds (E-Value & Oster Delta)
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §3, §6
Specification: docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md §3, §4
Verifies GATE-CAUSAL-SENSITIVITY: E-value computed and reported; confirms effect robust up to E-value >= 1.80.
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


def test_gate_causal_sensitivity_midwest_benchmark(causal_module):
    """
    GATE-CAUSAL-SENSITIVITY: Evaluates sensitivity of Midwest Truck Capacity
    treatment effect (+0.0660 cancellation increase) against unobserved confounding.
    Confirms E-value >= 1.80 and is_sensitive_to_unobserved_confounding is False.
    """
    true_ate = 0.0660
    ci_lower_conservative = 0.0350  # Conservative 95% CI lower bound
    baseline_risk = 0.0400          # 4% baseline cancellation rate

    sensitivity = causal_module.conduct_sensitivity_analysis(
        ate=true_ate,
        ci_lower=ci_lower_conservative,
        baseline_risk=baseline_risk,
        sensitivity_threshold=1.50,
        method="E_VALUE",
    )

    # 1. GATE-CAUSAL-SENSITIVITY: Point estimate E-value >= 1.80
    assert (
        sensitivity.e_value_estimate >= 1.80
    ), f"GATE-CAUSAL-SENSITIVITY violated: E-value {sensitivity.e_value_estimate:.2f} < 1.80"

    # 2. Confidence interval E-value >= 1.80
    assert (
        sensitivity.e_value_ci >= 1.80
    ), f"GATE-CAUSAL-SENSITIVITY CI violated: E-value CI {sensitivity.e_value_ci:.2f} < 1.80"

    # 3. Robustness confirmation
    assert (
        sensitivity.is_sensitive_to_unobserved_confounding is False
    ), "GATE-CAUSAL-SENSITIVITY violated: Robust effect mistakenly flagged as sensitive"
