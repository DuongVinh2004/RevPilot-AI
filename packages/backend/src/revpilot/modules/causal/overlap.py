"""
RevPilot AI — Positivity, Propensity Overlap Diagnostics & Common Support Gate
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §1.1, §3, §5 Step 3
Conforms to BR-001, BR-002, FR-ML-004, INV-AI-001, AC-006, and GATE-CAUSAL-OVERLAP.
"""

from __future__ import annotations
import math
from typing import Optional

from revpilot.modules.causal.domain import OverlapDiagnostics, CausalInferenceError


def calculate_propensity_scores(
    X: list[list[float]],
    T: list[int],
    learning_rate: float = 0.1,
    lambda_l2: float = 0.01,
    epochs: int = 120,
) -> list[float]:
    """
    Fit a deterministic L2-regularized logistic regression model to estimate propensity scores:
    e(X) = P(T=1 | X).
    Pure Python implementation guaranteeing reproducibility and no external dependencies.
    """
    n = len(X)
    if n == 0 or len(T) != n:
        raise CausalInferenceError(
            code="ERR_INVALID_SAMPLE_DATA",
            message=f"Sample size mismatch: X has {n} rows, T has {len(T)} labels",
        )

    p = len(X[0])
    if p == 0:
        # Trivial model: average treatment rate
        rate = sum(T) / n
        rate_clamped = max(0.001, min(0.999, rate))
        return [rate_clamped] * n

    # Step 1: Compute feature standardization (z-score)
    means = [0.0] * p
    for row in X:
        for j in range(p):
            means[j] += row[j]
    means = [m / n for m in means]

    stds = [0.0] * p
    for row in X:
        for j in range(p):
            diff = row[j] - means[j]
            stds[j] += diff * diff
    stds = [math.sqrt(s / n) if s > 1e-12 else 1.0 for s in stds]

    Z = [[(row[j] - means[j]) / stds[j] for j in range(p)] for row in X]

    # Step 2: Fit weights [w0, w1, ..., wp] using gradient descent
    w = [0.0] * (p + 1)

    for _ in range(epochs):
        grad = [0.0] * (p + 1)
        for i in range(n):
            z = w[0] + sum(w[j + 1] * Z[i][j] for j in range(p))
            z_clamped = max(-20.0, min(20.0, z))
            pred = 1.0 / (1.0 + math.exp(-z_clamped))
            err = pred - T[i]
            grad[0] += err
            for j in range(p):
                grad[j + 1] += err * Z[i][j]

        # Parameter update
        w[0] -= (learning_rate / n) * grad[0]
        for j in range(p):
            w[j + 1] -= (learning_rate / n) * grad[j + 1] + (learning_rate * lambda_l2 / n) * w[j + 1]

    # Step 3: Compute final propensity scores
    scores: list[float] = []
    for i in range(n):
        z = w[0] + sum(w[j + 1] * Z[i][j] for j in range(p))
        z_clamped = max(-20.0, min(20.0, z))
        prob = 1.0 / (1.0 + math.exp(-z_clamped))
        scores.append(round(max(0.0001, min(0.9999, prob)), 5))

    return scores


def evaluate_overlap_diagnostics(
    propensity_scores: list[float],
    T: list[int],
    min_cutoff: float = 0.05,
    max_cutoff: float = 0.95,
    required_common_support_ratio: float = 0.80,
) -> OverlapDiagnostics:
    """
    Step 3: Positivity & Overlap Gate.
    Evaluates common support across treatment and control cohorts.
    Enforces:
    1. Propensity scores must fall in [min_cutoff, max_cutoff].
    2. Both treatment (T=1) and control (T=0) units must exist within common support.
    3. Common support ratio must meet or exceed required threshold (default 80%).
    Halts with ERR_OVERLAP_VIOLATION if violated.
    """
    if len(propensity_scores) == 0 or len(T) != len(propensity_scores):
        raise CausalInferenceError(
            code="ERR_INVALID_SAMPLE_DATA",
            message="Propensity scores and treatment labels must be non-empty and of equal length",
        )

    n = len(propensity_scores)
    min_prop = min(propensity_scores)
    max_prop = max(propensity_scores)

    # Count common support units
    in_support_indices = [
        i for i, p in enumerate(propensity_scores) if min_cutoff <= p <= max_cutoff
    ]
    trimmed_count = n - len(in_support_indices)
    common_support_ratio = round(len(in_support_indices) / n, 4)

    # Check presence of both treated and control within common support
    treated_in_support = any(T[i] == 1 for i in in_support_indices)
    control_in_support = any(T[i] == 0 for i in in_support_indices)

    positivity_satisfied = (
        common_support_ratio >= required_common_support_ratio
        and treated_in_support
        and control_in_support
    )

    if not positivity_satisfied:
        reason_parts = []
        if common_support_ratio < required_common_support_ratio:
            reason_parts.append(
                f"Common support ratio {common_support_ratio:.2%} < required {required_common_support_ratio:.2%}"
            )
        if not treated_in_support:
            reason_parts.append("No treated units (T=1) found within common support window")
        if not control_in_support:
            reason_parts.append("No control units (T=0) found within common support window")

        raise CausalInferenceError(
            code="ERR_OVERLAP_VIOLATION",
            message=f"Positivity and overlap violation: {'; '.join(reason_parts)}. Deterministic treatment assignment or lack of common support prohibits causal estimation.",
            details={
                "min_propensity": min_prop,
                "max_propensity": max_prop,
                "common_support_ratio": common_support_ratio,
                "trimmed_sample_count": trimmed_count,
                "treated_in_support": treated_in_support,
                "control_in_support": control_in_support,
            },
        )

    return OverlapDiagnostics(
        min_propensity=min_prop,
        max_propensity=max_prop,
        positivity_satisfied=True,
        common_support_ratio=common_support_ratio,
        trimmed_sample_count=trimmed_count,
    )
