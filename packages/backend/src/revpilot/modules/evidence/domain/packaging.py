"""
RevPilot AI — Evidence Packaging and Bundle Integrity Engine
Specification: docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md §3, §4
Enforces single-tenant bundles, tamper-evident digests, and temporal validity.
"""

import hashlib
from typing import Any
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.results import Result, Success, Failure
from revpilot.shared.errors import DomainError
from revpilot.modules.evidence.domain.models import (
    EvidenceRecord,
    EvidenceBundle,
    compute_content_digest,
)
from revpilot.modules.evidence.domain.temporal_filter import is_evidence_temporally_valid


class PackagingError(DomainError):
    """Domain error representing failure during evidence bundling."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=retryable)
        self.http_status = http_status


def compute_bundle_digest(evidence_items: list[EvidenceRecord]) -> str:
    """
    Produce deterministic SHA-256 digest of evidence bundle conforming to §3.1:
    bundle_digest = SHA256(join(";", sort([e.content_digest for e in evidence_items])))
    """
    sorted_digests = sorted(e.content_digest for e in evidence_items)
    joined_payload = ";".join(sorted_digests).encode("utf-8")
    return hashlib.sha256(joined_payload).hexdigest()


def package_evidence_bundle(
    investigation_id: UUIDv7,
    tenant_id: TenantId,
    records: list[EvidenceRecord],
    as_of_time: UtcDateTime | None = None,
    verify_digests: bool = True,
) -> Result[EvidenceBundle, PackagingError]:
    """
    Assemble and seal an immutable EvidenceBundle for an investigation.
    
    Invariants:
    1. Single Tenant Guarantee (INV-TEN-001): All records must belong strictly to tenant_id.
    2. Content Digest Integrity (INV-EVD-001): Verifies payload hashes against content_digest.
    3. No Superseded Evidence (INV-EVD-002, FR-EVD-003): Excludes or rejects temporally invalid clauses.
    """
    for record in records:
        # 1. Cross-tenant isolation check (INV-TEN-001)
        if record.tenant_id != tenant_id:
            return Failure(
                PackagingError(
                    code="ERR_CROSS_TENANT_EVIDENCE",
                    message=f"Cross-tenant evidence mixing detected: expected tenant '{tenant_id}', record has '{record.tenant_id}'",
                    http_status=403,
                    details={"expected_tenant": str(tenant_id), "record_tenant": str(record.tenant_id)},
                )
            )

        # 2. Cryptographic digest verification (INV-EVD-001)
        if verify_digests:
            computed_hash = compute_content_digest(record.payload)
            if computed_hash != record.content_digest:
                return Failure(
                    PackagingError(
                        code="ERR_DIGEST_MISMATCH",
                        message=f"Evidence content digest mismatch for record {record.evidence_id}: computed {computed_hash} != stored {record.content_digest}",
                        http_status=500,
                        details={"record_id": str(record.evidence_id)},
                    )
                )

        # 3. Temporal validity and supersession check (INV-EVD-002, FR-EVD-003)
        if as_of_time is not None:
            if not is_evidence_temporally_valid(record, as_of_time):
                return Failure(
                    PackagingError(
                        code="ERR_EVIDENCE_SUPERSEDED",
                        message=f"Evidence record {record.evidence_id} is superseded or temporally invalid at {as_of_time}",
                        http_status=400,
                        details={
                            "record_id": str(record.evidence_id),
                            "supersession_status": record.supersession_status.value,
                            "as_of_time": as_of_time.isoformat(),
                        },
                    )
                )

    bundle_digest = compute_bundle_digest(records)
    bundle = EvidenceBundle(
        bundle_id=UUIDv7.generate(),
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        evidence_count=len(records),
        evidence_items=list(records),
        bundle_digest=bundle_digest,
        sealed_at=UtcDateTime.now(),
    )
    return Success(bundle)
