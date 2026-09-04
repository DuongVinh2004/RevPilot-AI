"""
RevPilot AI — Uplift CATE Accuracy Benchmark
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md §3, §4
Evaluation Gate: GATE-UPLIFT-CATE-ERR (NFR-AI-007)
Mean Absolute CATE Error <= 0.0400 against synthetic ground truth across 4 canonical cohorts:
  - Cohort A (Persuadables): tau* > 0.1500
  - Cohort B (Lost Causes): tau* <= 0.0200
  - Cohort C (Sure Things): tau* <= 0.0200
  - Cohort D (Sleeping Dogs): tau* < -0.0500
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_uplift_modules():
    """Clean uplift and causal modules between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.uplift") or mod.startswith("revpilot.modules.decision"):
            sys.modules.pop(mod, None)


@pytest.fixture
def uplift_module():
    import revpilot.modules.uplift as mod
    return mod


def test_uplift_cate_accuracy_four_cohorts(uplift_module):
    """
    Train and evaluate T-Learner on 4 synthetic cohorts.
    Verifies GATE-UPLIFT-CATE-ERR (MAE <= 0.0400) and cohort point estimate gates.
    """
    tenant_id = TenantId("tnt_logistics_benchmark")
    now = UtcDateTime.now()

    # Synthetic training data generator:
    # Feature x_1: customer sensitivity/engagement [0, 1]
    # Cohort A (Persuadable, x1 in [0.75, 1.0]): stay if treated Y(1)=0, leave if control Y(0)=1 -> tau* = 1 - 0 = +1.0 (or scaled retention gain)
    # Let's model Y as retention (1 = retained, 0 = churned):
    # Persuadable: Y(1) = 1, Y(0) = 0 -> tau* = +0.25
    # Lost cause (x1 in [0.5, 0.75]): Y(1) = 0, Y(0) = 0 -> tau* = 0.0
    # Sure thing (x1 in [0.25, 0.5]): Y(1) = 1, Y(0) = 1 -> tau* = 0.0
    # Sleeping dog (x1 in [0.0, 0.25]): Y(1) = 0, Y(0) = 1 -> tau* = -0.10

    # We generate balanced RCT training data (T in {0, 1})
    train_x: list[list[float]] = []
    train_t: list[int] = []
    train_y: list[float] = []

    # 400 training samples (100 per cohort, 50 treated, 50 control)
    cohort_specs = [
        # (cohort_name, one_hot_feat, p_y_control, p_y_treated, true_tau)
        ("A_PERSUADABLE", [1.0, 0.0, 0.0, 0.0], 0.40, 0.65, 0.25),   # tau* = +0.25
        ("B_LOST_CAUSE", [0.0, 1.0, 0.0, 0.0], 0.10, 0.10, 0.00),    # tau* = 0.00
        ("C_SURE_THING", [0.0, 0.0, 1.0, 0.0], 0.90, 0.90, 0.00),    # tau* = 0.00
        ("D_SLEEPING_DOG", [0.0, 0.0, 0.0, 1.0], 0.85, 0.75, -0.10), # tau* = -0.10
    ]

    for _, feat, p_c, p_t, _ in cohort_specs:
        # 50 controls
        for i in range(50):
            train_x.append(feat)
            train_t.append(0)
            train_y.append(1.0 if (i / 50.0) < p_c else 0.0)
        # 50 treated
        for i in range(50):
            train_x.append(feat)
            train_t.append(1)
            train_y.append(1.0 if (i / 50.0) < p_t else 0.0)

    # Test points corresponding to each cohort
    test_specs = [
        ("Cohort A (Persuadables)", [1.0, 0.0, 0.0, 0.0], 0.25),
        ("Cohort B (Lost Causes)", [0.0, 1.0, 0.0, 0.0], 0.00),
        ("Cohort C (Sure Things)", [0.0, 0.0, 1.0, 0.0], 0.00),
        ("Cohort D (Sleeping Dogs)", [0.0, 0.0, 0.0, 1.0], -0.10),
    ]

    abs_errors: list[float] = []
    estimates: dict[str, float] = {}

    for name, x_eval, true_tau in test_specs:
        res = uplift_module.estimate_t_learner_cate(
            X_train=train_x,
            T_train=train_t,
            Y_train=train_y,
            X_predict=[x_eval],
        )
        cate_est, se_est, ci_est = res[0]
        err = abs(cate_est - true_tau)
        abs_errors.append(err)
        estimates[name] = cate_est

    # 1. GATE-UPLIFT-CATE-ERR: Mean Absolute CATE Error <= 0.0400 (NFR-AI-007)
    mean_abs_error = sum(abs_errors) / len(abs_errors)
    assert mean_abs_error <= 0.0400, f"Mean Absolute CATE Error {mean_abs_error:.4f} > 0.0400"

    # 2. Benchmark gates for cohort point estimates
    assert estimates["Cohort A (Persuadables)"] > 0.1500, (
        f"Cohort A CATE {estimates['Cohort A (Persuadables)']} not > 0.1500"
    )
    assert estimates["Cohort B (Lost Causes)"] <= 0.0200, (
        f"Cohort B CATE {estimates['Cohort B (Lost Causes)']} not <= 0.0200"
    )
    assert estimates["Cohort C (Sure Things)"] <= 0.0200, (
        f"Cohort C CATE {estimates['Cohort C (Sure Things)']} not <= 0.0200"
    )
    assert estimates["Cohort D (Sleeping Dogs)"] < -0.0500, (
        f"Cohort D CATE {estimates['Cohort D (Sleeping Dogs)']} not < -0.0500"
    )
