"""
RevPilot AI — Formal Claim Verification Engine
Specification: docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md §4
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from revpilot.modules.verifier.domain import ClaimCategory, ClaimVerifierStatus, VerifiedClaim
from revpilot.modules.verifier.rules import (
    check_citation_span,
    check_temporal_leakage,
    check_correlation_causation_fallacy,
    check_self_authorization,
)
from revpilot.modules.evidence.domain.models import EvidenceBundle, EvidenceRecord, SupersessionStatus
from revpilot.modules.hypothesis.domain import HypothesisRecord
from revpilot.shared.temporal import UtcDateTime


def verify_claim(
    claim: VerifiedClaim,
    bundle: EvidenceBundle,
    as_of_time: UtcDateTime,
) -> VerifiedClaim:
    now = UtcDateTime.now()

    # Rule 9: Temporal lookahead / Data leakage
    if check_temporal_leakage(claim, as_of_time):
        return claim.model_copy(update={
            "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
            "rejection_reason": "ERR_TEMPORAL_LEAKAGE: Claim as_of exceeds evaluation as_of_time",
            "verified_at": now,
        })

    # Rule 10: Model Self-Authorization
    if check_self_authorization(claim):
        return claim.model_copy(update={
            "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
            "rejection_reason": "ERR_SELF_AUTHORIZATION: Claims cannot authorize actions or override policy",
            "verified_at": now,
        })

    # Rule 5 & 6: Correlation as Causation Fallacy
    if check_correlation_causation_fallacy(claim):
        return claim.model_copy(update={
            "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
            "rejection_reason": "ERR_CORRELATION_AS_CAUSATION: Association claim asserts causal intervention effect",
            "verified_at": now,
        })

    # Category: UNSUPPORTED_INFERENCE is automatically rejected
    if claim.category == ClaimCategory.UNSUPPORTED_INFERENCE:
        return claim.model_copy(update={
            "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
            "rejection_reason": "ERR_UNSUPPORTED_INFERENCE: Speculative or ungrounded statement",
            "verified_at": now,
        })

    # Rule 1: Missing Evidence
    if not claim.evidence_references:
        return claim.model_copy(update={
            "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
            "rejection_reason": "ERR_MISSING_EVIDENCE: Zero evidence references cited",
            "verified_at": now,
        })

    # Find cited records in bundle
    bundle_evidence_map: Dict[str, EvidenceRecord] = {
        str(rec.evidence_id): rec for rec in bundle.evidence_items
    }

    cited_records: List[EvidenceRecord] = []
    for ref_id in claim.evidence_references:
        ref_str = str(ref_id)
        if ref_str not in bundle_evidence_map:
            return claim.model_copy(update={
                "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
                "rejection_reason": f"ERR_UNGROUNDED_EVIDENCE: Cited reference {ref_str} not in evidence bundle",
                "verified_at": now,
            })
        cited_records.append(bundle_evidence_map[ref_str])

    # Evaluate cited records
    for rec in cited_records:
        # Rule 4: Tenant Mismatch
        if rec.tenant_id != bundle.tenant_id:
            return claim.model_copy(update={
                "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
                "rejection_reason": "ERR_TENANT_MISMATCH: Cited evidence belongs to another tenant",
                "verified_at": now,
            })

        # Rule 3: Expired or Superseded Evidence
        if rec.supersession_status in (SupersessionStatus.SUPERSEDED, SupersessionStatus.EXPIRED, SupersessionStatus.REVOKED):
            if rec.superseded_at and rec.superseded_at <= as_of_time:
                return claim.model_copy(update={
                    "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
                    "rejection_reason": "ERR_SUPERSEDED_EVIDENCE: Cited evidence was superseded before as_of_time",
                    "verified_at": now,
                })
            if rec.expiration_time and rec.expiration_time <= as_of_time:
                return claim.model_copy(update={
                    "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
                    "rejection_reason": "ERR_EXPIRED_EVIDENCE: Cited evidence was expired before as_of_time",
                    "verified_at": now,
                })

        # Rule 9: Evidence future temporal leakage
        if rec.effective_time > as_of_time or rec.event_time > as_of_time:
            return claim.model_copy(update={
                "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
                "rejection_reason": "ERR_TEMPORAL_LEAKAGE: Cited evidence timestamp exceeds as_of_time",
                "verified_at": now,
            })

        # Rule 2: Unprovenanced Evidence / Content digest check
        if not rec.content_digest or not rec.source_object_ref:
            return claim.model_copy(update={
                "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
                "rejection_reason": "ERR_UNPROVENANCED_EVIDENCE: Missing source object ref or content digest",
                "verified_at": now,
            })

        # Check citation span
        if not check_citation_span(claim, rec):
            return claim.model_copy(update={
                "verifier_status": ClaimVerifierStatus.UNSUPPORTED,
                "rejection_reason": "ERR_INVALID_CITATION_SPAN: Character offsets or snippet invalid",
                "verified_at": now,
            })

    # Contradiction Detection
    stmt_lower = claim.statement.lower()
    if ("no issue" in stmt_lower or "no outage" in stmt_lower or "zero delay" in stmt_lower) and len(cited_records) > 0:
        for rec in cited_records:
            if rec.payload.get("status") in ("OUTAGE", "DELAYED", "FAILED") or rec.payload.get("delay_minutes", 0) > 0:
                return claim.model_copy(update={
                    "verifier_status": ClaimVerifierStatus.CONTRADICTED,
                    "rejection_reason": "ERR_CONTRADICTED_BY_EVIDENCE: Canonical record directly refutes claim",
                    "verified_at": now,
                })

    return claim.model_copy(update={
        "verifier_status": ClaimVerifierStatus.VERIFIED,
        "rejection_reason": None,
        "verified_at": now,
    })


def verify_hypothesis_claims(
    hypothesis: HypothesisRecord,
    bundle: EvidenceBundle,
    as_of_time: UtcDateTime,
) -> List[VerifiedClaim]:
    now = UtcDateTime.now()
    claims: List[VerifiedClaim] = []
    ev_refs = [ew.evidence_id for ew in hypothesis.supporting_evidence]
    
    primary_claim = VerifiedClaim(
        claim_id=f"clm_{hypothesis.hypothesis_id}_primary",
        hypothesis_id=hypothesis.hypothesis_id,
        statement=hypothesis.statement,
        category=ClaimCategory.CAUSAL_ESTIMATE if hypothesis.ranking_method == "CAUSAL_STUDY_BACKED" else ClaimCategory.DERIVED_STATISTIC,
        evidence_references=ev_refs,
        temporal_as_of=hypothesis.time_window_end,
        verifier_status=ClaimVerifierStatus.NEED_MORE_EVIDENCE if hypothesis.evidence_coverage_ratio < 0.75 else ClaimVerifierStatus.VERIFIED,
        verified_at=now,
    )
    
    verified_primary = verify_claim(primary_claim, bundle, as_of_time)
    claims.append(verified_primary)
    return claims
