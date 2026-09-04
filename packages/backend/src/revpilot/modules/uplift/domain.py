"""
RevPilot AI — Canonical Uplift & Heterogeneous Treatment Effect Domain Models
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md §2
Conforms to BR-002, BR-005, FR-ML-003, FR-ML-004, INV-AI-001, INV-TEN-001..003, and AC-006.
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


class UpliftEstimatorType(str, Enum):
    """Meta-learner and non-parametric causal uplift estimation engines."""
    T_LEARNER = "T_LEARNER"
    S_LEARNER = "S_LEARNER"
    X_LEARNER = "X_LEARNER"
    CAUSAL_FOREST = "CAUSAL_FOREST"


class PersuadabilitySegment(str, Enum):
    """
    Canonical 4-quadrant persuadability segmentation:
    - PERSUADABLE: Retained if and only if treated (tau >= 0.05).
    - SURE_THING: Retained regardless of treatment (churn_risk <= 0.10, |tau| < 0.05).
    - LOST_CAUSE: Churns regardless of treatment (churn_risk >= 0.70, |tau| < 0.05).
    - SLEEPING_DOG: Churns BECAUSE of unsolicited treatment (tau <= -0.05).
    """
    PERSUADABLE = "PERSUADABLE"
    SURE_THING = "SURE_THING"
    LOST_CAUSE = "LOST_CAUSE"
    SLEEPING_DOG = "SLEEPING_DOG"


def compute_uplift_digest(
    score_id: UUIDv7,
    tenant_id: TenantId,
    customer_id: str,
    intervention_type: str,
    cate_estimate: float,
    persuadability_segment: PersuadabilitySegment,
    feature_snapshot_digest: str,
) -> str:
    """Produce deterministic SHA-256 digest over uplift prediction record."""
    norm_dict = {
        "score_id": str(score_id),
        "tenant_id": str(tenant_id),
        "customer_id": customer_id,
        "intervention_type": intervention_type,
        "cate_estimate": round(cate_estimate, 4),
        "persuadability_segment": persuadability_segment.value,
        "feature_snapshot_digest": feature_snapshot_digest,
    }
    clean_json = json.dumps(norm_dict, sort_keys=True)
    return hashlib.sha256(clean_json.encode("utf-8")).hexdigest()


class UpliftScoreRecord(BaseModel):
    """
    Canonical, versioned uplift score record estimating individual CATE.
    Conforms to UPLIFT-BENCHMARK-PROTOCOL.md §2 and FR-ML-003.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    score_id: UUIDv7
    tenant_id: TenantId
    customer_id: str
    intervention_type: str
    as_of_time: UtcDateTime
    model_artifact_id: str
    cate_estimate: float               # Incremental retention probability change: E[Y(1) - Y(0) | X]
    standard_error: float = Field(ge=0.0)
    confidence_interval_95: tuple[float, float]
    persuadability_segment: PersuadabilitySegment
    overlap_satisfied: bool
    feature_snapshot_digest: str
    score_digest: str = ""
    created_at: UtcDateTime


class UpliftError(DomainError):
    """Domain error during uplift scoring and segmentation."""

    def __init__(
        self,
        code: str = "ERR_UPLIFT_ERROR",
        message: str = "Uplift operation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)
