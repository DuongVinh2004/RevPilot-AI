"""
RevPilot AI — Sensitivity Analysis & Falsification Engine (E-Value & Oster Delta)
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §2, §3, §5 Step 5
Conforms to BR-001, BR-002, FR-ML-004, AC-006, and GATE-CAUSAL-SENSITIVITY.
"""

from __future__ import annotations
import math
from typing import Literal

from revpilot.modules.causal.domain import SensitivityAnalysis, CausalInferenceError


def calculate_e_value(risk_ratio: float) -> float:
    """
    Compute E-value for a given Risk Ratio (VanderWeele & Ding, 2017).
    E-value = RR + sqrt(RR * (RR - 1)) for RR >= 1.
    Represents the minimum strength of association on risk ratio scale that an unmeasured
    confounder must have with both treatment and outcome to explain away the observed effect.
    """
    if risk_ratio <= 1.0:
        return 1.0
    val = risk_ratio + math.sqrt(risk_ratio * (risk_ratio - 1.0))
    return max(1.0, round(val, 4))


def compute_e_value_from_ate(
    ate: float,
    ci_lower: float,
    baseline_risk: float = 0.04,
) -> tuple[float, float]:
    """
    Convert absolute additive risk difference (ATE) into approximate Risk Ratio
    and compute E-value for point estimate and the 95% confidence interval bound.
    """
    if baseline_risk <= 0.0:
        raise CausalInferenceError(
            code="ERR_INVALID_BASELINE_RISK",
            message=f"Baseline risk must be strictly positive, got {baseline_risk}",
        )

    # Estimate Risk Ratio
    treated_risk_est = baseline_risk + ate
    if treated_risk_est <= 0.0:
        rr_est = 1.0
    else:
        rr_est = treated_risk_est / baseline_risk

    if 0.0 < rr_est < 1.0:
        rr_est = 1.0 / rr_est
    e_est = calculate_e_value(rr_est)

    # If the 95% confidence interval spans the null (ci_lower <= 0 <= ate or ate <= 0 <= ci_upper),
    # then the E-value for the CI is analytically 1.0 (VanderWeele & Ding 2017).
    if (ate >= 0.0 and ci_lower <= 0.0) or (ate <= 0.0 and ci_lower >= 0.0):
        e_ci = 1.0
    else:
        # CI lower bound Risk Ratio
        treated_risk_ci = baseline_risk + ci_lower
        if treated_risk_ci <= 0.0:
            rr_ci = 1.0
        else:
            rr_ci = treated_risk_ci / baseline_risk

        if 0.0 < rr_ci < 1.0:
            rr_ci = 1.0 / rr_ci
        e_ci = calculate_e_value(rr_ci)

    return e_est, e_ci


def calculate_oster_delta(
    r_squared_controlled: float,
    r_squared_max: float,
    beta_controlled: float,
    beta_uncontrolled: float,
) -> float:
    """
    Compute Oster (2019) bounding parameter delta representing degree of selection on unobservables.
    A delta > 1.0 indicates selection on unobservables would need to be greater than selection on
    observables to explain away the result.
    """
    num = beta_controlled * max(0.0, r_squared_max - r_squared_controlled)
    denom = (beta_uncontrolled - beta_controlled) * max(1e-6, r_squared_controlled)
    if abs(denom) < 1e-9:
        return 999.0  # Stable effect under covariate adjustment
    val = num / denom
    return round(abs(val), 4)


def conduct_sensitivity_analysis(
    ate: float,
    ci_lower: float,
    baseline_risk: float = 0.04,
    sensitivity_threshold: float = 1.50,
    method: Literal["E_VALUE", "OSTER_DELTA", "ROSENBAUM_BOUNDS"] = "E_VALUE",
) -> SensitivityAnalysis:
    """
    Step 5: Sensitivity & Falsification Analysis.
    Evaluates robustness to unobserved confounding.
    Sets is_sensitive_to_unobserved_confounding = True if E-value estimate is below
    the sensitivity threshold or if the 95% CI E-value falls to 1.0.
    """
    e_est, e_ci = compute_e_value_from_ate(
        ate=ate,
        ci_lower=ci_lower,
        baseline_risk=baseline_risk,
    )

    # Flag sensitive if point estimate is fragile or CI spans null (e_ci == 1.0)
    is_sensitive = (e_est < sensitivity_threshold) or (e_ci <= 1.05)

    return SensitivityAnalysis(
        method=method,
        robustness_value=e_est,
        e_value_estimate=e_est,
        e_value_ci=e_ci,
        is_sensitive_to_unobserved_confounding=is_sensitive,
    )
