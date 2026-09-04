"""
RevPilot AI — Prompt Injection Scanner and Document Framing Engine
Specification: docs/09-rag/RAG-SPEC.md §4
Enforces INV-SEC-002, SEC-004, and untrusted document isolation.
"""

from __future__ import annotations
import html
import re


INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|prompts|rules)", re.IGNORECASE),
    re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|an\s+uncensored|jailbreak)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(the\s+)?(above|previous|system)", re.IGNORECASE),
    re.compile(r"reveal\s+all\s+(passwords|credentials|keys|secrets|tokens|prompts)", re.IGNORECASE),
    re.compile(r"do\s+not\s+follow\s+(system|safety)\s+(guidelines|instructions)", re.IGNORECASE),
    re.compile(r"(<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>)", re.IGNORECASE),
]


def scan_prompt_injection(text: str) -> tuple[bool, float, list[str]]:
    """
    Scan raw document text for adversarial prompt injection / jailbreak patterns.
    
    Returns:
        (is_malicious: bool, risk_score: float, matched_rules: list[str])
    """
    if not text:
        return False, 0.0, []

    matched_rules: list[str] = []
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            matched_rules.append(match.group(0))

    if not matched_rules:
        return False, 0.0, []

    # Score calculation based on match count (capped at 1.0)
    risk_score = min(1.0, 0.4 + (0.3 * len(matched_rules)))
    is_malicious = risk_score >= 0.5

    return is_malicious, round(risk_score, 2), matched_rules


def sanitize_and_frame_document(chunk_text: str, source_id: str, document_title: str = "") -> str:
    """
    Neutralize delimiter breakout attempts and wrap document text in
    strict untrusted isolation tags conforming to §4.1:
    
    <untrusted_document source="..." id="...">
    ...
    </untrusted_document>
    """
    title = document_title or source_id
    # Neutralize closing delimiter breakout attacks
    sanitized = re.sub(r"</\s*untrusted_document\s*>", "&lt;/untrusted_document&gt;", chunk_text, flags=re.IGNORECASE)
    # Neutralize opening delimiter imitation
    sanitized = re.sub(r"<\s*untrusted_document", "&lt;untrusted_document", sanitized, flags=re.IGNORECASE)

    framed = f'<untrusted_document source="{html.escape(title)}" id="{html.escape(source_id)}">\n{sanitized}\n</untrusted_document>'
    return framed
