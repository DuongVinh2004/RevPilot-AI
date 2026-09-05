"""
RevPilot AI — Deterministic Verification and Rejection Rules
Specification: docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md §3
"""

from __future__ import annotations
import re
from typing import Any, Optional
from revpilot.modules.verifier.domain import ClaimCategory, VerifiedClaim
from revpilot.modules.evidence.domain.models import EvidenceRecord, SupersessionStatus
from revpilot.shared.temporal import UtcDateTime

CAUSAL_KEYWORDS = [
    r"\bcaused\b",
    r"\bcauses\b",
    r"\bcausing\b",
    r"\bdrive[s]?\b",
    r"\bdriven by\b",
    r"\bled to\b",
    r"\bleads to\b",
    r"\bresulted in\b",
    r"\bresults in\b",
    r"\bdue to\b",
    r"\bbecause of\b",
    r"\broot cause\b",
]

SELF_AUTHORIZATION_KEYWORDS = [
    r"\bauthorize[s]?\b",
    r"\bwaive[s]?\b",
    r"\bapprove[s]?\b",
    r"\boverride[s]? policy\b",
    r"\bgrant[s]? access\b",
]

def check_citation_span(claim: VerifiedClaim, record: EvidenceRecord) -> bool:
    if record.citation_span is None:
        return True
    span = record.citation_span
    return span.start_char < span.end_char and len(span.snippet_text.strip()) > 0

def check_temporal_leakage(claim: VerifiedClaim, as_of_time: UtcDateTime) -> bool:
    return claim.temporal_as_of > as_of_time

def check_correlation_causation_fallacy(claim: VerifiedClaim) -> bool:
    if claim.category == ClaimCategory.ASSOCIATION:
        lower_stmt = claim.statement.lower()
        for kw in CAUSAL_KEYWORDS:
            if re.search(kw, lower_stmt):
                return True
    return False

def check_self_authorization(claim: VerifiedClaim) -> bool:
    lower_stmt = claim.statement.lower()
    for kw in SELF_AUTHORIZATION_KEYWORDS:
        if re.search(kw, lower_stmt):
            return True
    return False
