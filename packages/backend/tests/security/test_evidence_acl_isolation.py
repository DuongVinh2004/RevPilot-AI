"""
RevPilot AI — Security, Multi-Tenant ACL, and Supersession Isolation Tests for Evidence
Specification: docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md §4, §5
Verifies AC-P03-004-02: 100% rejection of cross-tenant mixing, superseded clauses, and future data.
Enforces INV-TEN-001, INV-EVD-001, INV-EVD-002, and FR-EVD-003.
"""

from __future__ import annotations
import sys
import pytest
from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import TenancyViolationError


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
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha")


@pytest.fixture
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta")


@pytest.fixture
def context_alpha(tenant_alpha) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_alpha,
        organization_id=OrganizationId("org_alpha"),
        tier="enterprise",
    )


@pytest.fixture
def context_beta(tenant_beta) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_beta,
        organization_id=OrganizationId("org_beta"),
        tier="growth",
    )


@pytest.fixture
def incident_as_of() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-05-15T00:00:00.000000Z")


def create_sample_record(
    evidence_module,
    tenant_id: TenantId,
    effective_time: UtcDateTime,
    supersession_status: Any = None,
    superseded_at: UtcDateTime | None = None,
    expiration_time: UtcDateTime | None = None,
    payload_override: dict | None = None,
    digest_override: str | None = None,
):
    status = supersession_status or evidence_module.SupersessionStatus.ACTIVE
    payload = payload_override or {"clause": "SLA_99_9", "penalty_cents": 5000}
    digest = digest_override or evidence_module.compute_content_digest(payload)
    return evidence_module.EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        acl_policy_ref="policy:contract:sla",
        source_system=evidence_module.SourceSystemType.DOCUMENT_STORE,
        source_object_ref="contracts/sla_v1.pdf",
        source_version="v1",
        content_digest=digest,
        classification=evidence_module.ClassificationLevel.CONFIDENTIAL,
        event_time=effective_time,
        effective_time=effective_time,
        expiration_time=expiration_time,
        as_of_time=effective_time,
        ingestion_time=effective_time,
        supersession_status=status,
        superseded_at=superseded_at,
        extraction_method=evidence_module.ExtractionMethod.DOCUMENT_CHUNK,
        parser_version="1.0",
        retrieval_method=evidence_module.RetrievalMethod.VECTOR_KNN,
        confidence_score=0.99,
        payload=payload,
    )


# =============================================================================
# AC-P03-004-02: Tenancy & Temporal Isolation Tests
# =============================================================================

def test_cross_tenant_bundle_packaging_rejected(evidence_module, tenant_alpha, tenant_beta, incident_as_of):
    """
    Verify bundling evidence records from distinct tenants fails closed (INV-TEN-001).
    """
    rec_alpha = create_sample_record(evidence_module, tenant_alpha, incident_as_of)
    rec_beta = create_sample_record(evidence_module, tenant_beta, incident_as_of)

    # Attempt to bundle Tenant Alpha and Tenant Beta records together
    res = evidence_module.package_evidence_bundle(
        investigation_id=UUIDv7.generate(),
        tenant_id=tenant_alpha,
        records=[rec_alpha, rec_beta],
        as_of_time=incident_as_of,
    )

    assert res.is_failure
    assert res.error.code == "ERR_CROSS_TENANT_EVIDENCE"
    assert res.error.http_status == 403


def test_superseded_clause_before_as_of_time_rejected(evidence_module, tenant_alpha, incident_as_of):
    """
    A contract clause superseded BEFORE incident as_of_time must be rejected (INV-EVD-002, FR-EVD-003).
    """
    effective_t = UtcDateTime.from_iso("2026-01-01T00:00:00.000000Z")
    superseded_t = UtcDateTime.from_iso("2026-04-01T00:00:00.000000Z")  # Prior to 2026-05-15

    rec = create_sample_record(
        evidence_module,
        tenant_id=tenant_alpha,
        effective_time=effective_t,
        supersession_status=evidence_module.SupersessionStatus.SUPERSEDED,
        superseded_at=superseded_t,
    )

    # Direct temporal check
    assert evidence_module.is_evidence_temporally_valid(rec, incident_as_of) is False

    # Bundling check
    res = evidence_module.package_evidence_bundle(
        investigation_id=UUIDv7.generate(),
        tenant_id=tenant_alpha,
        records=[rec],
        as_of_time=incident_as_of,
    )
    assert res.is_failure
    assert res.error.code == "ERR_EVIDENCE_SUPERSEDED"
    assert res.error.http_status == 400


def test_superseded_clause_after_as_of_time_accepted(evidence_module, tenant_alpha, incident_as_of):
    """
    A clause superseded AFTER incident as_of_time was legitimately active during the incident (FR-EVD-003).
    """
    effective_t = UtcDateTime.from_iso("2026-01-01T00:00:00.000000Z")
    superseded_t = UtcDateTime.from_iso("2026-07-01T00:00:00.000000Z")  # After 2026-05-15

    rec = create_sample_record(
        evidence_module,
        tenant_id=tenant_alpha,
        effective_time=effective_t,
        supersession_status=evidence_module.SupersessionStatus.SUPERSEDED,
        superseded_at=superseded_t,
    )

    # Was active on 2026-05-15
    assert evidence_module.is_evidence_temporally_valid(rec, incident_as_of) is True

    res = evidence_module.package_evidence_bundle(
        investigation_id=UUIDv7.generate(),
        tenant_id=tenant_alpha,
        records=[rec],
        as_of_time=incident_as_of,
    )
    assert res.is_success
    assert res.value.evidence_count == 1


def test_future_dated_evidence_rejected(evidence_module, tenant_alpha, incident_as_of):
    """
    Evidence with effective_time in future relative to incident as_of_time must be rejected (INV-DATA-001).
    """
    future_t = UtcDateTime.from_iso("2026-06-01T00:00:00.000000Z")  # After 2026-05-15
    rec = create_sample_record(evidence_module, tenant_id=tenant_alpha, effective_time=future_t)

    assert evidence_module.is_evidence_temporally_valid(rec, incident_as_of) is False

    res = evidence_module.package_evidence_bundle(
        investigation_id=UUIDv7.generate(),
        tenant_id=tenant_alpha,
        records=[rec],
        as_of_time=incident_as_of,
    )
    assert res.is_failure
    assert res.error.code == "ERR_EVIDENCE_SUPERSEDED"


def test_expired_clause_rejected(evidence_module, tenant_alpha, incident_as_of):
    """
    Evidence with expiration_time <= as_of_time must be rejected.
    """
    effective_t = UtcDateTime.from_iso("2026-01-01T00:00:00.000000Z")
    expiration_t = UtcDateTime.from_iso("2026-05-01T00:00:00.000000Z")  # Expired before 2026-05-15

    rec = create_sample_record(
        evidence_module,
        tenant_id=tenant_alpha,
        effective_time=effective_t,
        expiration_time=expiration_t,
    )

    assert evidence_module.is_evidence_temporally_valid(rec, incident_as_of) is False


def test_revoked_clause_rejected(evidence_module, tenant_alpha, incident_as_of):
    """
    Evidence with status REVOKED must be rejected.
    """
    effective_t = UtcDateTime.from_iso("2026-01-01T00:00:00.000000Z")
    rec = create_sample_record(
        evidence_module,
        tenant_id=tenant_alpha,
        effective_time=effective_t,
        supersession_status=evidence_module.SupersessionStatus.REVOKED,
    )

    assert evidence_module.is_evidence_temporally_valid(rec, incident_as_of) is False


def test_content_digest_tamper_detected(evidence_module, tenant_alpha, incident_as_of):
    """
    If payload content is altered without recalculating content_digest, packaging fails (INV-EVD-001).
    """
    rec = create_sample_record(
        evidence_module,
        tenant_id=tenant_alpha,
        effective_time=incident_as_of,
        digest_override="0000000000000000000000000000000000000000000000000000000000000000",
    )

    res = evidence_module.package_evidence_bundle(
        investigation_id=UUIDv7.generate(),
        tenant_id=tenant_alpha,
        records=[rec],
        as_of_time=incident_as_of,
        verify_digests=True,
    )

    assert res.is_failure
    assert res.error.code == "ERR_DIGEST_MISMATCH"
    assert res.error.http_status == 500


def test_repository_cross_tenant_isolation(evidence_module, context_alpha, context_beta, tenant_beta, incident_as_of):
    """
    Tenant Alpha cannot save or retrieve records / bundles belonging to Tenant Beta (INV-TEN-001).
    """
    repo = evidence_module.InMemoryEvidenceRepository()
    rec_beta = create_sample_record(evidence_module, tenant_beta, incident_as_of)

    # 1. Tenant Alpha cannot save Beta's record
    with pytest.raises(TenancyViolationError):
        repo.save_evidence(context_alpha, rec_beta)

    # 2. Beta saves its own record
    repo.save_evidence(context_beta, rec_beta)

    # 3. Alpha tries to retrieve Beta's record by ID -> returns None
    assert repo.get_evidence(context_alpha, rec_beta.evidence_id) is None

    # 4. Beta can retrieve its own record
    assert repo.get_evidence(context_beta, rec_beta.evidence_id) is not None
