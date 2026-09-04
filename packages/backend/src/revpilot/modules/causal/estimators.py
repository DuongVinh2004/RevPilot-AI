"""
RevPilot AI — Deterministic Causal Estimators (Doubly Robust AIPW & Linear DiD)
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §2, §4, §5 Step 4
Conforms to BR-001, BR-002, FR-ML-004, NFR-AI-007, AC-006, and GATE-CAUSAL-ATE-ERR.
"""

from __future__ import annotations
import math
from typing import Optional

from revpilot.modules.causal.domain import CausalInferenceError
from revpilot.modules.causal.overlap import calculate_propensity_scores


def _solve_linear_system(A: list[list[float]], b: list[float]) -> list[float]:
    """Solve A * x = b using Gaussian elimination with partial pivoting."""
    n = len(A)
    # Augment A with b
    M = [row[:] + [b[i]] for i, row in enumerate(A)]

    for i in range(n):
        # Pivot selection
        max_row = i
        max_val = abs(M[i][i])
        for k in range(i + 1, n):
            if abs(M[k][i]) > max_val:
                max_val = abs(M[k][i])
                max_row = k

        if max_val < 1e-12:
            # Singular matrix, add ridge jitter to diagonal
            M[i][i] += 1e-6

        if max_row != i:
            M[i], M[max_row] = M[max_row], M[i]

        # Eliminate below
        pivot = M[i][i]
        for k in range(i + 1, n):
            factor = M[k][i] / pivot
            for j in range(i, n + 1):
                M[k][j] -= factor * M[i][j]

    # Back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = (M[i][n] - s) / M[i][i]

    return x


def fit_ridge_linear_regression(
    X: list[list[float]],
    Y: list[float],
    lambda_ridge: float = 0.01,
) -> list[float]:
    """
    Fit linear regression model: Y = beta_0 + sum(beta_j * X_j).
    Returns beta vector of length (p + 1) with beta[0] as intercept.
    Deterministic analytic solution via normal equations: (X_aug^T * X_aug + lambda * I) * beta = X_aug^T * Y.
    """
    n = len(X)
    if n == 0 or len(Y) != n:
        raise CausalInferenceError(
            code="ERR_INVALID_SAMPLE_DATA",
            message=f"Sample size mismatch: X has {n} rows, Y has {len(Y)} targets",
        )

    p = len(X[0])
    m = p + 1  # Including intercept

    # Construct normal equation matrix A = X_aug^T * X_aug + lambda * I
    A = [[0.0] * m for _ in range(m)]
    b = [0.0] * m

    for i in range(n):
        row_aug = [1.0] + X[i]
        y_i = Y[i]
        for j in range(m):
            b[j] += row_aug[j] * y_i
            for k in range(m):
                A[j][k] += row_aug[j] * row_aug[k]

    # Add ridge penalty to coefficients (excluding intercept)
    for j in range(1, m):
        A[j][j] += lambda_ridge

    return _solve_linear_system(A, b)


def predict_linear(X: list[list[float]], beta: list[float]) -> list[float]:
    """Predict target using fitted beta coefficients."""
    preds = []
    p = len(beta) - 1
    for row in X:
        val = beta[0] + sum(beta[j + 1] * row[j] for j in range(p))
        preds.append(val)
    return preds


def compute_p_value_two_tailed(z: float) -> float:
    """Compute two-tailed p-value from standard normal z-statistic using math.erf."""
    abs_z = abs(z)
    # 2 * (1 - Phi(abs_z)) = 1 - erf(abs_z / sqrt(2))
    p = 1.0 - math.erf(abs_z / math.sqrt(2.0))
    return max(0.0, min(1.0, round(p, 6)))


def estimate_aipw_ate(
    X: list[list[float]],
    T: list[int],
    Y: list[float],
    propensity_scores: Optional[list[float]] = None,
    min_propensity: float = 0.05,
    max_propensity: float = 0.95,
) -> tuple[float, float, tuple[float, float], float]:
    """
    Augmented Inverse Probability Weighting (AIPW) Doubly Robust ATE Estimator.
    Returns:
    (point_estimate, standard_error, (ci_lower, ci_upper), p_value)
    """
    n = len(X)
    if n < 4:
        raise CausalInferenceError(
            code="ERR_INSUFFICIENT_SAMPLE",
            message="At least 4 samples required for AIPW estimation",
        )

    # Step 1: Propensity scores e(X)
    if propensity_scores is None:
        propensity_scores = calculate_propensity_scores(X, T)

    # Step 2: Separate treatment and control sets for outcome modeling
    X_treated = [X[i] for i in range(n) if T[i] == 1]
    Y_treated = [Y[i] for i in range(n) if T[i] == 1]
    X_control = [X[i] for i in range(n) if T[i] == 0]
    Y_control = [Y[i] for i in range(n) if T[i] == 0]

    if not X_treated or not X_control:
        raise CausalInferenceError(
            code="ERR_OVERLAP_VIOLATION",
            message="Both treated and control cohorts required for AIPW estimation",
        )

    # Step 3: Fit outcome models mu_1(X) and mu_0(X)
    beta_1 = fit_ridge_linear_regression(X_treated, Y_treated)
    beta_0 = fit_ridge_linear_regression(X_control, Y_control)

    mu_1_all = predict_linear(X, beta_1)
    mu_0_all = predict_linear(X, beta_0)

    # Step 4: Compute individual AIPW scores psi_i
    psi: list[float] = []
    for i in range(n):
        e_i = max(min_propensity, min(max_propensity, propensity_scores[i]))
        t_i = T[i]
        y_i = Y[i]
        m1_i = mu_1_all[i]
        m0_i = mu_0_all[i]

        val = (m1_i - m0_i) + (t_i * (y_i - m1_i) / e_i) - ((1 - t_i) * (y_i - m0_i) / (1.0 - e_i))
        psi.append(val)

    # Step 5: Point estimate
    ate = sum(psi) / n

    # Step 6: Influence function variance and Standard Error
    variance = sum((psi_i - ate) ** 2 for psi_i in psi) / (n * (n - 1))
    se = math.sqrt(max(0.0, variance))

    # Step 7: 95% Confidence Interval (z = 1.95996)
    z_crit = 1.95996
    ci_lower = ate - z_crit * se
    ci_upper = ate + z_crit * se

    # Step 8: Two-tailed p-value
    z_stat = (ate / se) if se > 1e-9 else 0.0
    p_val = compute_p_value_two_tailed(z_stat)

    return (
        round(ate, 4),
        round(se, 4),
        (round(ci_lower, 4), round(ci_upper, 4)),
        round(p_val, 6),
    )


def estimate_linear_did(
    Y_pre_treatment: list[float],
    Y_post_treatment: list[float],
    Y_pre_control: list[float],
    Y_post_control: list[float],
) -> tuple[float, float, tuple[float, float], float]:
    """
    Linear Difference-in-Differences (DiD) Estimator.
    ATE = (Y_post_treatment - Y_pre_treatment) - (Y_post_control - Y_pre_control)
    Returns:
    (point_estimate, standard_error, (ci_lower, ci_upper), p_value)
    """
    for grp in (Y_pre_treatment, Y_post_treatment, Y_pre_control, Y_post_control):
        if len(grp) < 2:
            raise CausalInferenceError(
                code="ERR_INSUFFICIENT_SAMPLE",
                message="Each DiD cohort must have at least 2 observations",
            )

    def _mean_var(vals: list[float]) -> tuple[float, float]:
        m = sum(vals) / len(vals)
        v = sum((x - m) ** 2 for x in vals) / (len(vals) - 1)
        return m, v

    m_treat_pre, v_treat_pre = _mean_var(Y_pre_treatment)
    m_treat_post, v_treat_post = _mean_var(Y_post_treatment)
    m_ctrl_pre, v_ctrl_pre = _mean_var(Y_pre_control)
    m_ctrl_post, v_ctrl_post = _mean_var(Y_post_control)

    delta_treat = m_treat_post - m_treat_pre
    delta_ctrl = m_ctrl_post - m_ctrl_pre

    ate = delta_treat - delta_ctrl

    se_squared = (
        v_treat_post / len(Y_post_treatment)
        + v_treat_pre / len(Y_pre_treatment)
        + v_ctrl_post / len(Y_post_control)
        + v_ctrl_pre / len(Y_pre_control)
    )
    se = math.sqrt(max(0.0, se_squared))

    z_crit = 1.95996
    ci_lower = ate - z_crit * se
    ci_upper = ate + z_crit * se

    z_stat = (ate / se) if se > 1e-9 else 0.0
    p_val = compute_p_value_two_tailed(z_stat)

    return (
        round(ate, 4),
        round(se, 4),
        (round(ci_lower, 4), round(ci_upper, 4)),
        round(p_val, 6),
    )
