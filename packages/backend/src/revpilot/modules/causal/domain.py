"""
RevPilot AI — Canonical Causal Study Domain Contract and Invariants
Specification: docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md §1, §2
Conforms to BR-001, BR-002, FR-ML-003, FR-ML-004, INV-AI-001, INV-DATA-001, INV-TEN-001..003, AC-006, AC-014.
"""

from __future__ import annotations
import hashlib
import json
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError


class EstimandType(str, Enum):
    """Formal causal estimand targets."""
    ATE = "ATE"    # Average Treatment Effect: E[Y(1) - Y(0)]
    ATT = "ATT"    # Average Treatment Effect on the Treated: E[Y(1) - Y(0) | T=1]
    ATC = "ATC"    # Average Treatment Effect on the Controls: E[Y(1) - Y(0) | T=0]
    CATE = "CATE"  # Conditional Average Treatment Effect: E[Y(1) - Y(0) | X=x]


class IdentificationStrategy(str, Enum):
    """Causal identification framework based on graphical and structural assumptions."""
    BACKDOOR_ADJUSTMENT = "BACKDOOR_ADJUSTMENT"
    DIFFERENCE_IN_DIFFERENCES = "DIFFERENCE_IN_DIFFERENCES"
    INSTRUMENTAL_VARIABLES = "INSTRUMENTAL_VARIABLES"
    SYNTHETIC_CONTROL = "SYNTHETIC_CONTROL"


class EstimatorType(str, Enum):
    """Deterministic statistical estimation engine."""
    DOUBLY_ROBUST_AIPW = "DOUBLY_ROBUST_AIPW"
    TMLE = "TMLE"
    TWO_STAGE_LEAST_SQUARES = "TWO_STAGE_LEAST_SQUARES"
    LINEAR_DID = "LINEAR_DID"


class OverlapDiagnostics(BaseModel):
    """Positivity and common support diagnostic indicators."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    min_propensity: float = Field(ge=0.0, le=1.0)
    max_propensity: float = Field(ge=0.0, le=1.0)
    positivity_satisfied: bool
    common_support_ratio: float = Field(ge=0.0, le=1.0)
    trimmed_sample_count: int = Field(ge=0)


class SensitivityAnalysis(BaseModel):
    """Robustness to unobserved confounding evaluation."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    method: Literal["ROSENBAUM_BOUNDS", "OSTER_DELTA", "E_VALUE"]
    robustness_value: float
    e_value_estimate: float = Field(ge=1.0)
    e_value_ci: float = Field(ge=1.0)
    is_sensitive_to_unobserved_confounding: bool


def compute_study_digest(
    study_id: UUIDv7,
    investigation_id: UUIDv7,
    tenant_id: TenantId,
    causal_question: str,
    treatment_variable: str,
    outcome_variable: str,
    estimand_type: EstimandType,
    identification_strategy: IdentificationStrategy,
    estimator: EstimatorType,
    reproducibility_seed: int,
) -> str:
    """Produce deterministic SHA-256 digest over canonical causal study specification."""
    norm_dict = {
        "study_id": str(study_id),
        "investigation_id": str(investigation_id),
        "tenant_id": str(tenant_id),
        "causal_question": causal_question,
        "treatment_variable": treatment_variable,
        "outcome_variable": outcome_variable,
        "estimand_type": estimand_type.value,
        "identification_strategy": identification_strategy.value,
        "estimator": estimator.value,
        "reproducibility_seed": reproducibility_seed,
    }
    clean_json = json.dumps(norm_dict, sort_keys=True)
    return hashlib.sha256(clean_json.encode("utf-8")).hexdigest()


class CausalStudy(BaseModel):
    """
    Canonical, immutable causal study aggregate.
    Conforms to CAUSAL-INFERENCE-SPEC.md §2 and FR-ML-004.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    study_id: UUIDv7
    investigation_id: UUIDv7
    tenant_id: TenantId
    causal_question: str
    treatment_variable: str
    outcome_variable: str
    unit_of_analysis: str
    target_population: str
    treatment_window_start: UtcDateTime
    treatment_window_end: UtcDateTime
    outcome_window_start: UtcDateTime
    outcome_window_end: UtcDateTime
    as_of_time: UtcDateTime
    pre_treatment_covariates: list[str]
    post_treatment_exclusions: list[str]
    estimand_type: EstimandType
    identification_strategy: IdentificationStrategy
    causal_dag_ref: str
    explicit_assumptions: list[str]
    estimator: EstimatorType
    overlap: OverlapDiagnostics
    point_estimate: float
    standard_error: float = Field(ge=0.0)
    confidence_interval_95: tuple[float, float]
    p_value: float = Field(ge=0.0, le=1.0)
    sensitivity: SensitivityAnalysis
    subgroup_estimates: dict[str, tuple[float, float]] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    reproducibility_seed: int
    study_digest: str = ""
    created_at: UtcDateTime


class CausalInferenceError(DomainError):
    """Base domain error for causal identification, audit, and estimation."""

    def __init__(
        self,
        code: str = "ERR_CAUSAL_INFERENCE_ERROR",
        message: str = "Causal inference operation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)
