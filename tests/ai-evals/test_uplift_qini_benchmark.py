"""
RevPilot AI — Uplift Qini and AUUC Benchmark Suite
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md §4, §5
Evaluation Gates:
  - GATE-UPLIFT-QINI: Normalized Qini Score > 0.2000 (NFR-AI-006)
  - GATE-UPLIFT-AUUC: Area under uplift curve beats random by >= 15% across top 30% scored cohort (NFR-AI-006)
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId


@pytest.fixture(autouse=True)
def _isolate_uplift_modules():
    """Clean uplift modules between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.uplift") or mod.startswith("revpilot.modules.decision"):
            sys.modules.pop(mod, None)


@pytest.fixture
def uplift_module():
    import revpilot.modules.uplift as mod
    return mod


def test_qini_and_auuc_benchmark_gates(uplift_module):
    """
    Evaluates Qini curve and cumulative gain against random targeting.
    Verifies GATE-UPLIFT-QINI (> 0.2000) and GATE-UPLIFT-AUUC (>= 15% gain over random at top 30%).
    """
    # 1. Generate synthetic evaluation population with 400 units:
    # 100 Persuadables (true tau = +0.30), 100 Lost Causes (tau = 0.0),
    # 100 Sure Things (tau = 0.0), 100 Sleeping Dogs (tau = -0.15).
    units: list[dict[str, float]] = []

    # Features: [persuadable_feature, sleeping_dog_feature]
    for i in range(100):
        # Persuadables: high persuadable feature
        units.append({"feat": [1.0, 0.0], "true_tau": 0.30, "t": i % 2, "y_c": 0.20, "y_t": 0.50})
    for i in range(100):
        # Lost causes: low both
        units.append({"feat": [0.0, 0.0], "true_tau": 0.00, "t": i % 2, "y_c": 0.10, "y_t": 0.10})
    for i in range(100):
        # Sure things: low both, high base retention
        units.append({"feat": [0.1, 0.1], "true_tau": 0.00, "t": i % 2, "y_c": 0.85, "y_t": 0.85})
    for i in range(100):
        # Sleeping dogs: high sleeping dog feature
        units.append({"feat": [0.0, 1.0], "true_tau": -0.15, "t": i % 2, "y_c": 0.80, "y_t": 0.65})

    train_x = [u["feat"] for u in units]
    train_t = [int(u["t"]) for u in units]
    # Realized outcome: Y = Y_t if T=1 else Y_c
    train_y = [u["y_t"] if u["t"] == 1 else u["y_c"] for u in units]

    # Predict CATE using T-Learner
    predictions = uplift_module.estimate_t_learner_cate(
        X_train=train_x,
        T_train=train_t,
        Y_train=train_y,
        X_predict=train_x,
    )

    scored_units = []
    for u, (cate_pred, _, _) in zip(units, predictions):
        scored_units.append({
            "pred_cate": cate_pred,
            "true_tau": u["true_tau"],
            "t": u["t"],
            "y": u["y_t"] if u["t"] == 1 else u["y_c"],
        })

    # Sort descending by predicted CATE
    model_sorted = sorted(scored_units, key=lambda u: u["pred_cate"], reverse=True)
    optimal_sorted = sorted(scored_units, key=lambda u: u["true_tau"], reverse=True)

    n = len(scored_units)
    # Compute cumulative uplift curve: u(k) = sum_{i=1}^k (y_i * t_i / n_t) - (y_i * (1 - t_i) / n_c)
    total_treated = sum(u["t"] for u in scored_units)
    total_control = n - total_treated

    def compute_cumulative_uplift(population: list[dict[str, float]]) -> list[float]:
        cum_u = []
        y_t = 0.0
        y_c = 0.0
        for item in population:
            if item["t"] == 1:
                y_t += item["y"]
            else:
                y_c += item["y"]
            # Normalized uplift gain
            u_k = (y_t / total_treated if total_treated > 0 else 0) - (y_c / total_control if total_control > 0 else 0)
            cum_u.append(u_k)
        return cum_u

    u_model = compute_cumulative_uplift(model_sorted)
    u_optimal = compute_cumulative_uplift(optimal_sorted)
    total_uplift = u_model[-1]

    # Random targeting cumulative curve: straight line from 0 to total_uplift
    u_random = [(k / n) * total_uplift for k in range(1, n + 1)]

    # 1. Compute Normalized Qini Score Q = (Area_model - Area_random) / (Area_optimal - Area_random)
    area_model = sum(u_model)
    area_random = sum(u_random)
    area_optimal = sum(u_optimal)

    qini_normalized = (area_model - area_random) / max(1e-6, (area_optimal - area_random))

    # GATE-UPLIFT-QINI: Normalized Qini Score > 0.2000 (NFR-AI-006)
    assert qini_normalized > 0.2000, f"Normalized Qini score {qini_normalized:.4f} not > 0.2000"

    # 2. GATE-UPLIFT-AUUC: Cumulative incremental churn reduction across top 30% scored cohort beats random by >= 15%
    top_30_pct_idx = int(0.30 * n) - 1
    gain_model_top30 = u_model[top_30_pct_idx]
    gain_random_top30 = u_random[top_30_pct_idx]

    assert gain_model_top30 > 0.0, f"Model gain at top 30% ({gain_model_top30}) must be positive"
    improvement_over_random = (gain_model_top30 - gain_random_top30) / max(1e-6, abs(gain_random_top30))
    # Beats random by >= 15% (factor of 1.15)
    assert gain_model_top30 >= 1.15 * gain_random_top30, (
        f"Top 30% model gain {gain_model_top30:.4f} did not beat random {gain_random_top30:.4f} by >= 15%"
    )
