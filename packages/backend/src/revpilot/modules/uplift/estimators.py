"""
RevPilot AI — CATE Estimators (T-Learner, S-Learner) and Persuadability Classifier
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md §1, §2, §3
Conforms to BR-002, BR-005, FR-ML-003, FR-ML-004, and NFR-AI-007.
"""

from __future__ import annotations
import math
from typing import Optional

from revpilot.modules.uplift.domain import PersuadabilitySegment, UpliftError
from revpilot.modules.causal.estimators import fit_ridge_linear_regression, predict_linear


def classify_persuadability(cate_estimate: float, churn_risk: float) -> PersuadabilitySegment:
    """
    Classify customer into canonical 4-quadrant persuadability taxonomy:
    1. SLEEPING_DOG: tau <= -0.05 (negative uplift: outreach harms retention).
    2. PERSUADABLE: tau >= 0.05 (positive uplift: outreach saves customer).
    3. LOST_CAUSE: |tau| < 0.05 and churn_risk >= 0.50 (high risk, unresponsive).
    4. SURE_THING: |tau| < 0.05 and churn_risk < 0.50 (low/moderate risk, stays anyway).
    """
    if cate_estimate <= -0.0500:
        return PersuadabilitySegment.SLEEPING_DOG
    if cate_estimate >= 0.0500:
        return PersuadabilitySegment.PERSUADABLE
    if churn_risk >= 0.50:
        return PersuadabilitySegment.LOST_CAUSE
    return PersuadabilitySegment.SURE_THING


def estimate_t_learner_cate(
    X_train: list[list[float]],
    T_train: list[int],
    Y_train: list[float],
    X_predict: list[list[float]],
    lambda_ridge: float = 0.01,
) -> list[tuple[float, float, tuple[float, float]]]:
    """
    T-Learner: Estimates CATE by fitting two independent regression surfaces:
    mu_1(X) on treated units (T=1), mu_0(X) on control units (T=0).
    tau(X) = mu_1(X) - mu_0(X).
    Returns list of (cate_estimate, standard_error, (ci_lower, ci_upper)).
    """
    n = len(X_train)
    if n < 4 or len(T_train) != n or len(Y_train) != n:
        raise UpliftError(
            code="ERR_INSUFFICIENT_TRAINING_DATA",
            message="At least 4 observations required to train T-Learner",
        )

    X_treated = [X_train[i] for i in range(n) if T_train[i] == 1]
    Y_treated = [Y_train[i] for i in range(n) if T_train[i] == 1]
    X_control = [X_train[i] for i in range(n) if T_train[i] == 0]
    Y_control = [Y_train[i] for i in range(n) if T_train[i] == 0]

    if len(X_treated) < 2 or len(X_control) < 2:
        raise UpliftError(
            code="ERR_OVERLAP_VIOLATION",
            message="Both treatment and control subsets must have at least 2 samples",
        )

    # Fit mu_1 and mu_0
    beta_1 = fit_ridge_linear_regression(X_treated, Y_treated, lambda_ridge=lambda_ridge)
    beta_0 = fit_ridge_linear_regression(X_control, Y_control, lambda_ridge=lambda_ridge)

    # Compute residual variances
    preds_treated = predict_linear(X_treated, beta_1)
    var_1 = sum((y - p) ** 2 for y, p in zip(Y_treated, preds_treated)) / max(1, len(X_treated) - len(beta_1))

    preds_control = predict_linear(X_control, beta_0)
    var_0 = sum((y - p) ** 2 for y, p in zip(Y_control, preds_control)) / max(1, len(X_control) - len(beta_0))

    # Base standard error
    pooled_se = math.sqrt(max(1e-6, (var_1 / len(X_treated)) + (var_0 / len(X_control))))

    # Predict CATE for test points
    preds_1 = predict_linear(X_predict, beta_1)
    preds_0 = predict_linear(X_predict, beta_0)

    results: list[tuple[float, float, tuple[float, float]]] = []
    z_crit = 1.95996

    for m1, m0 in zip(preds_1, preds_0):
        cate = round(m1 - m0, 4)
        se = round(pooled_se, 4)
        ci_low = round(cate - z_crit * se, 4)
        ci_high = round(cate + z_crit * se, 4)
        results.append((cate, se, (ci_low, ci_high)))

    return results


def estimate_s_learner_cate(
    X_train: list[list[float]],
    T_train: list[int],
    Y_train: list[float],
    X_predict: list[list[float]],
    lambda_ridge: float = 0.01,
) -> list[tuple[float, float, tuple[float, float]]]:
    """
    S-Learner: Fits a single regression model including treatment indicator T as an interaction feature.
    tau(X) = mu(X, 1) - mu(X, 0).
    Returns list of (cate_estimate, standard_error, (ci_lower, ci_upper)).
    """
    n = len(X_train)
    if n < 4:
        raise UpliftError(
            code="ERR_INSUFFICIENT_TRAINING_DATA",
            message="At least 4 observations required to train S-Learner",
        )

    # Augment features with T as last column
    X_aug_train = [X_train[i] + [float(T_train[i])] for i in range(n)]

    beta = fit_ridge_linear_regression(X_aug_train, Y_train, lambda_ridge=lambda_ridge)

    # Compute residual variance
    preds_train = predict_linear(X_aug_train, beta)
    deg_freedom = max(1, n - len(beta))
    res_var = sum((y - p) ** 2 for y, p in zip(Y_train, preds_train)) / deg_freedom
    se = math.sqrt(max(1e-6, res_var / n))

    X_aug_1 = [row + [1.0] for row in X_predict]
    X_aug_0 = [row + [0.0] for row in X_predict]

    preds_1 = predict_linear(X_aug_1, beta)
    preds_0 = predict_linear(X_aug_0, beta)

    results: list[tuple[float, float, tuple[float, float]]] = []
    z_crit = 1.95996

    for m1, m0 in zip(preds_1, preds_0):
        cate = round(m1 - m0, 4)
        se_rounded = round(se, 4)
        ci_low = round(cate - z_crit * se_rounded, 4)
        ci_high = round(cate + z_crit * se_rounded, 4)
        results.append((cate, se_rounded, (ci_low, ci_high)))

    return results
