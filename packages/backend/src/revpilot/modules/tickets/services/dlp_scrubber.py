"""
RevPilot AI — Ticket DLP Scrubber and Prompt Injection Defense
Specification: docs/06-agent-platform/TICKET-INTELLIGENCE-SPEC.md §3, §6
Enforces PII/secret scrubbing (INV-PRV-001, NFR-PRV-001) and prompt injection quarantine (INV-SEC-002, AC-P03-007-01..02).
"""

from __future__ import annotations
import re

# 1. Credit card / PAN detection (Visa, MasterCard, Amex, Discover, standard 13-19 digit blocks)
_CREDIT_CARD_REGEX = re.compile(
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:[0-9]{4}[ -]?){3}[0-9]{4})\b"
)

# 2. Social Security / Tax ID detection
_TAX_ID_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{2}-\d{7}\b")

# 3. High-entropy API keys, Bearer tokens, secrets, and credentials
_SECRET_KEYWORD_REGEX = re.compile(
    r"(?i)\b(?:api[_-]?key|bearer|access[_-]?token|secret[_-]?key|auth[_-]?token|password|passwd|client[_-]?secret)\s*[:=]?\s*['\"]?[a-zA-Z0-9_\-\.]{8,}['\"]?"
)
_SECRET_PREFIX_REGEX = re.compile(
    r"\b(?:sk|pk|ghp|gho|xoxb|xoxp|live_secret|live_key|rk)_[a-zA-Z0-9_\-]{16,}\b"
)

# 4. Email address masking
_EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# 5. Phone number masking
_PHONE_REGEX = re.compile(
    r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?[2-9]\d{2}[-.\s]?\d{4}\b|\b\+\d{1,3}[-.\s]\d{3,4}[-.\s]\d{3,4}\b"
)

# Prompt injection threat signatures
_INJECTION_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"(?i)\bignore\s+(?:all\s+)?(?:previous|above)\s+instructions\b"),
    re.compile(r"(?i)\bdisregard\s+(?:all\s+)?prior\s+instructions\b"),
    re.compile(r"(?i)\bsystem\s+prompt\s+override\b"),
    re.compile(r"(?i)\byou\s+are\s+now\b"),
    re.compile(r"(?i)\byou\s+must\s+now\s+act\s+as\b"),
    re.compile(r"(?i)\bdeveloper\s+mode\s+(?:enabled|active)\b"),
    re.compile(r"(?i)^\s*system\s*:\s*"),
    re.compile(r"(?i)\bauthorize\s+refund\b"),
    re.compile(r"(?i)\bgrant\s+admin(?:istrator)?\b"),
    re.compile(r"(?i)\bbypass\s+authorization\b"),
    re.compile(r"(?i)<\s*script[^>]*>"),
)


def scrub_pii_and_secrets(text: str) -> str:
    """
    Scrub raw customer ticket text of all PII, PANs, tax IDs, and credentials.
    Conforms to INV-PRV-001 and NFR-PRV-001.
    """
    if not text:
        return ""

    # Order matters: first secrets and credentials
    scrubbed = _SECRET_KEYWORD_REGEX.sub("[REDACTED_SECRET]", text)
    scrubbed = _SECRET_PREFIX_REGEX.sub("[REDACTED_SECRET]", scrubbed)

    # Credit card PANs
    scrubbed = _CREDIT_CARD_REGEX.sub("[REDACTED_CC]", scrubbed)

    # Tax IDs and SSNs
    scrubbed = _TAX_ID_REGEX.sub("[REDACTED_TAX_ID]", scrubbed)

    # Email addresses
    scrubbed = _EMAIL_REGEX.sub("[EMAIL_MASKED]", scrubbed)

    # Phone numbers
    scrubbed = _PHONE_REGEX.sub("[PHONE_MASKED]", scrubbed)

    return scrubbed


def calculate_injection_risk(text: str) -> float:
    """
    Calculate prompt injection risk heuristic [0.0, 1.0].
    Returns > 0.85 if prompt injection patterns are detected (triggers quarantine).
    """
    if not text:
        return 0.0

    matches = 0
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            matches += 1

    if matches >= 2:
        return 0.98
    elif matches == 1:
        return 0.90

    return 0.0


def frame_untrusted_ticket(text: str, ticket_id: str) -> str:
    """
    Enclose untrusted ticket text in isolation containment tags.
    Escapes any counterfeit closing tags to prevent delimiter injection.
    """
    sanitized = text.replace("</untrusted_support_ticket>", "&lt;/untrusted_support_ticket&gt;")
    return f'<untrusted_support_ticket id="{ticket_id}">\n{sanitized}\n</untrusted_support_ticket>'
