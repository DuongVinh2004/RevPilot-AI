"""
RevPilot AI — Deterministic Investigation Verifier Contract and Verification Engine
Specification: docs/06-agent-platform/MULTI-AGENT-SPEC.md §2.3, §6, §7
Enforces deterministic evidence cross-checking, zero hallucination acceptance,
and NEED_MORE_EVIDENCE fallback (INV-AI-001, FR-RCA-001..002, AC-004, AC-013, AC-P03-006-02).
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.agent.synthesizer import Hypothesis
from revpilot.modules.evidence.domain.models import EvidenceBundle, SupersessionStatus


class VerificationStatus(str, Enum):
    """
    Authoritative verification verdicts.
    Conforms to MULTI-AGENT-SPEC.md §2.3.
    """
    VERIFIED = "VERIFIED"
    REFUTED = "REFUTED"
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"


class VerificationResult(BaseModel):
    """
    Deterministic, typed verification output.
    Strictly suppresses model scratchpads and hidden chains-of-thought (AC-013).
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    investigation_id: UUIDv7
    tenant_id: TenantId
    status: VerificationStatus
    ranked_hypotheses: list[Hypothesis]
    top_hypothesis_id: Optional[str] = None
    evidence_coverage_ratio: float = Field(ge=0.0, le=1.0)
    unsupported_claim_count: int
    contradiction_count: int
    missing_evidence_descriptors: list[str] = Field(default_factory=list)
    verifier_version: str = "v1.0"
    verified_at: UtcDateTime


class InvestigationVerifier:
    """
    Deterministic policy engine that validates candidate hypotheses against
    an immutable evidence bundle without ambient LLM hallucination.
    """

    def verify_hypotheses(
        self,
        hypotheses: list[Hypothesis],
        evidence_bundle: EvidenceBundle,
    ) -> VerificationResult:
        """
        Verify every claim and citation against the sealed evidence bundle:
        - Rejects ungrounded claims and phantom citation IDs (INV-AI-001).
        - Detects authoritative contradictory evidence.
        - Falls back to NEED_MORE_EVIDENCE if coverage < 0.70 or gaps exist (FR-RCA-002, AC-004).
        """
        verified_at = UtcDateTime.now()

        # Handle empty hypotheses
        if not hypotheses:
            return VerificationResult(
                investigation_id=evidence_bundle.investigation_id,
                tenant_id=evidence_bundle.tenant_id,
                status=VerificationStatus.NEED_MORE_EVIDENCE,
                ranked_hypotheses=[],
                top_hypothesis_id=None,
                evidence_coverage_ratio=0.0,
                unsupported_claim_count=0,
                contradiction_count=0,
                missing_evidence_descriptors=["No hypotheses submitted for verification."],
                verifier_version="v1.0",
                verified_at=verified_at,
            )

        # Index bundle items by stringified UUID
        bundle_evidence_map: dict[str, Any] = {}
        for item in evidence_bundle.evidence_items:
            key = item.evidence_id.value if isinstance(item.evidence_id, UUIDv7) else str(item.evidence_id)
            bundle_evidence_map[key] = item

        # If bundle has 0 items, all hypotheses lack evidence
        if not bundle_evidence_map:
            total_unsupported = sum(
                max(len(h.supporting_evidence_ids), 1) + len(h.unverified_claims)
                for h in hypotheses
            )
            return VerificationResult(
                investigation_id=evidence_bundle.investigation_id,
                tenant_id=evidence_bundle.tenant_id,
                status=VerificationStatus.NEED_MORE_EVIDENCE,
                ranked_hypotheses=hypotheses,
                top_hypothesis_id=hypotheses[0].hypothesis_id,
                evidence_coverage_ratio=0.0,
                unsupported_claim_count=total_unsupported,
                contradiction_count=0,
                missing_evidence_descriptors=["Evidence bundle contains zero evidence records."],
                verifier_version="v1.0",
                verified_at=verified_at,
            )

        missing_descriptors: list[str] = []
        hypothesis_evaluations: list[dict[str, Any]] = []

        total_unsupported_claims = 0
        total_contradictions = 0

        for h in hypotheses:
            h_valid_citations = 0
            h_unsupported_citations = 0
            h_contradictions = 0

            # 1. Check citations
            if not h.supporting_evidence_ids:
                h_unsupported_citations += 1
                desc = f"Hypothesis {h.hypothesis_id} lacks supporting evidence citations."
                missing_descriptors.append(desc)
            else:
                for ev_id in h.supporting_evidence_ids:
                    key = ev_id.value if isinstance(ev_id, UUIDv7) else str(ev_id)
                    if key not in bundle_evidence_map:
                        h_unsupported_citations += 1
                        desc = f"Hypothesis {h.hypothesis_id} cites non-existent evidence ID: {key}."
                        missing_descriptors.append(desc)
                    else:
                        record = bundle_evidence_map[key]
                        # Check tenant isolation
                        if str(record.tenant_id) != str(evidence_bundle.tenant_id):
                            h_unsupported_citations += 1
                            desc = f"Hypothesis {h.hypothesis_id} cites cross-tenant evidence ID: {key}."
                            missing_descriptors.append(desc)
                        # Check supersession
                        elif record.supersession_status != SupersessionStatus.ACTIVE:
                            h_unsupported_citations += 1
                            desc = f"Hypothesis {h.hypothesis_id} cites non-active evidence ID: {key} ({record.supersession_status.value})."
                            missing_descriptors.append(desc)
                        else:
                            h_valid_citations += 1

            # 2. Check unverified claims
            h_unverified_claims = len(h.unverified_claims)
            for claim in h.unverified_claims:
                missing_descriptors.append(f"Hypothesis {h.hypothesis_id} has unverified claim: {claim}")

            h_total_unsupported = h_unsupported_citations + h_unverified_claims

            # 3. Check contradicting evidence
            for c_id in h.contradicting_evidence_ids:
                key = c_id.value if isinstance(c_id, UUIDv7) else str(c_id)
                if key in bundle_evidence_map:
                    h_contradictions += 1
                    desc = f"Hypothesis {h.hypothesis_id} contradicted by bundle evidence ID: {key}."
                    missing_descriptors.append(desc)

            total_claims_in_h = len(h.supporting_evidence_ids) + h_unverified_claims
            if total_claims_in_h == 0:
                h_coverage = 0.0
            else:
                h_coverage = max(0.0, min(1.0, h_valid_citations / total_claims_in_h))

            total_unsupported_claims += h_total_unsupported
            total_contradictions += h_contradictions

            hypothesis_evaluations.append({
                "hypothesis": h,
                "coverage": h_coverage,
                "unsupported": h_total_unsupported,
                "contradictions": h_contradictions,
                "valid_citations": h_valid_citations,
                "is_contradicted": h_contradictions > 0,
            })

        # Rank hypotheses:
        # 1. Not contradicted first
        # 2. Highest evidence coverage
        # 3. Lowest unsupported claims
        # 4. Highest likelihood score
        hypothesis_evaluations.sort(
            key=lambda e: (
                not e["is_contradicted"],
                e["coverage"],
                -e["unsupported"],
                e["hypothesis"].likelihood_score,
            ),
            reverse=True,
        )

        ranked_hypotheses = [e["hypothesis"] for e in hypothesis_evaluations]
        top_eval = hypothesis_evaluations[0]
        top_hypo = top_eval["hypothesis"]
        top_coverage = float(top_eval["coverage"])
        top_unsupported = top_eval["unsupported"]
        top_contradicted = top_eval["is_contradicted"]

        # Final verdict determination according to INV-AI-001, FR-RCA-002, and AC-004
        if top_contradicted and not any(not e["is_contradicted"] and e["coverage"] >= 0.70 for e in hypothesis_evaluations):
            final_status = VerificationStatus.REFUTED
        elif (
            top_unsupported > 0
            or top_coverage < 0.70
            or top_hypo.likelihood_score < 0.80
            or not top_hypo.supporting_evidence_ids
        ):
            final_status = VerificationStatus.NEED_MORE_EVIDENCE
        else:
            final_status = VerificationStatus.VERIFIED

        return VerificationResult(
            investigation_id=evidence_bundle.investigation_id,
            tenant_id=evidence_bundle.tenant_id,
            status=final_status,
            ranked_hypotheses=ranked_hypotheses,
            top_hypothesis_id=top_hypo.hypothesis_id,
            evidence_coverage_ratio=top_coverage,
            unsupported_claim_count=total_unsupported_claims,
            contradiction_count=total_contradictions,
            missing_evidence_descriptors=missing_descriptors,
            verifier_version="v1.0",
            verified_at=verified_at,
        )
