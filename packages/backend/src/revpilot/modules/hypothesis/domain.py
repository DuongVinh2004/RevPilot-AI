"""
RevPilot AI — Canonical Hypothesis Domain Models and Invariants
Specification: docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md §1, §2
Conforms to BR-001, BR-002, FR-RCA-001, FR-RCA-002, INV-AI-001..002, and AC-013.
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


class HypothesisType(str, Enum):
    """Business anomaly hypothesis classification."""
    LOGISTICS_BOTTLENECK = "LOGISTICS_BOTTLENECK"
    PAYMENT_GATEWAY_OUTAGE = "PAYMENT_GATEWAY_OUTAGE"
    PRODUCT_QUALITY_DEFECT = "PRODUCT_QUALITY_DEFECT"
    PRICING_CATALOG_MISCONFIGURATION = "PRICING_CATALOG_MISCONFIGURATION"
    EXTERNAL_MACRO_EVENT = "EXTERNAL_MACRO_EVENT"
    CUSTOMER_BEHAVIOR_SHIFT = "CUSTOMER_BEHAVIOR_SHIFT"


class HypothesisStatus(str, Enum):
    """Lifecycle and verification state of hypothesis candidate."""
    PROPOSED = "PROPOSED"
    EVALUATING = "EVALUATING"
    VERIFIED = "VERIFIED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    REFUTED = "REFUTED"
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"


class EpistemicCategory(str, Enum):
    """Strict epistemic ontological taxonomy (§1.1)."""
    OBSERVATION = "OBSERVATION"
    DERIVED_STATISTIC = "DERIVED_STATISTIC"
    ASSOCIATION = "ASSOCIATION"
    MECHANISM_HYPOTHESIS = "MECHANISM_HYPOTHESIS"
    STATISTICAL_SIGNAL = "STATISTICAL_SIGNAL"
    CAUSAL_HYPOTHESIS = "CAUSAL_HYPOTHESIS"
    CAUSAL_ESTIMATE = "CAUSAL_ESTIMATE"
    RECOMMENDATION = "RECOMMENDATION"


class EvidenceWeight(BaseModel):
    """Binding between a hypothesis claim and an immutable evidence item."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    evidence_id: UUIDv7
    content_digest: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    polarity: Literal["SUPPORTING", "CONTRADICTING"]
    citation_span_ref: Optional[str] = None
    provenance_source: str


def compute_hypothesis_digest(
    hypothesis_id: str,
    investigation_id: UUIDv7,
    tenant_id: TenantId,
    statement: str,
    hypothesis_type: HypothesisType,
    supporting_evidence: list[EvidenceWeight],
    contradicting_evidence: list[EvidenceWeight],
) -> str:
    """Produce deterministic SHA-256 digest over canonical hypothesis fields."""
    norm_dict = {
        "hypothesis_id": hypothesis_id,
        "investigation_id": str(investigation_id),
        "tenant_id": str(tenant_id),
        "statement": statement,
        "hypothesis_type": hypothesis_type.value,
        "supporting": sorted([str(e.evidence_id) for e in supporting_evidence]),
        "contradicting": sorted([str(e.evidence_id) for e in contradicting_evidence]),
    }
    clean_json = json.dumps(norm_dict, sort_keys=True)
    return hashlib.sha256(clean_json.encode("utf-8")).hexdigest()


class HypothesisRecord(BaseModel):
    """
    Canonical, versioned hypothesis candidate for an observed business anomaly.
    Conforms to HYPOTHESIS-VERIFIER-SPEC.md §2.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    hypothesis_id: str
    investigation_id: UUIDv7
    tenant_id: TenantId
    statement: str
    epistemic_category: EpistemicCategory = EpistemicCategory.MECHANISM_HYPOTHESIS
    hypothesis_type: HypothesisType
    affected_scope: dict[str, Any]
    time_window_start: UtcDateTime
    time_window_end: UtcDateTime
    supporting_evidence: list[EvidenceWeight] = Field(default_factory=list)
    contradicting_evidence: list[EvidenceWeight] = Field(default_factory=list)
    evidence_coverage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    ordinal_rank: int = Field(default=1, ge=1)
    ranking_score: float = Field(default=0.0, ge=0.0, le=1.0)
    ranking_method: Literal["EVIDENCE_EVALUATION_V1", "CAUSAL_STUDY_BACKED"] = "EVIDENCE_EVALUATION_V1"
    alternative_hypothesis_ids: list[str] = Field(default_factory=list)
    missing_evidence_descriptors: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    causal_study_id: Optional[UUIDv7] = None
    created_at: UtcDateTime
    updated_at: UtcDateTime
    manifest_digest: str = ""


class HypothesisError(DomainError):
    """Domain error during hypothesis operations."""

    def __init__(
        self,
        code: str = "ERR_HYPOTHESIS_ERROR",
        message: str = "Hypothesis operation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)
