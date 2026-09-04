"""
RevPilot AI — Evidence Domain Submodule
Exports canonical models, temporal filter, and packaging engine.
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

__all__ = [
    "SourceSystemType",
    "ClassificationLevel",
    "SupersessionStatus",
    "ExtractionMethod",
    "RetrievalMethod",
    "CitationSpan",
    "EvidenceRecord",
    "EvidenceBundle",
    "compute_content_digest",
    "is_evidence_temporally_valid",
    "PackagingError",
    "compute_bundle_digest",
    "package_evidence_bundle",
]
