"""
RevPilot AI — Ticket Intelligence and Untrusted Content Boundary Module
Specification: docs/06-agent-platform/TICKET-INTELLIGENCE-SPEC.md §1–§7
Exports canonical ticket models, PII scrubbing, injection defense, and evidence extractor.
"""

from revpilot.modules.tickets.domain.models import (
    CanonicalTicket,
    InMemoryTicketStore,
    OutOfOrderTicketError,
    TicketDlpBlockedError,
    TicketPriority,
    TicketStatus,
    compute_ticket_digest,
)
from revpilot.modules.tickets.services.dlp_scrubber import (
    calculate_injection_risk,
    frame_untrusted_ticket,
    scrub_pii_and_secrets,
)
from revpilot.modules.tickets.services.evidence_extractor import (
    extract_ticket_evidence,
)
from revpilot.modules.tickets.services.normalizer import (
    normalize_ticket_text,
)

__all__ = [
    "CanonicalTicket",
    "InMemoryTicketStore",
    "OutOfOrderTicketError",
    "TicketDlpBlockedError",
    "TicketPriority",
    "TicketStatus",
    "calculate_injection_risk",
    "compute_ticket_digest",
    "extract_ticket_evidence",
    "frame_untrusted_ticket",
    "normalize_ticket_text",
    "scrub_pii_and_secrets",
]
