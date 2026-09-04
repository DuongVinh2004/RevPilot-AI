"""
RevPilot AI — Canonical Ticket Domain Models and Ingestion Store
Specification: docs/06-agent-platform/TICKET-INTELLIGENCE-SPEC.md §2, §4
Implements CanonicalTicket schema, enums, and monotonic event ordering (INV-DATA-001).
"""

from __future__ import annotations
import hashlib
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError


class TicketPriority(str, Enum):
    """Support ticket severity priority."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TicketStatus(str, Enum):
    """Lifecycle status of customer ticket."""
    NEW = "NEW"
    OPEN = "OPEN"
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CanonicalTicket(BaseModel):
    """
    Sanitized, PII-scrubbed canonical representation of external support ticket.
    Conforms to TICKET-INTELLIGENCE-SPEC.md §2.2.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    ticket_id: str
    tenant_id: TenantId
    source_system: str
    version: int = Field(default=1, ge=1)
    customer_id: str
    created_at: UtcDateTime
    updated_at: UtcDateTime
    status: TicketStatus
    priority: TicketPriority
    category: str
    subject_masked: str
    body_masked: str
    sentiment_score: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    injection_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_quarantined: bool = False
    content_digest: str


class TicketDlpBlockedError(DomainError):
    """Triggered when ticket content contains unmaskable secrets or severe risk."""

    def __init__(
        self,
        message: str = "Ticket quarantined due to high-risk secret or injection",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ERR_TICKET_DLP_BLOCKED",
            message=message,
            details=details,
            retryable=False,
        )


class OutOfOrderTicketError(DomainError):
    """Triggered when an incoming ticket update has an earlier timestamp than stored record."""

    def __init__(
        self,
        message: str = "Out-of-order ticket event recorded to history without state override",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ERR_OUT_OF_ORDER_TICKET",
            message=message,
            details=details,
            retryable=False,
        )


def compute_ticket_digest(body: str) -> str:
    """Deterministic SHA-256 digest of masked ticket text."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class InMemoryTicketStore:
    """
    In-memory store enforcing idempotent ingestion and monotonic timestamp ordering
    according to TICKET-INTELLIGENCE-SPEC.md §4.
    """

    def __init__(self) -> None:
        # Key: (tenant_id_str, source_system, ticket_id) -> CanonicalTicket
        self._store: dict[tuple[str, str, str], CanonicalTicket] = {}
        # Audit history of out-of-order or duplicate events
        self._history: dict[tuple[str, str, str], list[CanonicalTicket]] = {}

    def _make_key(self, tenant_id: TenantId, source_system: str, ticket_id: str) -> tuple[str, str, str]:
        return (str(tenant_id), source_system, ticket_id)

    def ingest(self, ticket: CanonicalTicket) -> tuple[CanonicalTicket, bool]:
        """
        Ingest a ticket with deduplication and monotonic event ordering:
        - Duplicate event (same version and timestamps): acknowledged idempotently (returns False for modified).
        - Out-of-order event (updated_at < stored.updated_at): stored in history but does not overwrite active state.
        - Monotonic update: overwrites stored active state.
        Returns: (active_ticket, is_new_or_updated)
        """
        key = self._make_key(ticket.tenant_id, ticket.source_system, ticket.ticket_id)
        if key not in self._history:
            self._history[key] = []

        if key not in self._store:
            self._store[key] = ticket
            self._history[key].append(ticket)
            return ticket, True

        stored = self._store[key]

        # 1. Exact deduplication
        if (
            stored.version == ticket.version
            and stored.updated_at == ticket.updated_at
            and stored.content_digest == ticket.content_digest
        ):
            return stored, False

        # 2. Out-of-order event protection (INV-DATA-001)
        if ticket.updated_at < stored.updated_at:
            self._history[key].append(ticket)
            # Retain canonical active state
            return stored, False

        # 3. Monotonic update
        self._store[key] = ticket
        self._history[key].append(ticket)
        return ticket, True

    def get(self, tenant_id: TenantId, source_system: str, ticket_id: str) -> Optional[CanonicalTicket]:
        key = self._make_key(tenant_id, source_system, ticket_id)
        return self._store.get(key)

    def get_history(self, tenant_id: TenantId, source_system: str, ticket_id: str) -> list[CanonicalTicket]:
        key = self._make_key(tenant_id, source_system, ticket_id)
        return list(self._history.get(key, []))

    def list_by_tenant(self, tenant_id: TenantId) -> list[CanonicalTicket]:
        t_id_str = str(tenant_id)
        return [t for k, t in self._store.items() if k[0] == t_id_str]
