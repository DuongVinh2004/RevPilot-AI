"""
RevPilot AI — Ticket Text Normalizer Service
Specification: docs/06-agent-platform/TICKET-INTELLIGENCE-SPEC.md §3
Performs Unicode NFC normalization, strips null bytes, ANSI escapes, and control characters.
"""

from __future__ import annotations
import re
import unicodedata

_ANSI_ESCAPE_REGEX = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def normalize_ticket_text(raw_text: str) -> str:
    """
    Sanitize raw incoming text from external systems:
    1. Unicode NFC normalization (INV-DATA-001).
    2. Strip null bytes (\x00) and unprintable terminal escape sequences.
    3. Strip dangerous non-printable ASCII/Unicode control characters except tabs and newlines.
    """
    if not raw_text:
        return ""

    # 1. Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", raw_text)

    # 2. Strip null bytes
    normalized = normalized.replace("\x00", "")

    # 3. Strip ANSI escape sequences
    normalized = _ANSI_ESCAPE_REGEX.sub("", normalized)

    # 4. Remove unprintable control characters while preserving standard whitespace (\t, \n, \r)
    clean_chars = []
    for ch in normalized:
        if ch in ("\n", "\r", "\t"):
            clean_chars.append(ch)
        elif not unicodedata.category(ch).startswith("C"):
            clean_chars.append(ch)

    return "".join(clean_chars)
