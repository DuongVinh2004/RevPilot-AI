"""
RevPilot AI — Unit Tests for 11 Strict Rejection Rules
Specification: docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md §3
"""

from __future__ import annotations
import pytest
from datetime import timedelta
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
def bundle_fixture():
    tenant_id = TenantId("tnt_rule_test")
    now = UtcDateTime.now()
    payload = {"status": "FAILED", "delay_minutes": 120}
    rec = EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        acl_policy_ref="tier_1_ops",
        source_system=SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="shipment_99",
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
        investigation_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        evidence_count=1,
        evidence_items=[rec],
        bundle_digest="digest_test",
        sealed_at=now,
    )
    return bundle, rec, now

def test_rule_temporal_leakage(bundle_fixture):
    bundle, rec, now = bundle_fixture
    future_time = UtcDateTime.from_datetime(now.value + timedelta(days=1))
    claim = VerifiedClaim(
        claim_id="clm_future",
        hypothesis_id="hypo_01",
        statement="Future lookahead claim",
        category=ClaimCategory.DIRECTLY_OBSERVED,
        evidence_references=[rec.evidence_id],
        temporal_as_of=future_time,
        verifier_status=ClaimVerifierStatus.NEED_MORE_EVIDENCE,
        verified_at=now,
    )
    res = verify_claim(claim, bundle, now)
    assert res.verifier_status == ClaimVerifierStatus.UNSUPPORTED
    assert "ERR_TEMPORAL_LEAKAGE" in res.rejection_reason

def test_rule_correlation_as_causation(bundle_fixture):
    bundle, rec, now = bundle_fixture
    claim = VerifiedClaim(
        claim_id="clm_fallacy",
        hypothesis_id="hypo_01",
        statement="Carrier change caused order drop because of correlation",
        category=ClaimCategory.ASSOCIATION,
        evidence_references=[rec.evidence_id],
        temporal_as_of=now,
        verifier_status=ClaimVerifierStatus.NEED_MORE_EVIDENCE,
        verified_at=now,
    )
    res = verify_claim(claim, bundle, now)
    assert res.verifier_status == ClaimVerifierStatus.UNSUPPORTED
    assert "ERR_CORRELATION_AS_CAUSATION" in res.rejection_reason

def test_rule_self_authorization(bundle_fixture):
    bundle, rec, now = bundle_fixture
    claim = VerifiedClaim(
        claim_id="clm_self_auth",
        hypothesis_id="hypo_01",
        statement="I authorize a $500 waiver and grant access immediately",
        category=ClaimCategory.POLICY_ACTION_CLAIM,
        evidence_references=[rec.evidence_id],
        temporal_as_of=now,
        verifier_status=ClaimVerifierStatus.NEED_MORE_EVIDENCE,
        verified_at=now,
    )
    res = verify_claim(claim, bundle, now)
    assert res.verifier_status == ClaimVerifierStatus.UNSUPPORTED
    assert "ERR_SELF_AUTHORIZATION" in res.rejection_reason

def test_rule_contradiction_detection(bundle_fixture):
    bundle, rec, now = bundle_fixture
    claim = VerifiedClaim(
        claim_id="clm_contradicted",
        hypothesis_id="hypo_01",
        statement="Facility experienced no issue and zero delay",
        category=ClaimCategory.DIRECTLY_OBSERVED,
        evidence_references=[rec.evidence_id],
        temporal_as_of=now,
        verifier_status=ClaimVerifierStatus.NEED_MORE_EVIDENCE,
        verified_at=now,
    )
    res = verify_claim(claim, bundle, now)
    assert res.verifier_status == ClaimVerifierStatus.CONTRADICTED
    assert "ERR_CONTRADICTED_BY_EVIDENCE" in res.rejection_reason
