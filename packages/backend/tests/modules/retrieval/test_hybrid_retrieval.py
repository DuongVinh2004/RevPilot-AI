"""
RevPilot AI — Unit and Integration Tests for Governed Hybrid Retrieval
Specification: docs/09-rag/RAG-SPEC.md §2, §3, §5
Verifies AC-P03-005-01: RRF fusion, candidate deduplication, and citation span verification.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7, PrincipalId, OrganizationId
from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_retrieval_modules():
    """Ensure retrieval and evidence modules are clean between test runs and collection."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.retrieval") or mod.startswith("revpilot.modules.evidence"):
            sys.modules.pop(mod, None)


@pytest.fixture
def retrieval_mod():
    import revpilot.modules.retrieval as mod
    return mod


@pytest.fixture
def evidence_mod():
    import revpilot.modules.evidence as mod
    return mod


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha")


@pytest.fixture
def context_alpha(tenant_alpha) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_alpha,
        organization_id=OrganizationId("org_alpha"),
        tier="enterprise",
    )


@pytest.fixture
def principal_analyst(tenant_alpha) -> PrincipalContext:
    return PrincipalContext(
        principal_id=PrincipalId("usr_analyst_01"),
        tenant_id=tenant_alpha,
        roles=frozenset(["analyst"]),
        permissions=frozenset(["retrieval:execute", "analytics:query"]),
    )


@pytest.fixture
def now() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-05-18T12:00:00.000000Z")


# =============================================================================
# AC-P03-005-01: RRF, Citation Span, and 12-Step Pipeline Tests
# =============================================================================

def test_rrf_fusion_formula(retrieval_mod):
    """Verify standard Reciprocal Rank Fusion formula and deterministic ranking (RAG-SPEC.md §2.1 Step 7)."""
    # doc1 is rank 1 in lexical, rank 2 in dense
    # doc2 is rank 2 in lexical, rank 1 in dense
    # doc3 is rank 3 in lexical, absent in dense
    lexical = {"doc1": 1, "doc2": 2, "doc3": 3}
    dense = {"doc1": 2, "doc2": 1}

    # k = 60
    # score(doc1) = 1/(60+1) + 1/(60+2) = 1/61 + 1/62 = 0.016393 + 0.016129 = 0.032522
    # score(doc2) = 1/(60+2) + 1/(60+1) = 0.032522
    # score(doc3) = 1/(60+3) = 1/63 = 0.015873
    fused = retrieval_mod.reciprocal_rank_fusion(lexical, dense, k=60)
    assert len(fused) == 3

    docs = [d for d, _ in fused]
    # doc1 and doc2 tie on score, tie-break alphabetically: doc1 before doc2
    assert docs[0] == "doc1"
    assert docs[1] == "doc2"
    assert docs[2] == "doc3"
    assert fused[0][1] == pytest.approx(1/61 + 1/62, rel=1e-5)
    assert fused[2][1] == pytest.approx(1/63, rel=1e-5)


def test_rrf_invalid_arguments(retrieval_mod):
    """Verify validation on RRF parameters."""
    with pytest.raises(ValueError):
        retrieval_mod.reciprocal_rank_fusion({"doc1": 1}, {}, k=0)

    with pytest.raises(ValueError):
        retrieval_mod.reciprocal_rank_fusion({"doc1": 0}, {}, k=60)


def test_citation_span_exact_verification(retrieval_mod, evidence_mod):
    """
    Verify citation span verification deterministically validates exact match
    and rejects corrupted or fabricated spans (AC-004, INV-AI-001).
    """
    source_text = "Standard delivery window is 2 to 4 business days for continental US shipments."

    # 1. Exact valid span: "2 to 4 business days" (start=28, end=48)
    snippet = "2 to 4 business days"
    start_char = source_text.find(snippet)
    end_char = start_char + len(snippet)

    span = evidence_mod.CitationSpan(
        chunk_id="chk_01",
        start_char=start_char,
        end_char=end_char,
        snippet_text=snippet,
    )
    assert retrieval_mod.verify_citation_span(source_text, span) is True

    # 2. Fabricated / inexact span (offset points to different text)
    bad_span = evidence_mod.CitationSpan(
        chunk_id="chk_01",
        start_char=start_char,
        end_char=end_char,
        snippet_text="same-day delivery guaranteed",
    )
    assert retrieval_mod.verify_citation_span(source_text, bad_span) is False

    # 3. Corrupted bounds
    bad_bounds_span = evidence_mod.CitationSpan(
        chunk_id="chk_01",
        start_char=10,
        end_char=999,
        snippet_text="out of bounds",
    )
    assert retrieval_mod.verify_citation_span(source_text, bad_bounds_span) is False


def test_extract_citation_span(retrieval_mod):
    """Verify helper extracts exact valid CitationSpan from text."""
    text = "Section 4.1: Late shipment rebate is 5 percent per hour."
    span = retrieval_mod.extract_citation_span(text, "chk_02", "5 percent per hour", section_id="4.1")
    assert span is not None
    assert span.chunk_id == "chk_02"
    assert span.section_id == "4.1"
    assert text[span.start_char:span.end_char] == "5 percent per hour"

    # Non-existent snippet
    assert retrieval_mod.extract_citation_span(text, "chk_02", "non-existent") is None


@pytest.mark.asyncio
async def test_12_step_hybrid_pipeline_execution(
    retrieval_mod, evidence_mod, context_alpha, principal_analyst, tenant_alpha, now
):
    """
    Execute 12-step hybrid retrieval pipeline and verify fused scoring, citation validation,
    and document containment framing.
    """
    pipeline = retrieval_mod.GovernedRetrievalPipeline()

    chunk_meta = retrieval_mod.ChunkMetadata(
        document_id=UUIDv7.generate(),
        version_id="v1.0",
        chunk_index=0,
        source_uri="contracts/2026/sla.pdf",
        title="Enterprise Master SLA Agreement",
        section="Section 3: Fulfillment SLAs",
        effective_from=UtcDateTime.from_iso("2026-01-01T00:00:00Z"),
        digest="sha256_mock_digest",
        tenant_id=tenant_alpha,
        classification=evidence_mod.ClassificationLevel.INTERNAL,
    )

    doc_text = "Fulfillment carrier delays exceeding 4 hours incur a mandatory 1000 USD penalty fee."
    pipeline.index_document_chunk(
        chunk_id="chunk_sla_001",
        text=doc_text,
        metadata=chunk_meta,
        embedding=[1.0, 0.0, 0.0],
    )

    query = retrieval_mod.RetrievalQuery(
        query_text="carrier delays penalty fee",
        tenant_context=context_alpha,
        principal_context=principal_analyst,
        filters=retrieval_mod.RetrievalFilter(
            as_of_time=now,
            effective_at=now,
            classification_max=evidence_mod.ClassificationLevel.CONFIDENTIAL,
        ),
        top_k=5,
    )

    res = await pipeline.search(query)
    assert res.is_success
    chunks = res.value
    assert len(chunks) == 1
    chunk = chunks[0]

    assert chunk.chunk_id == "chunk_sla_001"
    assert chunk.fused_score > 0.0
    # Verify citation span is exact
    assert retrieval_mod.verify_citation_span(chunk.text, chunk.citation_span) is True
    # Verify untrusted document framing (§4.1)
    assert "<untrusted_document" in chunk.framed_text
    assert "</untrusted_document>" in chunk.framed_text
