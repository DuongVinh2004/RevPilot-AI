"""
RevPilot AI — Unit Tests for Claim Verifier
Specification: docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md
"""

from __future__ import annotations
import pytest
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.verifier.domain import (
    ClaimCategory,
    ClaimVerifierStatus,
    VerifiedClaim,
)
from revpilot.modules.verifier.engine import verify_claim
from revpilot.modules.evidence.domain.models import (
    EvidenceBundle,
    EvidenceRecord,
    SourceSystemType,
    ClassificationLevel,
    ExtractionMethod,
    RetrievalMethod,
    SupersessionStatus,
    compute_content_digest,
)

@pytest.fixture
def sample_bundle():
    tenant_id = TenantId("tnt_verifier_test")
    inv_id = UUIDv7.generate()
    ev_id = UUIDv7.generate()
    now = UtcDateTime.now()
    payload = {"delay_minutes": 180, "carrier": "TRUCK_CORP"}
    
    rec = EvidenceRecord(
        evidence_id=ev_id,
        tenant_id=tenant_id,
        acl_policy_ref="tier_1_ops",
        source_system=SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="shipment_01",
        source_version="v1.0",
        content_digest=compute_content_digest(payload),
        classification=ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=SupersessionStatus.ACTIVE,
        extraction_method=ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0",
        retrieval_method=RetrievalMethod.SQL_DIRECT,
        confidence_score=1.0,
        payload=payload,
    )
    
    bundle = EvidenceBundle(
        bundle_id=UUIDv7.generate(),
        investigation_id=inv_id,
        tenant_id=tenant_id,
        evidence_count=1,
        evidence_items=[rec],
        bundle_digest="digest_abc123",
        sealed_at=now,
    )
    return bundle, rec

def test_verifier_accepts_valid_claim(sample_bundle):
    bundle, rec = sample_bundle
    now = UtcDateTime.now()
    claim = VerifiedClaim(
        claim_id="clm_01",
        hypothesis_id="hypo_01",
        statement="Shipment delayed by 180 minutes",
        category=ClaimCategory.DIRECTLY_OBSERVED,
        evidence_references=[rec.evidence_id],
        temporal_as_of=now,
        verifier_status=ClaimVerifierStatus.NEED_MORE_EVIDENCE,
        verified_at=now,
    )
    result = verify_claim(claim, bundle, now)
    assert result.verifier_status == ClaimVerifierStatus.VERIFIED
    assert result.rejection_reason is None

def test_verifier_rejects_missing_evidence(sample_bundle):
    bundle, _ = sample_bundle
    now = UtcDateTime.now()
    claim = VerifiedClaim(
        claim_id="clm_02",
        hypothesis_id="hypo_01",
        statement="Ungrounded hallucination claim",
        category=ClaimCategory.DIRECTLY_OBSERVED,
        evidence_references=[],
        temporal_as_of=now,
        verifier_status=ClaimVerifierStatus.NEED_MORE_EVIDENCE,
        verified_at=now,
    )
    result = verify_claim(claim, bundle, now)
    assert result.verifier_status == ClaimVerifierStatus.UNSUPPORTED
    assert "ERR_MISSING_EVIDENCE" in result.rejection_reason

def test_verifier_rejects_unsupported_inference(sample_bundle):
    bundle, rec = sample_bundle
    now = UtcDateTime.now()
    claim = VerifiedClaim(
        claim_id="clm_03",
        hypothesis_id="hypo_01",
        statement="It probably was caused by sunspots",
        category=ClaimCategory.UNSUPPORTED_INFERENCE,
        evidence_references=[rec.evidence_id],
        temporal_as_of=now,
        verifier_status=ClaimVerifierStatus.NEED_MORE_EVIDENCE,
        verified_at=now,
    )
    result = verify_claim(claim, bundle, now)
    assert result.verifier_status == ClaimVerifierStatus.UNSUPPORTED
    assert "ERR_UNSUPPORTED_INFERENCE" in result.rejection_reason
