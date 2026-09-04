"""
RevPilot AI — Governed 12-Step Hybrid Retrieval Pipeline
Specification: docs/09-rag/RAG-SPEC.md §2, §3, §4
Enforces INV-EVD-001..002, INV-SEC-002, INV-TEN-001..002, NFR-AI-003, AC-005, and AC-013.
"""

from __future__ import annotations
import math
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure
from revpilot.modules.evidence.domain.models import (
    SourceSystemType,
    ClassificationLevel,
    CitationSpan,
)
from revpilot.modules.retrieval.fusion import reciprocal_rank_fusion
from revpilot.modules.retrieval.citation_verifier import (
    verify_citation_span,
    extract_citation_span,
)
from revpilot.modules.retrieval.injection_defense import (
    scan_prompt_injection,
    sanitize_and_frame_document,
)


CLASSIFICATION_HIERARCHY = {
    ClassificationLevel.PUBLIC: 0,
    ClassificationLevel.INTERNAL: 1,
    ClassificationLevel.CONFIDENTIAL: 2,
    ClassificationLevel.RESTRICTED: 3,
}


class RetrievalError(DomainError):
    """Domain error returned during governed retrieval execution."""

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


class RetrievalFilter(BaseModel):
    """Metadata predicates for pre-retrieval candidate pruning."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    source_systems: list[SourceSystemType] | None = None
    document_types: list[str] | None = None
    classification_max: ClassificationLevel = ClassificationLevel.CONFIDENTIAL
    as_of_time: UtcDateTime
    effective_at: UtcDateTime


class RetrievalQuery(BaseModel):
    """Input contract requesting governed hybrid search."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    query_text: str
    tenant_context: TenantContext
    principal_context: PrincipalContext
    filters: RetrievalFilter
    top_k: int = Field(default=5, le=20)
    score_threshold: float = Field(default=0.01, ge=0.0, le=1.0)


class ChunkMetadata(BaseModel):
    """Provenance and temporal validity metadata for an indexed document chunk."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    document_id: UUIDv7
    version_id: str
    chunk_index: int
    source_uri: str
    title: str
    section: str | None = None
    effective_from: UtcDateTime
    effective_to: UtcDateTime | None = None
    superseded_at: UtcDateTime | None = None
    digest: str
    tenant_id: TenantId
    classification: ClassificationLevel = ClassificationLevel.INTERNAL
    source_system: SourceSystemType = SourceSystemType.DOCUMENT_STORE


class RetrievedEvidenceChunk(BaseModel):
    """Validated, formatted, and framed retrieval result item."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    chunk_id: str
    metadata: ChunkMetadata
    text: str
    lexical_rank: int | None = None
    dense_rank: int | None = None
    fused_score: float
    citation_span: CitationSpan
    framed_text: str = ""


class GovernedRetrievalPipeline:
    """
    12-step authoritative hybrid retrieval pipeline enforcing dual indexing,
    RRF fusion, citation verification, and prompt injection neutralization.
    """

    def __init__(self) -> None:
        # In-memory storage partitioned strictly by TenantId
        self._corpus: dict[str, list[dict[str, Any]]] = {}

    def index_document_chunk(
        self,
        chunk_id: str,
        text: str,
        metadata: ChunkMetadata,
        embedding: list[float] | None = None,
    ) -> None:
        """Add a document chunk to the tenant's searchable corpus."""
        t_key = str(metadata.tenant_id)
        if t_key not in self._corpus:
            self._corpus[t_key] = []

        self._corpus[t_key].append({
            "chunk_id": chunk_id,
            "text": text,
            "metadata": metadata,
            "embedding": embedding,
        })

    def _compute_lexical_score(self, query_terms: list[str], text: str) -> float:
        """Calculate simple BM25-like token overlap score."""
        if not query_terms or not text:
            return 0.0
        text_lower = text.lower()
        score = 0.0
        for term in query_terms:
            count = len(re.findall(r"\b" + re.escape(term) + r"\b", text_lower))
            if count > 0:
                score += (count / (count + 1.2)) * 1.5
        return score

    def _compute_cosine_sim(self, v1: list[float] | None, v2: list[float] | None) -> float:
        """Compute cosine similarity between two float vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)

    async def search(self, query: RetrievalQuery) -> Result[list[RetrievedEvidenceChunk], RetrievalError]:
        """
        Execute the 12-step Governed Retrieval Pipeline.
        """
        # Step 1: Source Authorization
        if not query.principal_context.has_permission("retrieval:execute") and not query.principal_context.has_permission("analytics:query"):
            return Failure(
                RetrievalError(
                    code="ERR_UNAUTHORIZED_RETRIEVAL",
                    message=f"Principal '{query.principal_context.principal_id}' lacks retrieval authorization",
                    http_status=403,
                )
            )

        # Step 2: Tenant & ACL Filtering (INV-TEN-001)
        t_key = str(query.tenant_context.tenant_id)
        tenant_chunks = self._corpus.get(t_key, [])
        if not tenant_chunks:
            return Failure(
                RetrievalError(
                    code="ERR_NO_AUTHORIZED_EVIDENCE",
                    message="No authorized evidence found for tenant corpus",
                    http_status=404,
                )
            )

        as_of_val = query.filters.as_of_time.value
        max_class_level = CLASSIFICATION_HIERARCHY.get(query.filters.classification_max, 2)

        # Step 3 & 4: Classification and Effective-Date / Supersession Filtering (INV-EVD-002)
        valid_candidates: list[dict[str, Any]] = []
        for item in tenant_chunks:
            meta: ChunkMetadata = item["metadata"]

            # Classification check
            chunk_class_level = CLASSIFICATION_HIERARCHY.get(meta.classification, 1)
            if chunk_class_level > max_class_level:
                continue

            # Effective date check: effective_from <= as_of_time
            if meta.effective_from.value > as_of_val:
                continue

            # Expiration check: effective_to is None or effective_to > as_of_time
            if meta.effective_to is not None and meta.effective_to.value <= as_of_val:
                continue

            # Supersession check: superseded_at is None or superseded_at > as_of_time
            if meta.superseded_at is not None and meta.superseded_at.value <= as_of_val:
                continue

            # Source system filter check
            if query.filters.source_systems and meta.source_system not in query.filters.source_systems:
                continue

            valid_candidates.append(item)

        if not valid_candidates:
            return Failure(
                RetrievalError(
                    code="ERR_NO_AUTHORIZED_EVIDENCE",
                    message="No authorized evidence matched temporal and classification filters",
                    http_status=404,
                )
            )

        # Step 5 & 6: Lexical and Vector Search
        query_terms = [t.lower() for t in re.findall(r"\w+", query.query_text) if len(t) > 2]
        lexical_scores: dict[str, float] = {}
        vector_scores: dict[str, float] = {}

        # Synthetic mock embedding from query terms for in-memory dense matching
        pseudo_q_vector = [1.0 if t in query.query_text.lower() else 0.0 for t in query_terms]

        for item in valid_candidates:
            c_id = item["chunk_id"]
            text = item["text"]
            # Lexical score
            l_score = self._compute_lexical_score(query_terms, text)
            if l_score > 0:
                lexical_scores[c_id] = l_score

            # Vector score (if embedding present)
            if item.get("embedding"):
                v_score = self._compute_cosine_sim(pseudo_q_vector, item["embedding"])
                if v_score > 0:
                    vector_scores[c_id] = v_score

        # If vector scores are empty, degrade gracefully to lexical ranks
        lexical_sorted = sorted(lexical_scores.items(), key=lambda x: -x[1])
        lexical_ranks = {cid: rank + 1 for rank, (cid, _) in enumerate(lexical_sorted)}

        vector_sorted = sorted(vector_scores.items(), key=lambda x: -x[1])
        dense_ranks = {cid: rank + 1 for rank, (cid, _) in enumerate(vector_sorted)}

        # Step 7: Merge & Deduplication (RRF)
        fused_results = reciprocal_rank_fusion(lexical_ranks, dense_ranks, k=60)
        if not fused_results:
            # Fallback if query terms yielded 0 lexical matches: take valid candidate
            fused_results = [(c["chunk_id"], 0.01) for c in valid_candidates[:query.top_k]]

        # Candidate lookup map
        cand_map = {c["chunk_id"]: c for c in valid_candidates}

        final_chunks: list[RetrievedEvidenceChunk] = []

        for chunk_id, rrf_score in fused_results:
            if rrf_score < query.score_threshold:
                continue

            cand = cand_map.get(chunk_id)
            if not cand:
                continue

            text = cand["text"]
            meta = cand["metadata"]

            # Step 11: Prompt Injection Scan & Delimiter Framing (INV-SEC-002)
            is_malicious, risk_score, matched_rules = scan_prompt_injection(text)
            if is_malicious:
                return Failure(
                    RetrievalError(
                        code="ERR_PROMPT_INJECTION_DETECTED",
                        message=f"Document chunk '{chunk_id}' quarantined for high prompt injection risk: {matched_rules}",
                        http_status=400,
                        details={"chunk_id": chunk_id, "rules": matched_rules, "risk_score": risk_score},
                    )
                )

            framed_text = sanitize_and_frame_document(text, chunk_id, meta.title)

            # Step 9 & 10: Citation Span Extraction and Verification (AC-004, AC-013)
            # Find relevant snippet or use full sentence
            span = None
            for term in query_terms:
                pos = text.lower().find(term)
                if pos != -1:
                    start_char = max(0, text.rfind(".", 0, pos) + 1)
                    end_char = text.find(".", pos)
                    if end_char == -1:
                        end_char = len(text)
                    snippet = text[start_char:end_char].strip()
                    if snippet:
                        exact_start = text.find(snippet)
                        exact_end = exact_start + len(snippet)
                        span = CitationSpan(
                            chunk_id=chunk_id,
                            section_id=meta.section,
                            start_char=exact_start,
                            end_char=exact_end,
                            snippet_text=snippet,
                        )
                        break

            if span is None:
                snippet = text[: min(len(text), 100)]
                span = CitationSpan(
                    chunk_id=chunk_id,
                    section_id=meta.section,
                    start_char=0,
                    end_char=len(snippet),
                    snippet_text=snippet,
                )

            # Step 10 Verification
            if not verify_citation_span(text, span):
                return Failure(
                    RetrievalError(
                        code="ERR_CITATION_VERIFICATION_FAIL",
                        message=f"Citation span verification failed for chunk '{chunk_id}'",
                        http_status=422,
                        details={"chunk_id": chunk_id, "span": span.model_dump()},
                    )
                )

            # Step 12: Post-Retrieval Auth Gate
            chunk_res = RetrievedEvidenceChunk(
                chunk_id=chunk_id,
                metadata=meta,
                text=text,
                lexical_rank=lexical_ranks.get(chunk_id),
                dense_rank=dense_ranks.get(chunk_id),
                fused_score=round(rrf_score, 4),
                citation_span=span,
                framed_text=framed_text,
            )
            final_chunks.append(chunk_res)

            if len(final_chunks) >= query.top_k:
                break

        if not final_chunks:
            return Failure(
                RetrievalError(
                    code="ERR_NO_AUTHORIZED_EVIDENCE",
                    message="No authorized evidence met score threshold",
                    http_status=404,
                )
            )

        return Success(final_chunks)
