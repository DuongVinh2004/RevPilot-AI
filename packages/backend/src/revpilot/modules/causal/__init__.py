"""
RevPilot AI — Causal Inference and Estimand Module
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md
Conforms to BR-001, BR-002, FR-ML-003, FR-ML-004, INV-AI-001, INV-DATA-001, and AC-006.
"""

from revpilot.modules.causal.domain import (
    EstimandType,
    IdentificationStrategy,
    EstimatorType,
    OverlapDiagnostics,
    SensitivityAnalysis,
    CausalStudy,
    CausalInferenceError,
    compute_study_digest,
)
from revpilot.modules.causal.audit import (
    PROHIBITED_VARIABLE_ROLES,
    audit_pre_treatment_covariates,
    audit_temporal_leakage,
    audit_causal_study_specification,
)
from revpilot.modules.causal.overlap import (
    calculate_propensity_scores,
    evaluate_overlap_diagnostics,
)
from revpilot.modules.causal.estimators import (
    fit_ridge_linear_regression,
    predict_linear,
    compute_p_value_two_tailed,
    estimate_aipw_ate,
    estimate_linear_did,
)
from revpilot.modules.causal.sensitivity import (
    calculate_e_value,
    compute_e_value_from_ate,
    calculate_oster_delta,
    conduct_sensitivity_analysis,
)
from revpilot.modules.causal.ports import (
    CausalStudyRepository,
    InMemoryCausalStudyRepository,
)

__all__ = [
    # Domain Enums & Models
    "EstimandType",
    "IdentificationStrategy",
    "EstimatorType",
    "OverlapDiagnostics",
    "SensitivityAnalysis",
    "CausalStudy",
    "CausalInferenceError",
    "compute_study_digest",
    # Audit Engine
    "PROHIBITED_VARIABLE_ROLES",
    "audit_pre_treatment_covariates",
    "audit_temporal_leakage",
    "audit_causal_study_specification",
    # Overlap Engine
    "calculate_propensity_scores",
    "evaluate_overlap_diagnostics",
    # Estimators Engine
    "fit_ridge_linear_regression",
    "predict_linear",
    "compute_p_value_two_tailed",
    "estimate_aipw_ate",
    "estimate_linear_did",
    # Sensitivity Engine
    "calculate_e_value",
    "compute_e_value_from_ate",
    "calculate_oster_delta",
    "conduct_sensitivity_analysis",
    # Ports & Adapters
    "CausalStudyRepository",
    "InMemoryCausalStudyRepository",
]
