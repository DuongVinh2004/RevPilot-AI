"""
RevPilot AI — Canonical Claim Verifier Domain Models
Specification: docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md §2
Traceability: INV-AI-001, INV-DATA-001, INV-SEC-002, FR-RCA-002
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Optional, Tuple, List
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import UUIDv7
from revpilot.shared.temporal import UtcDateTime


class ClaimCategory(str, Enum):
    """Formal claim classification taxonomy (§2.1)."""
    DIRECTLY_OBSERVED = "DIRECTLY_OBSERVED"
    DERIVED_STATISTIC = "DERIVED_STATISTIC"
    ASSOCIATION = "ASSOCIATION"
    CAUSAL_ESTIMATE = "CAUSAL_ESTIMATE"
    UNSUPPORTED_INFERENCE = "UNSUPPORTED_INFERENCE"
    POLICY_ACTION_CLAIM = "POLICY_ACTION_CLAIM"


class ClaimVerifierStatus(str, Enum):
    """Verification outcome status (§2.2)."""
    VERIFIED = "VERIFIED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"


class VerifiedClaim(BaseModel):
    """Canonical record representing a verified atomic claim proposition."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    claim_id: str
    hypothesis_id: str
    statement: str
    category: ClaimCategory
    evidence_references: List[UUIDv7] = Field(default_factory=list)
    metric_id: Optional[str] = None
    data_snapshot_digest: Optional[str] = None
    temporal_as_of: UtcDateTime
    calculation_method: Optional[str] = None
    stated_assumptions: List[str] = Field(default_factory=list)
    stated_limitations: List[str] = Field(default_factory=list)
    confidence_interval: Optional[Tuple[float, float]] = None
    verifier_status: ClaimVerifierStatus
    rejection_reason: Optional[str] = None
    verified_at: UtcDateTime
