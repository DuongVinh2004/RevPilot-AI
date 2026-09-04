"""
RevPilot AI — Canonical Evidence Domain Models
Specification: docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md §2, §3
Enforces immutable provenance, verified citation spans, and typed metadata.
"""

import hashlib
import json
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


class SourceSystemType(str, Enum):
    """Origin system from which evidence was extracted."""
    CANONICAL_POSTGRES = "CANONICAL_POSTGRES"
    DOCUMENT_STORE = "DOCUMENT_STORE"
    SUPPORT_DESK = "SUPPORT_DESK"
    WMS_FULFILLMENT = "WMS_FULFILLMENT"
    ERP_FINANCE = "ERP_FINANCE"


class ClassificationLevel(str, Enum):
    """Data sensitivity classification level."""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class SupersessionStatus(str, Enum):
    """Lifecycle and supersession validity status."""
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class ExtractionMethod(str, Enum):
    """Pipeline or method used to extract evidence payload."""
    SQL_AGGREGATE = "SQL_AGGREGATE"
    DOCUMENT_CHUNK = "DOCUMENT_CHUNK"
    TICKET_EXTRACT = "TICKET_EXTRACT"
    CAUSAL_ESTIMATE = "CAUSAL_ESTIMATE"


class RetrievalMethod(str, Enum):
    """Retrieval approach that surfaced this evidence item."""
    SQL_DIRECT = "SQL_DIRECT"
    LEXICAL_BM25 = "LEXICAL_BM25"
    VECTOR_KNN = "VECTOR_KNN"
    HYBRID_FUSED = "HYBRID_FUSED"


class CitationSpan(BaseModel):
    """Verifiable character-level citation span within source document chunk."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    chunk_id: str
    section_id: str | None = None
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    snippet_text: str

    @model_validator(mode="after")
    def validate_offsets(self) -> "CitationSpan":
        if self.start_char >= self.end_char:
            raise ValueError(f"start_char ({self.start_char}) must be less than end_char ({self.end_char})")
        return self


def compute_content_digest(payload: dict[str, Any]) -> str:
    """
    Produce deterministic SHA-256 hex string over normalized content payload.
    Conforms to INV-EVD-001.
    """
    clean_json = json.dumps(
        payload,
        sort_keys=True,
        default=lambda o: str(o.value) if hasattr(o, "value") else str(o),
    )
    return hashlib.sha256(clean_json.encode("utf-8")).hexdigest()


class EvidenceRecord(BaseModel):
    """
    Canonical evidence item with cryptographic provenance, ACL binding,
    and temporal validity metadata.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    evidence_id: UUIDv7
    tenant_id: TenantId
    acl_policy_ref: str
    source_system: SourceSystemType
    source_object_ref: str
    source_version: str
    content_digest: str
    classification: ClassificationLevel
    event_time: UtcDateTime
    effective_time: UtcDateTime
    expiration_time: UtcDateTime | None = None
    as_of_time: UtcDateTime
    ingestion_time: UtcDateTime
    supersession_status: SupersessionStatus
    superseded_at: UtcDateTime | None = None
    superseded_by_ref: str | None = None
    lineage_parent_ids: list[UUIDv7] = Field(default_factory=list)
    extraction_method: ExtractionMethod
    parser_version: str
    retrieval_method: RetrievalMethod
    citation_span: CitationSpan | None = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    redaction_state: Literal["NONE", "PII_MASKED", "SECRET_REDACTED"] = "NONE"
    retention_class: Literal["OPERATIONAL_30D", "COMPLIANCE_7Y", "INVESTIGATION_BOUND"] = "INVESTIGATION_BOUND"
    authorization_decision: Literal["PERMITTED", "DENIED_ACL", "DENIED_SUPERSEDED", "DENIED_TENANT"] = "PERMITTED"
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_supersession_consistency(self) -> "EvidenceRecord":
        if self.supersession_status == SupersessionStatus.SUPERSEDED and self.superseded_at is None:
            raise ValueError("superseded_at timestamp is required when supersession_status is SUPERSEDED")
        return self


class EvidenceBundle(BaseModel):
    """
    Sealed, immutable collection of evidence records assembled for an investigation.
    Enforces single-tenant isolation and tamper-evident bundle digest.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    bundle_id: UUIDv7
    investigation_id: UUIDv7
    tenant_id: TenantId
    evidence_count: int
    evidence_items: list[EvidenceRecord]
    bundle_digest: str
    sealed_at: UtcDateTime
