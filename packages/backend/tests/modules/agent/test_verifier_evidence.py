"""
RevPilot AI — Unit and Contract Tests for Deterministic Investigation Verifier
Specification: docs/06-agent-platform/MULTI-AGENT-SPEC.md §2.3, §6, §7
Enforces AC-P03-006-02: Hypotheses lacking supporting citations or having unverified claims
are rejected or marked NEED_MORE_EVIDENCE (INV-AI-001, FR-RCA-002, AC-004, AC-013).
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_agent_and_evidence_modules():
    """Ensure agent and evidence modules are isolated and cleaned up between test cases."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.agent") or mod.startswith("revpilot.modules.evidence"):
            sys.modules.pop(mod, None)


@pytest.fixture
def agent_module():
    """Lazily load agent module to avoid top-level test collection contamination."""
    import revpilot.modules.agent as mod
    return mod


@pytest.fixture
def evidence_module():
    """Lazily load evidence module to avoid top-level test collection contamination."""
    import revpilot.modules.evidence as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_alpha_corp")


@pytest.fixture
def sample_investigation_id() -> UUIDv7:
    return UUIDv7.generate()


def _make_evidence_record(
    evidence_mod,
    tenant_id: TenantId,
    evidence_id: UUIDv7 | None = None,
    supersession_status=None,
    superseded_at: UtcDateTime | None = None,
):
    """Helper to produce valid immutable EvidenceRecord."""
    now = UtcDateTime.now()
    status = supersession_status or evidence_mod.SupersessionStatus.ACTIVE
    return evidence_mod.EvidenceRecord(
        evidence_id=evidence_id or UUIDv7.generate(),
        tenant_id=tenant_id,
        acl_policy_ref="policy_rev_read",
        source_system=evidence_mod.SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="canonical_orders:tier=enterprise",
        source_version="v1",
        content_digest="abc123sha256fake",
        classification=evidence_mod.ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=status,
        superseded_at=superseded_at,
        extraction_method=evidence_mod.ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0.0",
        retrieval_method=evidence_mod.RetrievalMethod.SQL_DIRECT,
        confidence_score=0.92,
        payload={"tier": "enterprise", "mrr_loss": 50000},
    )


def _make_evidence_bundle(
    evidence_mod,
    tenant_id: TenantId,
    investigation_id: UUIDv7,
    items: list,
):
    """Helper to produce a sealed EvidenceBundle."""
    return evidence_mod.EvidenceBundle(
        bundle_id=UUIDv7.generate(),
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        evidence_count=len(items),
        evidence_items=items,
        bundle_digest="bundle_digest_sha256_mock",
        sealed_at=UtcDateTime.now(),
    )


# =============================================================================
# AC-P03-006-02: Citation Verification and Verdict Determinism
# =============================================================================

def test_verifier_accepts_fully_grounded_hypothesis(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """Hypothesis with valid active citations, no contradictions, and high likelihood is VERIFIED."""
    rec1 = _make_evidence_record(evidence_module, sample_tenant)
    rec2 = _make_evidence_record(evidence_module, sample_tenant)
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [rec1, rec2])

    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_01",
        title="Enterprise tier churn surge",
        description="Cancellation spike detected in tier enterprise.",
        likelihood_score=0.88,
        supporting_evidence_ids=[rec1.evidence_id, rec2.evidence_id],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == agent_module.VerificationStatus.VERIFIED
    assert result.top_hypothesis_id == "hypo_01"
    assert result.evidence_coverage_ratio == 1.0
    assert result.unsupported_claim_count == 0
    assert result.contradiction_count == 0


def test_verifier_rejects_hallucinated_citation_ids(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """AC-P03-006-02: Phantom citations not in evidence bundle yield NEED_MORE_EVIDENCE (INV-AI-001)."""
    rec1 = _make_evidence_record(evidence_module, sample_tenant)
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [rec1])

    phantom_id = UUIDv7.generate()
    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_phantom",
        title="Hallucinated Root Cause",
        description="Asserts causation using phantom evidence.",
        likelihood_score=0.90,
        supporting_evidence_ids=[rec1.evidence_id, phantom_id],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == agent_module.VerificationStatus.NEED_MORE_EVIDENCE
    assert result.unsupported_claim_count >= 1
    assert any("cites non-existent evidence ID" in d for d in result.missing_evidence_descriptors)


def test_verifier_flags_hypothesis_lacking_citations(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """AC-P03-006-02: Hypothesis lacking citations must fall back to NEED_MORE_EVIDENCE (AC-004)."""
    rec1 = _make_evidence_record(evidence_module, sample_tenant)
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [rec1])

    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_uncited",
        title="Uncited Speculation",
        description="Speculation without any evidence attachment.",
        likelihood_score=0.85,
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == agent_module.VerificationStatus.NEED_MORE_EVIDENCE
    assert result.unsupported_claim_count >= 1
    assert result.evidence_coverage_ratio == 0.0


def test_verifier_flags_unverified_claims(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """AC-P03-006-02: Presence of unverified claims forces NEED_MORE_EVIDENCE."""
    rec1 = _make_evidence_record(evidence_module, sample_tenant)
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [rec1])

    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_claims",
        title="Partially Grounded Hypothesis",
        description="One verified fact and one unsupported assertion.",
        likelihood_score=0.85,
        supporting_evidence_ids=[rec1.evidence_id],
        contradicting_evidence_ids=[],
        unverified_claims=["Competitor price drop caused immediate enterprise contract cancellations."],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == agent_module.VerificationStatus.NEED_MORE_EVIDENCE
    assert result.unsupported_claim_count >= 1
    assert any("unverified claim" in d for d in result.missing_evidence_descriptors)


def test_verifier_rejects_superseded_evidence_citations(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """Citations pointing to superseded/revoked evidence are treated as unsupported."""
    superseded_rec = _make_evidence_record(
        evidence_module,
        sample_tenant,
        supersession_status=evidence_module.SupersessionStatus.SUPERSEDED,
        superseded_at=UtcDateTime.now(),
    )
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [superseded_rec])

    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_stale",
        title="Stale Evidence Hypothesis",
        description="Relies on superseded evidence records.",
        likelihood_score=0.85,
        supporting_evidence_ids=[superseded_rec.evidence_id],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == agent_module.VerificationStatus.NEED_MORE_EVIDENCE
    assert result.unsupported_claim_count >= 1


def test_verifier_rejects_cross_tenant_evidence_citations(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """Cross-tenant evidence in bundle is rejected as unauthorized citation."""
    foreign_tenant = TenantId("tnt_beta_adversary")
    cross_rec = _make_evidence_record(evidence_module, foreign_tenant)
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [cross_rec])

    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_cross",
        title="Cross Tenant Hypothesis",
        description="Illegally references foreign tenant evidence.",
        likelihood_score=0.85,
        supporting_evidence_ids=[cross_rec.evidence_id],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == agent_module.VerificationStatus.NEED_MORE_EVIDENCE
    assert result.unsupported_claim_count >= 1


def test_verifier_marks_refuted_on_authoritative_contradiction(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """Hypothesis contradicted by authoritative evidence in bundle yields REFUTED status."""
    rec_support = _make_evidence_record(evidence_module, sample_tenant)
    rec_contradict = _make_evidence_record(evidence_module, sample_tenant)
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [rec_support, rec_contradict])

    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_refuted",
        title="Disproven Hypothesis",
        description="Hypothesis contradicts authoritative billing records.",
        likelihood_score=0.90,
        supporting_evidence_ids=[rec_support.evidence_id],
        contradicting_evidence_ids=[rec_contradict.evidence_id],
        unverified_claims=[],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == agent_module.VerificationStatus.REFUTED
    assert result.contradiction_count >= 1
    assert any("contradicted by bundle evidence" in d for d in result.missing_evidence_descriptors)


def test_verifier_empty_evidence_bundle_fallback(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """Empty evidence bundle always results in NEED_MORE_EVIDENCE."""
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [])

    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_any",
        title="Hypothesis in Vacuum",
        description="No evidence available anywhere.",
        likelihood_score=0.85,
        supporting_evidence_ids=[UUIDv7.generate()],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == agent_module.VerificationStatus.NEED_MORE_EVIDENCE
    assert result.evidence_coverage_ratio == 0.0


def test_verifier_low_likelihood_fallback(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """Even with 100% evidence coverage, likelihood < 0.80 results in NEED_MORE_EVIDENCE."""
    rec = _make_evidence_record(evidence_module, sample_tenant)
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [rec])

    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_low_conf",
        title="Uncertain Hypothesis",
        description="Supported by evidence but low confidence model score.",
        likelihood_score=0.65,  # < 0.80 threshold
        supporting_evidence_ids=[rec.evidence_id],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == agent_module.VerificationStatus.NEED_MORE_EVIDENCE


def test_verifier_suppresses_chain_of_thought(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """AC-013: VerificationResult schema strictly suppresses model scratchpad or prompt leakage."""
    rec = _make_evidence_record(evidence_module, sample_tenant)
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [rec])

    hypo = agent_module.Hypothesis(
        hypothesis_id="hypo_clean",
        title="Clean Hypothesis",
        description="Well grounded.",
        likelihood_score=0.90,
        supporting_evidence_ids=[rec.evidence_id],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=[],
    )

    verifier = agent_module.InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)
    dumped = result.model_dump()

    forbidden_keys = [
        "scratchpad",
        "thought",
        "chain_of_thought",
        "cot",
        "raw_prompt",
        "prompt",
        "internal_reasoning",
    ]
    for key in forbidden_keys:
        assert key not in dumped, f"VerificationResult illegally exposed {key}"


# =============================================================================
# HypothesisSynthesizer Unit Tests
# =============================================================================

@pytest.mark.asyncio
async def test_hypothesis_synthesizer_produces_grounded_candidates(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """HypothesisSynthesizer extracts active evidence and constructs candidate hypotheses."""
    rec1 = _make_evidence_record(evidence_module, sample_tenant)
    rec2 = _make_evidence_record(evidence_module, sample_tenant)
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [rec1, rec2])

    synthesizer = agent_module.HypothesisSynthesizer()
    res = await synthesizer.synthesize(bundle)

    assert res.is_success
    hypotheses = res.unwrap()
    assert len(hypotheses) == 1
    top_hypo = hypotheses[0]
    assert rec1.evidence_id in top_hypo.supporting_evidence_ids
    assert rec2.evidence_id in top_hypo.supporting_evidence_ids
    assert top_hypo.likelihood_score >= 0.80


@pytest.mark.asyncio
async def test_hypothesis_synthesizer_handles_empty_bundle(agent_module, evidence_module, sample_tenant, sample_investigation_id):
    """HypothesisSynthesizer gracefully returns empty list when bundle has no items."""
    bundle = _make_evidence_bundle(evidence_module, sample_tenant, sample_investigation_id, [])

    synthesizer = agent_module.HypothesisSynthesizer()
    res = await synthesizer.synthesize(bundle)

    assert res.is_success
    assert res.unwrap() == []
