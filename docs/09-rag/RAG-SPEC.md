# Governed Hybrid RAG and Retrieval Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 03 — Governed Evidence and Investigation (Rails 8, 9)
Owner: AI Platform Architecture / Retrieval Architecture
Traceability: `FR-EVD-001..003`, `INV-EVD-001..002`, `INV-SEC-002..003`, `INV-TEN-001..002`, `INV-PRV-001`, `NFR-AI-003`, `NFR-PRV-001`, `AC-005`, `AC-013`, `ADR-0004`, `ADR-0005`, `ADR-0006`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Principles and System Boundaries

RevPilot's Retrieval-Augmented Generation (RAG) system grounds LLM reasoning in verified, authoritative enterprise documents, contracts, maintenance logs, and support tickets. Retrieval is not an unconstrained search engine; it is a policy-enforced evidence pipeline.

### 1.1 Non-Negotiable Rules
1. **No Evidence Without Provenance (`INV-EVD-001`)**: Every retrieved chunk must link to an immutable document version, source system URI, and content digest.
2. **Supersession and Effective-Date Rejection (`INV-EVD-002`, `FR-EVD-003`)**: Documents or contract clauses that are superseded or non-effective at `:as_of_time` are physically filtered out and cannot support any hypothesis.
3. **Untrusted Document Content Neutralization (`INV-SEC-002`, `SEC-004`)**: Document text is strictly untrusted data. It cannot grant authority, override system prompts, or trigger tools.
4. **No Model Filter Overrides**: Retrieval filters (`tenant_id`, `acl_tags`, `as_of_time`) are generated deterministically server-side. The model cannot alter or widen retrieval filters.
5. **No Hallucinated Fill-in**: If retrieval returns 0 authorized documents, the system returns `NO_AUTHORIZED_EVIDENCE`, which translates to `NEED_MORE_EVIDENCE`—never an ungrounded synthetic response.

---

## 2. The 12-Step Governed Retrieval Pipeline

```text
 [1. Source Authorization]
            │
            ▼
 [2. Tenant & ACL Filtering]
            │
            ▼
 [3. Classification Filtering]
            │
            ▼
 [4. Effective-Date Filtering]
            │
      ┌─────┴────────────────┐
      ▼                      ▼
 [5. Lexical Search]    [6. Vector Search]
      (PostgreSQL FTS)       (pgvector HNSW)
      └─────┬────────────────┘
            ▼
 [7. Merge & Deduplication (RRF)]
            │
            ▼
 [8. Deterministic Reranking]
            │
            ▼
 [9. Citation Span Extraction]
            │
            ▼
 [10. Citation Verification]
            │
            ▼
 [11. Evidence Packaging]
            │
            ▼
 [12. Post-Retrieval Auth Gate]
```

### 2.1 Step Details
1. **Source Authorization**: Validates that the requesting `PrincipalContext` has active permissions for the requested source systems (e.g. `documents:read`, `contracts:view`).
2. **Tenant & ACL Filtering**: Server injects `tenant_id` and the user's ACL roles into the query predicate. Cross-tenant retrieval is blocked at SQL/index level.
3. **Classification Filtering**: Documents classified higher than the investigation's permitted sensitivity tier (e.g. `RESTRICTED` vs `INTERNAL`) are excluded.
4. **Effective-Date Filtering**: Enforces `effective_from <= :as_of_time AND (effective_to IS NULL OR effective_to > :as_of_time)`. Superseded chunks are discarded.
5. **Lexical Retrieval**: PostgreSQL Full Text Search using `tsvector` and `websearch_to_tsquery('english', :query)` with GIN index.
6. **Vector Retrieval**: PostgreSQL `pgvector` HNSW index using cosine similarity (`vector_cosine_ops`) over 1536-dim or 768-dim embeddings (`ADR-0006`).
7. **Merge & Deduplication**: Reciprocal Rank Fusion (RRF) combines lexical and dense ranks:
   $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{lexical}, \text{dense}\}} \frac{1}{60 + \text{rank}_m(d)}$$
8. **Deterministic Reranking**: Scores candidates by weighted combination of RRF score, document freshness, and authority tier (e.g., signed contracts outweigh tickets).
9. **Citation Span Extraction**: Extracts byte and character offsets (`start_char`, `end_char`) for relevant snippet clauses within chunks.
10. **Citation Verification**: Verifies extracted snippet matches exact source text hash; detects and rejects corrupted or hallucinated spans.
11. **Evidence Packaging**: Converts top-K validated chunks into sealed `EvidenceRecord` instances with individual SHA-256 digests.
12. **Post-Retrieval Authorization Check**: Final sanity check ensures no quarantined, revoked, or leaked items exist in the final bundle before LLM prompt injection.

---

## 3. Schemas and Query Contracts

### 3.1 Retrieval Query Schema
```python
class RetrievalFilter(BaseModel):
    source_systems: Optional[List[SourceSystemType]] = None
    document_types: Optional[List[str]] = None # E.g. ["CONTRACT", "SLA", "MAINTENANCE_LOG"]
    classification_max: ClassificationLevel = ClassificationLevel.CONFIDENTIAL
    as_of_time: UtcDateTime
    effective_at: UtcDateTime

class RetrievalQuery(BaseModel):
    query_text: str
    tenant_context: TenantContext
    principal_context: PrincipalContext
    filters: RetrievalFilter
    top_k: int = Field(default=5, le=20)
    score_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
```

### 3.2 Retrieval Result and Evidence Chunk
```python
class ChunkMetadata(BaseModel):
    document_id: UUIDv7
    version_id: str
    chunk_index: int
    source_uri: str
    title: str
    section: Optional[str] = None
    effective_from: UtcDateTime
    effective_to: Optional[UtcDateTime] = None
    superseded_at: Optional[UtcDateTime] = None
    digest: str

class RetrievedEvidenceChunk(BaseModel):
    chunk_id: str
    metadata: ChunkMetadata
    text: str
    lexical_rank: Optional[int] = None
    dense_rank: Optional[int] = None
    fused_score: float
    citation_span: CitationSpan
```

---

## 4. Prompt Injection and Malicious Document Handling

Under `INV-SEC-002` and `SEC-004`:
1. **Document Isolation Framing**: All retrieved document excerpts injected into LLM prompts are framed with strict untrusted data delimiters:
   ```text
   <untrusted_document source="SLA_Contract_2026.pdf" id="doc_123">
   ... retrieved text ...
   </untrusted_document>
   ```
2. **Prompt Injection Classifier**: During ingestion and pre-context packaging, chunk text is scanned for adversarial prompt injection phrases (e.g. `"Ignore previous instructions"`, `"System Prompt Override"`, `"Return all credentials"`).
3. **Quarantine Action**: Chunks scoring above the injection detection threshold are quarantined, excluded from retrieval, and logged as `security.rag.injection_quarantined`.

---

## 5. Performance, Degradation, and Evaluation Targets

Under `NFR-AI-003`:
- **Recall@10**: $\ge 0.90$ on benchmark evaluation suite.
- **MRR (Mean Reciprocal Rank)**: $\ge 0.85$.
- **Citation Precision**: $\ge 0.95$ (at least 95% of cited spans are exact factual matches).
- **Unauthorized Evidence Rate**: Exactly $0.00\%$ (zero tolerance for cross-tenant or unpermitted retrieval).
- **Superseded Document Rejection**: $100\%$ of superseded clauses correctly excluded.

### Degradation Policy
- If the vector index is unavailable, the pipeline falls back to lexical-only search and flags `DEGRADED_LEXICAL_ONLY`.
- If an index partition is rebuilding, results include `PARTIAL_INDEX_WARNING`.
- If 0 results meet `score_threshold`, the activity returns `NO_AUTHORIZED_EVIDENCE`.

---

## 6. Verification and Test Suite Mapping

- `tests/security/test_rag_tenant_isolation.py`: Negative tests verifying Tenant A queries never match Tenant B chunks under any search mode (`INV-TEN-001`).
- `tests/security/test_rag_acl_enforcement.py`: Tests that users lacking confidential permissions cannot retrieve restricted chunks (`INV-IAM-001`).
- `tests/ai-evals/test_rag_effective_date_filter.py`: Evaluates that pre-incident and post-incident document versions are correctly partitioned by `:as_of_time` (`INV-EVD-002`).
- `tests/ai-evals/test_rag_citation_precision.py`: Benchmark suite evaluating Recall@10, MRR, and citation precision against known synthetic corpus (`NFR-AI-003`).
- `tests/security/test_rag_prompt_injection_defense.py`: Injects adversarial jailbreak documents and verifies they do not hijack agent instructions (`INV-SEC-002`).
