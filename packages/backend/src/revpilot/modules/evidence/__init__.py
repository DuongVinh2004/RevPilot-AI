"""
RevPilot AI — Governed Evidence and Provenance Module
Specification: docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md
Authoritative public exports for evidence domain models, packaging, and governance.
Conforms to INV-EVD-001, INV-EVD-002, INV-TEN-001..003, AC-004, and AC-005.
"""

from revpilot.modules.evidence.domain.models import (
    SourceSystemType,
    ClassificationLevel,
    SupersessionStatus,
    ExtractionMethod,
    RetrievalMethod,
    CitationSpan,
    EvidenceRecord,
    EvidenceBundle,
    compute_content_digest,
)
from revpilot.modules.evidence.domain.temporal_filter import (
    is_evidence_temporally_valid,
)
from revpilot.modules.evidence.domain.packaging import (
    PackagingError,
    compute_bundle_digest,
    package_evidence_bundle,
)
from revpilot.modules.evidence.ports.repository import (
    EvidenceRepositoryPort,
    InMemoryEvidenceRepository,
)

__all__ = [
    # Domain Enums & Models
    "SourceSystemType",
    "ClassificationLevel",
    "SupersessionStatus",
    "ExtractionMethod",
    "RetrievalMethod",
    "CitationSpan",
    "EvidenceRecord",
    "EvidenceBundle",
    # Functions
    "compute_content_digest",
    "is_evidence_temporally_valid",
    "PackagingError",
    "compute_bundle_digest",
    "package_evidence_bundle",
    # Ports
    "EvidenceRepositoryPort",
    "InMemoryEvidenceRepository",
]
