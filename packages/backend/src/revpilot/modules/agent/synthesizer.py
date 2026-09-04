"""
RevPilot AI — Hypothesis Synthesizer Contract and Models
Specification: docs/06-agent-platform/MULTI-AGENT-SPEC.md §2.3, §3
Implements HypothesisSynthesizer generating grounded candidate hypotheses.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import UUIDv7
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure
from revpilot.modules.evidence.domain.models import EvidenceBundle, SupersessionStatus


class Hypothesis(BaseModel):
    """
    Candidate root cause hypothesis backed by verifiable evidence citations.
    Conforms to MULTI-AGENT-SPEC.md §2.3.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    hypothesis_id: str
    title: str
    description: str
    likelihood_score: float = Field(ge=0.0, le=1.0)
    supporting_evidence_ids: list[UUIDv7]
    contradicting_evidence_ids: list[UUIDv7] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class SynthesizerError(DomainError):
    """Domain error during hypothesis synthesis."""

    def __init__(
        self,
        code: str = "ERR_SYNTHESIZER_FAILURE",
        message: str = "Hypothesis synthesis failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)


class HypothesisSynthesizer:
    """
    Synthesizes candidate root-cause hypotheses grounded in verified evidence bundles.
    """

    async def synthesize(
        self,
        evidence_bundle: EvidenceBundle,
    ) -> Result[list[Hypothesis], SynthesizerError]:
        """
        Produce ranked candidate hypotheses from evidence bundle records.
        """
        if not evidence_bundle.evidence_items:
            return Success([])

        active_items = [
            item for item in evidence_bundle.evidence_items
            if item.supersession_status == SupersessionStatus.ACTIVE
            and item.authorization_decision == "PERMITTED"
        ]

        if not active_items:
            return Success([])

        # Calculate base heuristic likelihood from evidence confidence scores
        avg_confidence = sum(item.confidence_score for item in active_items) / len(active_items)
        heuristic_likelihood = round(min(max(avg_confidence, 0.1), 0.95), 2)

        supporting_ids = [item.evidence_id for item in active_items]

        # Primary hypothesis synthesized from active evidence records
        primary_hypo = Hypothesis(
            hypothesis_id="hypo_01",
            title="Evidence-Grounded Anomaly Hypothesis",
            description=f"Synthesized root cause based on {len(active_items)} verified evidence items.",
            likelihood_score=heuristic_likelihood,
            supporting_evidence_ids=supporting_ids,
            contradicting_evidence_ids=[],
            unverified_claims=[],
            limitations=[
                f"Scoped to {len(active_items)} active evidence records in bundle {evidence_bundle.bundle_id.value}",
                "Citations require deterministic verification against evidence store",
            ],
        )

        return Success([primary_hypo])
