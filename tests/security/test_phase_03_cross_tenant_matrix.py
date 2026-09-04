"""
RevPilot AI — Phase 03 Cross-Tenant Negative Security Matrix
Specification: docs/06-agent-platform/MULTI-AGENT-SPEC.md §1, docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md
Verifies INV-TEN-001..003, INV-SEC-001..003, and AC-P03-008-02.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_modules():
    """Ensure modules are isolated between test runs to protect dependency rules."""
    yield
    for mod in list(sys.modules.keys()):
        if any(
            mod.startswith(p)
            for p in (
                "revpilot.modules.investigation",
                "revpilot.modules.analytics",
                "revpilot.modules.evidence",
                "revpilot.modules.retrieval",
                "revpilot.modules.agent",
                "revpilot.modules.tickets",
            )
        ):
            sys.modules.pop(mod, None)


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha_corp")


@pytest.fixture
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta_adversary")


@pytest.fixture
def sample_investigation_id() -> UUIDv7:
    return UUIDv7.generate()


# =============================================================================
# Cross-Tenant Negative Matrix Tests
# =============================================================================

def test_cross_tenant_ticket_isolation(tenant_alpha, tenant_beta):
    """INV-TEN-001: Support tickets ingested for Tenant Beta cannot be accessed by Tenant Alpha."""
    from revpilot.modules.tickets.domain.models import InMemoryTicketStore, CanonicalTicket, TicketStatus, TicketPriority, compute_ticket_digest

    store = InMemoryTicketStore()
    now = UtcDateTime.now()

    ticket_beta = CanonicalTicket(
        ticket_id="TCK-BETA-01",
        tenant_id=tenant_beta,
        source_system="ZENDESK",
        version=1,
        customer_id="cus_beta_1",
        created_at=now,
        updated_at=now,
        status=TicketStatus.OPEN,
        priority=TicketPriority.HIGH,
        category="BILLING",
        subject_masked="Beta private dispute",
        body_masked="Confidential customer dispute for Beta.",
        sentiment_score=-0.5,
        injection_risk_score=0.0,
        is_quarantined=False,
        content_digest=compute_ticket_digest("Confidential customer dispute for Beta."),
    )
    store.ingest(ticket_beta)

    # Tenant Alpha queries their tickets
    alpha_tickets = store.list_by_tenant(tenant_alpha)
    assert len(alpha_tickets) == 0

    # Tenant Alpha cannot fetch Beta's ticket directly
    retrieved = store.get(tenant_alpha, "ZENDESK", "TCK-BETA-01")
    assert retrieved is None


def test_cross_tenant_evidence_bundle_isolation(tenant_alpha, tenant_beta, sample_investigation_id):
    """INV-EVD-001, INV-TEN-001: Evidence bundle packaging strictly rejects foreign tenant items."""
    from revpilot.modules.evidence.domain.models import (
        EvidenceRecord,
        SourceSystemType,
        ClassificationLevel,
        SupersessionStatus,
        ExtractionMethod,
        RetrievalMethod,
        compute_content_digest,
    )
    from revpilot.modules.evidence import package_evidence_bundle

    now = UtcDateTime.now()
    alpha_payload = {"revenue": 1000}
    alpha_item = EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=tenant_alpha,
        acl_policy_ref="policy_read",
        source_system=SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="canonical_orders:1",
        source_version="v1",
        content_digest=compute_content_digest(alpha_payload),
        classification=ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=SupersessionStatus.ACTIVE,
        extraction_method=ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0.0",
        retrieval_method=RetrievalMethod.SQL_DIRECT,
        confidence_score=0.95,
        payload=alpha_payload,
    )

    beta_payload = {"revenue": 999999}
    foreign_beta_item = EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=tenant_beta,
        acl_policy_ref="policy_read",
        source_system=SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="canonical_orders:2",
        source_version="v1",
        content_digest=compute_content_digest(beta_payload),
        classification=ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=SupersessionStatus.ACTIVE,
        extraction_method=ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0.0",
        retrieval_method=RetrievalMethod.SQL_DIRECT,
        confidence_score=0.95,
        payload=beta_payload,
    )

    # Packaging a bundle for Tenant Alpha with foreign Beta items must fail with cross-tenant violation
    res = package_evidence_bundle(
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        records=[alpha_item, foreign_beta_item],
        verify_digests=True,
    )
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_CROSS_TENANT_EVIDENCE"


def test_cross_tenant_verifier_citation_rejection(tenant_alpha, tenant_beta, sample_investigation_id):
    """INV-AI-001: Verifier flags any cross-tenant citations as unsupported."""
    from revpilot.modules.evidence.domain.models import (
        EvidenceRecord,
        EvidenceBundle,
        SourceSystemType,
        ClassificationLevel,
        SupersessionStatus,
        ExtractionMethod,
        RetrievalMethod,
    )
    from revpilot.modules.agent.verifier import InvestigationVerifier, VerificationStatus
    from revpilot.modules.agent.synthesizer import Hypothesis

    now = UtcDateTime.now()
    foreign_rec = EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=tenant_beta,
        acl_policy_ref="policy_read",
        source_system=SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="canonical_orders:foreign",
        source_version="v1",
        content_digest="digest_foreign",
        classification=ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=SupersessionStatus.ACTIVE,
        extraction_method=ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0.0",
        retrieval_method=RetrievalMethod.SQL_DIRECT,
        confidence_score=0.90,
        payload={},
    )

    bundle = EvidenceBundle(
        bundle_id=UUIDv7.generate(),
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        evidence_count=1,
        evidence_items=[foreign_rec],
        bundle_digest="mock_digest",
        sealed_at=now,
    )

    hypo = Hypothesis(
        hypothesis_id="hypo_foreign",
        title="Cross Tenant Breach Claim",
        description="Hypothesis claiming insight from foreign tenant data.",
        likelihood_score=0.90,
        supporting_evidence_ids=[foreign_rec.evidence_id],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=[],
    )

    verifier = InvestigationVerifier()
    result = verifier.verify_hypotheses([hypo], bundle)

    assert result.status == VerificationStatus.NEED_MORE_EVIDENCE
    assert result.unsupported_claim_count >= 1
    assert any("cross-tenant" in d for d in result.missing_evidence_descriptors)
