"""
RevPilot AI — Unit and Contract Tests for Evidence Provenance and Packaging
Specification: docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md §1, §2, §3
Verifies AC-P03-004-01: Deterministic bundle digests, citation spans, and immutable provenance.
"""

from __future__ import annotations
import sys
from typing import TYPE_CHECKING
import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from revpilot.modules.evidence.domain.models import CitationSpan, EvidenceBundle

from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_evidence_module():
    """Ensure evidence module is clean between test runs and during collection."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.evidence"):
            sys.modules.pop(mod, None)


@pytest.fixture
def evidence_module():
    """Lazily load evidence module to prevent collection-phase pollution."""
    import revpilot.modules.evidence as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_alpha_corp")


@pytest.fixture
def tenant_context(sample_tenant) -> TenantContext:
    return TenantContext(
        tenant_id=sample_tenant,
        organization_id=OrganizationId("org_alpha"),
        tier="growth",
    )


@pytest.fixture
def now() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-05-18T12:00:00.000000Z")


@pytest.fixture
def sample_payload() -> dict:
    return {
        "metric": "order_cancellation_rate",
        "spike_factor": 2.45,
        "affected_carrier": "FEDEX",
        "notes": "Severe delay at regional sorting facility",
    }


@pytest.fixture
def sample_citation(evidence_module) -> CitationSpan:
    return evidence_module.CitationSpan(
        chunk_id="chunk_wms_sla_004",
        section_id="sec_carrier_sla",
        start_char=120,
        end_char=280,
        snippet_text="Carrier delivery failures exceeding 4 hours result in 2% SLA rebate penalty.",
    )


def test_citation_span_validation(evidence_module, sample_citation):
    """Verify CitationSpan preserves offsets and validates bounds."""
    assert sample_citation.chunk_id == "chunk_wms_sla_004"
    assert sample_citation.start_char == 120
    assert sample_citation.end_char == 280
    assert "SLA rebate penalty" in sample_citation.snippet_text

    # Negative: start_char >= end_char rejected
    with pytest.raises(ValidationError):
        evidence_module.CitationSpan(
            chunk_id="chunk_bad",
            start_char=200,
            end_char=100,
            snippet_text="Invalid span",
        )

    with pytest.raises(ValidationError):
        evidence_module.CitationSpan(
            chunk_id="chunk_bad",
            start_char=150,
            end_char=150,
            snippet_text="Zero length span",
        )


def test_evidence_record_provenance_and_digest(evidence_module, sample_tenant, now, sample_payload, sample_citation):
    """Verify EvidenceRecord creation and deterministic content digest computation (INV-EVD-001)."""
    digest = evidence_module.compute_content_digest(sample_payload)
    assert len(digest) == 64

    record = evidence_module.EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        acl_policy_ref="policy:wms:carrier_read",
        source_system=evidence_module.SourceSystemType.WMS_FULFILLMENT,
        source_object_ref="wms/reports/2026-05-18/delays.json",
        source_version="git:9a8b7c6d",
        content_digest=digest,
        classification=evidence_module.ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=evidence_module.SupersessionStatus.ACTIVE,
        extraction_method=evidence_module.ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0.0",
        retrieval_method=evidence_module.RetrievalMethod.SQL_DIRECT,
        citation_span=sample_citation,
        confidence_score=0.98,
        payload=sample_payload,
    )

    assert record.tenant_id == sample_tenant
    assert record.content_digest == digest
    assert record.citation_span == sample_citation
    assert record.supersession_status == evidence_module.SupersessionStatus.ACTIVE


def test_bundle_digest_determinism(evidence_module, sample_tenant, now):
    """
    Verify bundle digest calculation is completely deterministic and order-independent (AC-P03-004-01).
    """
    payload_1 = {"id": 1, "value": "first"}
    payload_2 = {"id": 2, "value": "second"}
    payload_3 = {"id": 3, "value": "third"}

    rec1 = evidence_module.EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        acl_policy_ref="policy:default",
        source_system=evidence_module.SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="orders/1",
        source_version="v1",
        content_digest=evidence_module.compute_content_digest(payload_1),
        classification=evidence_module.ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=evidence_module.SupersessionStatus.ACTIVE,
        extraction_method=evidence_module.ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0",
        retrieval_method=evidence_module.RetrievalMethod.SQL_DIRECT,
        confidence_score=1.0,
        payload=payload_1,
    )

    rec2 = evidence_module.EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        acl_policy_ref="policy:default",
        source_system=evidence_module.SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="orders/2",
        source_version="v1",
        content_digest=evidence_module.compute_content_digest(payload_2),
        classification=evidence_module.ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=evidence_module.SupersessionStatus.ACTIVE,
        extraction_method=evidence_module.ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0",
        retrieval_method=evidence_module.RetrievalMethod.SQL_DIRECT,
        confidence_score=1.0,
        payload=payload_2,
    )

    rec3 = evidence_module.EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        acl_policy_ref="policy:default",
        source_system=evidence_module.SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="orders/3",
        source_version="v1",
        content_digest=evidence_module.compute_content_digest(payload_3),
        classification=evidence_module.ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=evidence_module.SupersessionStatus.ACTIVE,
        extraction_method=evidence_module.ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0",
        retrieval_method=evidence_module.RetrievalMethod.SQL_DIRECT,
        confidence_score=1.0,
        payload=payload_3,
    )

    # Digest with order [1, 2, 3] vs [3, 1, 2]
    d1 = evidence_module.compute_bundle_digest([rec1, rec2, rec3])
    d2 = evidence_module.compute_bundle_digest([rec3, rec1, rec2])
    assert d1 == d2
    assert len(d1) == 64


def test_package_evidence_bundle_success(evidence_module, sample_tenant, now, sample_payload):
    """Verify package_evidence_bundle packages valid records into a sealed bundle."""
    inv_id = UUIDv7.generate()
    record = evidence_module.EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        acl_policy_ref="policy:default",
        source_system=evidence_module.SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="orders/101",
        source_version="v1",
        content_digest=evidence_module.compute_content_digest(sample_payload),
        classification=evidence_module.ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=evidence_module.SupersessionStatus.ACTIVE,
        extraction_method=evidence_module.ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0",
        retrieval_method=evidence_module.RetrievalMethod.SQL_DIRECT,
        confidence_score=0.95,
        payload=sample_payload,
    )

    result = evidence_module.package_evidence_bundle(
        investigation_id=inv_id,
        tenant_id=sample_tenant,
        records=[record],
        as_of_time=now,
    )

    assert result.is_success
    bundle: EvidenceBundle = result.value
    assert bundle.investigation_id == inv_id
    assert bundle.tenant_id == sample_tenant
    assert bundle.evidence_count == 1
    assert len(bundle.evidence_items) == 1
    assert len(bundle.bundle_digest) == 64


def test_in_memory_evidence_repository(evidence_module, tenant_context, sample_tenant, now, sample_payload):
    """Verify InMemoryEvidenceRepository persistence and retrieval operations."""
    repo = evidence_module.InMemoryEvidenceRepository()
    record_id = UUIDv7.generate()
    record = evidence_module.EvidenceRecord(
        evidence_id=record_id,
        tenant_id=sample_tenant,
        acl_policy_ref="policy:default",
        source_system=evidence_module.SourceSystemType.DOCUMENT_STORE,
        source_object_ref="docs/sla.pdf",
        source_version="v1",
        content_digest=evidence_module.compute_content_digest(sample_payload),
        classification=evidence_module.ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=evidence_module.SupersessionStatus.ACTIVE,
        extraction_method=evidence_module.ExtractionMethod.DOCUMENT_CHUNK,
        parser_version="1.0",
        retrieval_method=evidence_module.RetrievalMethod.VECTOR_KNN,
        confidence_score=0.9,
        payload=sample_payload,
    )

    # Save and retrieve record
    repo.save_evidence(tenant_context, record)
    retrieved = repo.get_evidence(tenant_context, record_id)
    assert retrieved is not None
    assert retrieved.evidence_id == record_id

    # Package and save bundle
    inv_id = UUIDv7.generate()
    bundle_res = evidence_module.package_evidence_bundle(inv_id, sample_tenant, [record])
    assert bundle_res.is_success
    bundle = bundle_res.value

    repo.save_bundle(tenant_context, bundle)
    retrieved_bundle = repo.get_bundle(tenant_context, bundle.bundle_id)
    assert retrieved_bundle is not None
    assert retrieved_bundle.bundle_id == bundle.bundle_id

    bundles_list = repo.list_bundles_by_investigation(tenant_context, inv_id)
    assert len(bundles_list) == 1
    assert bundles_list[0].bundle_id == bundle.bundle_id
