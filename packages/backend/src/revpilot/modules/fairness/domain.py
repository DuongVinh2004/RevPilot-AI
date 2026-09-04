"""
RevPilot AI — Fairness and Disparity Evaluation Domain Models
Specification: docs/11-decision-intelligence/FAIRNESS-SLICE-EVALUATION.md §1..§4
Conforms to BR-002, FR-ML-002..003, INV-AI-001, INV-PRV-001, INV-TEN-001..003, NFR-AI-005..006, and AC-014.
"""

from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError

EvaluationStatus = Literal["EVALUATED", "INSUFFICIENT_SAMPLE", "SUPPRESSED"]
GovernanceStatus = Literal["PASS", "NEEDS_REVIEW", "INSUFFICIENT_DATA"]


class SliceObservation(BaseModel):
    """Single observation record carrying operational slice tags and model outputs."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    customer_id: str
    slice_dimension: str
    slice_value: str
    actual_churn: int = Field(ge=0, le=1)
    predicted_prob: float = Field(ge=0.0, le=1.0)
    cate_estimate: float = Field(default=0.0)
    is_recommended: bool = False


class SliceMetric(BaseModel):
    """Performance and allocation metrics audited within a specific operational slice."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    slice_dimension: str
    slice_value: str
    sample_size: int = Field(ge=0)
    is_statistically_reliable: bool
    pr_auc: float | None = None
    ece: float | None = None
    mean_uplift_cate: float | None = None
    treatment_recommendation_rate: float | None = None
    evaluation_status: EvaluationStatus


class DisparityAuditReport(BaseModel):
    """Canonical, dated empirical audit report documenting subgroup disparity without compliance claims."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    report_id: UUIDv7
    tenant_id: TenantId
    model_artifact_id: str
    decision_policy_id: str
    as_of_time: UtcDateTime
    evaluated_slices: list[SliceMetric]
    max_calibration_disparity: float = Field(ge=0.0)
    max_allocation_disparity_ratio: float = Field(ge=0.0)
    governance_status: GovernanceStatus
    audit_digest: str
    created_at: UtcDateTime


class FairnessError(DomainError):
    """Domain error during fairness or slice audit processing."""

    def __init__(
        self,
        code: str = "ERR_FAIRNESS_AUDIT_ERROR",
        message: str = "Fairness slice audit failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)
