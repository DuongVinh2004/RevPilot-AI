"""
RevPilot AI — Citation Span Extraction and Verification
Specification: docs/09-rag/RAG-SPEC.md §2.1 (Step 10), §3.2
Enforces AC-004, AC-013, and INV-AI-001 machine-verifiable factual citations.
"""

from __future__ import annotations
from revpilot.modules.evidence.domain.models import CitationSpan


def verify_citation_span(source_text: str, span: CitationSpan) -> bool:
    """
    Verify that citation span offsets exactly match the snippet text within source text.
    
    Formula:
        source_text[span.start_char:span.end_char] == span.snippet_text
        
    Rejects inexact, hallucinated, or out-of-bounds character spans (AC-004).
    """
    if not isinstance(source_text, str) or not isinstance(span, CitationSpan):
        return False

    text_len = len(source_text)
    if span.start_char < 0 or span.end_char > text_len or span.start_char >= span.end_char:
        return False

    actual_slice = source_text[span.start_char:span.end_char]
    return actual_slice == span.snippet_text


def extract_citation_span(
    source_text: str,
    chunk_id: str,
    snippet: str,
    section_id: str | None = None,
) -> CitationSpan | None:
    """
    Locate substring within source text and construct verifiable CitationSpan.
    Returns None if snippet is not found.
    """
    if not snippet or not source_text:
        return None

    start_idx = source_text.find(snippet)
    if start_idx == -1:
        return None

    end_idx = start_idx + len(snippet)
    try:
        return CitationSpan(
            chunk_id=chunk_id,
            section_id=section_id,
            start_char=start_idx,
            end_char=end_idx,
            snippet_text=snippet,
        )
    except Exception:
        return None
