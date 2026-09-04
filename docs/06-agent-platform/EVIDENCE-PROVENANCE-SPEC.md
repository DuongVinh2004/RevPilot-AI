# Evidence Provenance, ACL, and Citation Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 03 — Governed Evidence and Investigation (Rails 6, 8)
Owner: Evidence Architecture / Data Governance
Traceability: `INV-EVD-001`, `INV-EVD-002`, `INV-TEN-001..003`, `INV-SEC-002`, `INV-DATA-002`, `INV-PRV-001`, `FR-EVD-001`, `FR-EVD-003`, `AC-004`, `AC-005`, `AC-013`, `ADR-0004`, `ADR-0005`

---

## 1. Principles of Governed Evidence

In RevPilot AI, evidence is the sole factual substrate for automated analysis, root cause hypotheses, and decision intelligence. Unsubstantiated model statements are strictly prohibited (`INV-AI-001`).

### 1.1 Non-Negotiable Invariants
1. **Immutable Provenance (`INV-EVD-001`)**: Every evidence object must record its origin system, source object identifier, version, cryptographic content digest, extraction pipeline, and extraction timestamp.
2. **Strict Tenant & ACL Isolation (`INV-TEN-001`, `AC-005`)**: Evidence cannot be shared, cached, or retrieved across tenant boundaries. Evidence access is validated against the principal's permission scope prior to context inclusion.
3. **Temporal Validity and Supersession Filtering (`INV-EVD-002`, `FR-EVD-003`)**: Documents, policies, SLAs, or data clauses that have been superseded, revoked, or are outside the effective date range at `:as_of_time` cannot be used to support any hypothesis.
4. **Verifiable Citation Spans (`AC-004`, `AC-013`)**: Textual evidence must include exact, machine-verifiable citation offsets (`start_char`, `end_char`, `chunk_id`). Synthetic or inexact citations are rejected by the Verifier.
5. **No Secret or Raw PII Ingestion (`INV-PRV-001`)**: Evidence objects undergo automated masking/redaction before storage and embedding.

---

## 2. Canonical Evidence Data Contract

Every evidence item conforms to the typed `EvidenceRecord` schema:

```python
class SourceSystemType(str, Enum):
    CANONICAL_POSTGRES = "CANONICAL_POSTGRES"
    DOCUMENT_STORE = "DOCUMENT_STORE"
    SUPPORT_DESK = "SUPPORT_DESK"
    WMS_FULFILLMENT = "WMS_FULFILLMENT"
    ERP_FINANCE = "ERP_FINANCE"

class ClassificationLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"

class SupersessionStatus(str, Enum):
    ACTIVE = "ACTIVE"                 # Currently valid and applicable
    SUPERSEDED = "SUPERSEDED"         # Replaced by newer version; invalid for as_of >= superseded_at
    REVOKED = "REVOKED"               # Explicitly invalidated/withdrawn
    EXPIRED = "EXPIRED"               # Expired past its natural validity window

class ExtractionMethod(str, Enum):
    SQL_AGGREGATE = "SQL_AGGREGATE"
    DOCUMENT_CHUNK = "DOCUMENT_CHUNK"
    TICKET_EXTRACT = "TICKET_EXTRACT"
    CAUSAL_ESTIMATE = "CAUSAL_ESTIMATE"

class RetrievalMethod(str, Enum):
    SQL_DIRECT = "SQL_DIRECT"
    LEXICAL_BM25 = "LEXICAL_BM25"
    VECTOR_KNN = "VECTOR_KNN"
    HYBRID_FUSED = "HYBRID_FUSED"

class CitationSpan(BaseModel):
    chunk_id: str
    section_id: Optional[str] = None
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    snippet_text: str

class EvidenceRecord(BaseModel):
    evidence_id: UUIDv7
    tenant_id: TenantId
    acl_policy_ref: str               # E.g. "policy:contracts:finance_view"
    source_system: SourceSystemType
    source_object_ref: str            # E.g. "contracts/2026/SLA_LOGISTICS_ACME_v2.pdf"
    source_version: str               # E.g. "git:sha1", "s3:etag", "row:version"
    content_digest: str               # SHA-256 hex string over normalized content
    classification: ClassificationLevel
    event_time: UtcDateTime           # When real-world event happened
    effective_time: UtcDateTime       # When clause/policy became legally effective
    expiration_time: Optional[UtcDateTime] = None # When clause/policy expired
    as_of_time: UtcDateTime           # Query evaluation perspective
    ingestion_time: UtcDateTime       # When RevPilot ingested and signed evidence
    supersession_status: SupersessionStatus
    superseded_at: Optional[UtcDateTime] = None # Required when status is SUPERSEDED
    superseded_by_ref: Optional[str] = None
    lineage_parent_ids: List[UUIDv7] = Field(default_factory=list)
    extraction_method: ExtractionMethod
    parser_version: str
    retrieval_method: RetrievalMethod
    citation_span: Optional[CitationSpan] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    redaction_state: Literal["NONE", "PII_MASKED", "SECRET_REDACTED"]
    retention_class: Literal["OPERATIONAL_30D", "COMPLIANCE_7Y", "INVESTIGATION_BOUND"]
    authorization_decision: Literal["PERMITTED", "DENIED_ACL", "DENIED_SUPERSEDED", "DENIED_TENANT"]
    payload: Dict[str, Any]           # Structured data or text excerpt
```

### 2.1. Supersession and Temporal Validity Fields (`INV-EVD-002`, `FR-EVD-003`)
- **Explicit Schema Declaration**: `EvidenceRecord` explicitly declares both temporal and relational supersession attributes:
  - `superseded_at: Optional[UtcDateTime] = None`: Canonical timestamp indicating exactly when the clause/document became superseded. Mandatory whenever `supersession_status == SupersessionStatus.SUPERSEDED`.
  - `superseded_by_ref: Optional[str] = None`: Opaque identifier pointing to successor document version or replacing evidence ID.
- **Deterministic Temporal Evaluation**: The temporal filter predicate `IS_VALID(evidence, as_of_time)` (§4) uses `evidence.superseded_at` to resolve historical point-in-time applicability without relying on undeclared or external fields.

---

## 3. Evidence Packaging and Bundle Validation

Evidence items are assembled into a sealed `EvidenceBundle`:

```python
class EvidenceBundle(BaseModel):
    bundle_id: UUIDv7
    investigation_id: UUIDv7
    tenant_id: TenantId
    evidence_count: int
    evidence_items: List[EvidenceRecord]
    bundle_digest: str                # SHA256 of sorted evidence content digests
    sealed_at: UtcDateTime
```

### Bundle Invariants:
1. **Single Tenant Guarantee**: All `evidence_items` must have `tenant_id == bundle.tenant_id`.
2. **Digest Integrity**: `bundle_digest` is calculated deterministically:
   ```text
   bundle_digest = SHA256(join(";", sort([e.content_digest for e in evidence_items])))
   ```
3. **No Mixed Supersession**: If `supersession_status != 'ACTIVE'` at `as_of_time`, the item cannot be included in a bundle marked for hypothesis synthesis.

---

## 4. Effective-Date and Supersession Verification

When evaluating an evidence clause against an investigation with `:as_of_time`:
```text
IS_VALID(evidence, as_of_time) = 
    (evidence.effective_time <= as_of_time) AND
    (evidence.expiration_time IS NULL OR evidence.expiration_time > as_of_time) AND
    (evidence.supersession_status == 'ACTIVE' OR 
        (evidence.supersession_status == 'SUPERSEDED' AND evidence.superseded_at > as_of_time))
```
- If an older SLA contract was active on the date of the incident (`2026-05-15`), it MUST be used, even if a newer version was uploaded later (`2026-07-01`).
- If an SLA was amended *before* the incident, the superseded clause is rejected with `DENIED_SUPERSEDED` (`FR-EVD-003`).

---

## 5. Failure and Threat Mitigation Matrix

| Threat / Flaw | Detection Layer | System Action | Audit Event |
|---|---|---|---|
| Ingestion of cross-tenant document | Ingestion Interceptor | Reject document; fail closed | `security.evidence.cross_tenant_rejected` |
| Evidence without SHA-256 digest | Schema Validator | Quarantine record; return `ERR_MISSING_DIGEST` | `data.evidence.malformed` |
| Using superseded contract clause | Verifier Engine | Reject citation; flag `DENIED_SUPERSEDED` | `rag.evidence.superseded_rejected` |
| Inexact or fabricated citation span | Deterministic Verifier | Invalidate claim; mark `UNSUPPORTED_CLAIM` | `ai.citation.mismatch_rejected` |
| PII or secret in evidence payload | Ingestion DLP Scanner | Mask PII; redact secret; quarantine unmaskable | `security.dlp.pii_masked` |
| Tampered evidence content | Bundle Validator | Hash mismatch throws `ERR_EVIDENCE_TAMPERED` | `security.evidence.tamper_detected` |

---

## 6. Test Suite and Verification Mapping

- `tests/contract/test_evidence_record_schema.py`: Verifies Pydantic validation, mandatory field checks, and enum enforcement.
- `tests/security/test_evidence_tenant_isolation.py`: Verifies that querying tenant A cannot retrieve tenant B evidence records (`INV-TEN-001`).
- `tests/analytics/test_evidence_effective_date.py`: Tests boundary conditions on effective dates, expirations, and historical point-in-time replays (`FR-EVD-003`).
- `tests/ai-evals/test_evidence_citation_verifier.py`: Injects accurate and distorted citation spans; verifies exact offset validation and rejection of hallucinations (`AC-004`).
