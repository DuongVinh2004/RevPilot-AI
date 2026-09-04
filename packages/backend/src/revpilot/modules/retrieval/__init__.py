"""
RevPilot AI — Governed Hybrid Retrieval and Citation Verification Module
Specification: docs/09-rag/RAG-SPEC.md
Authoritative exports for hybrid search, RRF fusion, and injection defense.
"""

from revpilot.modules.retrieval.fusion import reciprocal_rank_fusion
from revpilot.modules.retrieval.citation_verifier import (
    verify_citation_span,
    extract_citation_span,
)
from revpilot.modules.retrieval.injection_defense import (
    scan_prompt_injection,
    sanitize_and_frame_document,
)
from revpilot.modules.retrieval.pipeline import (
    RetrievalFilter,
    RetrievalQuery,
    ChunkMetadata,
    RetrievedEvidenceChunk,
    RetrievalError,
    GovernedRetrievalPipeline,
)

__all__ = [
    "reciprocal_rank_fusion",
    "verify_citation_span",
    "extract_citation_span",
    "scan_prompt_injection",
    "sanitize_and_frame_document",
    "RetrievalFilter",
    "RetrievalQuery",
    "ChunkMetadata",
    "RetrievedEvidenceChunk",
    "RetrievalError",
    "GovernedRetrievalPipeline",
]
