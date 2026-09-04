"""
RevPilot AI — Benchmark Harness for Causal Estimand & ATE Accuracy
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §4, §6
Specification: docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md §2, §3, §4
Verifies:
- GATE-CAUSAL-ATE-ERR: |ATE_hat - 0.0660| <= 0.0500 (NFR-AI-007)
- GATE-CAUSAL-CI-COV: 95% CI covers true ATE 0.0660 (FR-ML-004, AC-006)
- GATE-CAUSAL-DIRECTION: ATE_hat > 0 and p < 0.01 (FR-ML-004)
"""

from __future__ import annotations
import math
import random
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


def test_gate_causal_ate_synthetic_midwest_benchmark(causal_module):
    """
    Evaluates Doubly Robust AIPW estimator against seeded Midwest Truck Capacity disruption.
    Ground-truth ATE: +0.0660 (+6.6% absolute cancellation increase).
    """
    # Deterministic generation using SEED 42
    rng = random.Random(42)
    n = 100
    true_ate = 0.0660

    X: list[list[float]] = []
    T: list[int] = []
    Y: list[float] = []

    for _ in range(n):
        # Confounders:
        # X1: Storm severity index in transit corridor [0.0, 1.0]
        # X2: Promotion campaign volume lift multiplier [1.0, 2.5]
        # X3: Customer tier baseline [1, 2, 3]
        x_storm = rng.uniform(0.1, 0.9)
        x_promo = rng.uniform(1.0, 2.2)
        x_tier = rng.choice([1.0, 2.0, 3.0])
        X.append([x_storm, x_promo, x_tier])

        # Propensity to be assigned to regional carrier (treatment)
        # Positivity maintained around [0.20, 0.80]
        logit_t = -0.5 + 0.8 * x_storm + 0.2 * x_promo - 0.2 * x_tier
        p_t = 1.0 / (1.0 + math.exp(-logit_t))
        t_i = 1 if rng.random() < p_t else 0
        T.append(t_i)

        # Baseline cancellation probability (without capacity collapse)
        base_rate = 0.04 + 0.03 * x_storm - 0.01 * (x_tier - 1.0)
        # Treatment effect (+0.0660)
        eff = true_ate if t_i == 1 else 0.0
        # Continuous cancellation propensity + Gaussian noise
        y_latent = base_rate + eff + rng.gauss(0.0, 0.015)
        Y.append(max(0.0, min(1.0, y_latent)))

    # Run AIPW estimation
    ate_hat, se_hat, (ci_lower, ci_upper), p_val = causal_module.estimate_aipw_ate(X, T, Y)

    # 1. GATE-CAUSAL-ATE-ERR (NFR-AI-007): Absolute error <= 0.0500
    abs_error = abs(ate_hat - true_ate)
    assert (
        abs_error <= 0.0500
    ), f"GATE-CAUSAL-ATE-ERR violated: |{ate_hat:.4f} - {true_ate:.4f}| = {abs_error:.4f} > 0.0500"

    # 2. GATE-CAUSAL-CI-COV (FR-ML-004, AC-006): 95% CI covers true value
    assert (
        ci_lower <= true_ate <= ci_upper
    ), f"GATE-CAUSAL-CI-COV violated: [{ci_lower:.4f}, {ci_upper:.4f}] does not span true ATE {true_ate:.4f}"

    # 3. GATE-CAUSAL-DIRECTION (FR-ML-004): Significant positive increase
    assert (
        ate_hat > 0.0
    ), f"GATE-CAUSAL-DIRECTION violated: point estimate {ate_hat:.4f} <= 0"
    assert (
        p_val < 0.01
    ), f"GATE-CAUSAL-DIRECTION violated: p-value {p_val:.6f} >= 0.01"
