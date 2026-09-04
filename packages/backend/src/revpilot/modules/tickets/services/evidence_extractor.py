"""
RevPilot AI — Ticket Evidence Extractor Service
Specification: docs/06-agent-platform/TICKET-INTELLIGENCE-SPEC.md §5
Extracts verified EvidenceRecord items from canonical tickets, filtering out quarantined records.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from revpilot.shared.identifiers import UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.evidence.domain.models import (
    EvidenceRecord,
    CitationSpan,
    SourceSystemType,
    ClassificationLevel,
    SupersessionStatus,
    ExtractionMethod,
    RetrievalMethod,
)

if TYPE_CHECKING:
    from revpilot.modules.tickets.domain.models import CanonicalTicket


def extract_ticket_evidence(
    tickets: list[CanonicalTicket],
    investigation_id: UUIDv7,
) -> list[EvidenceRecord]:
    """
    Transform non-quarantined canonical tickets into immutable EvidenceRecord objects
    ready for packaging into an investigation evidence bundle (AC-P03-007-02).
    """
    records: list[EvidenceRecord] = []
    now = UtcDateTime.now()

    for ticket in tickets:
        # Strictly exclude quarantined / poisoned tickets from evidence
        if ticket.is_quarantined:
            continue

        body_snippet = ticket.body_masked[:200] if ticket.body_masked else ticket.subject_masked
        span = None
        if body_snippet:
            span = CitationSpan(
                chunk_id=ticket.ticket_id,
                start_char=0,
                end_char=len(body_snippet),
                snippet_text=body_snippet,
            )

        record = EvidenceRecord(
            evidence_id=UUIDv7.generate(),
            tenant_id=ticket.tenant_id,
            acl_policy_ref="policy_ticket_read",
            source_system=SourceSystemType.SUPPORT_DESK,
            source_object_ref=f"ticket:{ticket.ticket_id}",
            source_version=str(ticket.version),
            content_digest=ticket.content_digest,
            classification=ClassificationLevel.INTERNAL,
            event_time=ticket.created_at,
            effective_time=ticket.updated_at,
            as_of_time=now,
            ingestion_time=now,
            supersession_status=SupersessionStatus.ACTIVE,
            lineage_parent_ids=[investigation_id],
            extraction_method=ExtractionMethod.TICKET_EXTRACT,
            parser_version="1.0.0",
            retrieval_method=RetrievalMethod.SQL_DIRECT,
            citation_span=span,
            confidence_score=0.90,
            redaction_state="PII_MASKED",
            payload={
                "ticket_id": ticket.ticket_id,
                "customer_id": ticket.customer_id,
                "category": ticket.category,
                "priority": ticket.priority.value,
                "status": ticket.status.value,
                "subject": ticket.subject_masked,
                "body": ticket.body_masked,
                "sentiment_score": ticket.sentiment_score,
            },
        )
        records.append(record)

    return records
