"""
RevPilot AI — Evidence Temporal Validity and Supersession Filter
Specification: docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md §4
Enforces INV-EVD-002, INV-DATA-001, and FR-EVD-003.
"""

from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.evidence.domain.models import EvidenceRecord, SupersessionStatus


def is_evidence_temporally_valid(record: EvidenceRecord, as_of_time: UtcDateTime) -> bool:
    """
    Evaluate whether an evidence clause or document is valid and active at :as_of_time perspective.
    
    Formula (§4):
        (effective_time <= as_of_time) AND
        (expiration_time IS NULL OR expiration_time > as_of_time) AND
        (supersession_status == ACTIVE OR (supersession_status == SUPERSEDED AND superseded_at > as_of_time))
    """
    # 1. Effective date check: cannot use future-dated contracts or events (INV-DATA-001)
    if record.effective_time.value > as_of_time.value:
        return False

    # 2. Expiration check: cannot use expired clauses
    if record.expiration_time is not None and record.expiration_time.value <= as_of_time.value:
        return False

    # 3. Supersession / revocation check (INV-EVD-002, FR-EVD-003)
    if record.supersession_status == SupersessionStatus.ACTIVE:
        return True

    if record.supersession_status == SupersessionStatus.SUPERSEDED:
        # If clause was superseded AFTER as_of_time, it was still active at the time of incident
        return record.superseded_at is not None and record.superseded_at.value > as_of_time.value

    # REVOKED or EXPIRED
    return False
