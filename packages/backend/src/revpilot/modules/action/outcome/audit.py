"""
RevPilot AI — Action Audit Logging & Security Observability
Specification: docs/22-billing/AUDIT-LOG-SPEC.md §2, §3
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §2
Conforms to INV-AUD-001 (100% unsampled audit), INV-AUD-002 (Zero secret archive), and NFR-OBS-001.
"""

from __future__ import annotations
import logging
import re
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)

SENSITIVE_AUDIT_KEYS = {
    "token",
    "token_id",
    "token_value",
    "secret",
    "api_key",
    "password",
    "authorization",
    "credential",
    "private_key",
    "bearer",
}

BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE)


def scrub_audit_details(data: Any) -> Any:
    """Recursively scrub secrets and bearer tokens from audit metadata payloads (INV-AUD-002)."""
    if isinstance(data, dict):
        scrubbed = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_AUDIT_KEYS):
                scrubbed[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                scrubbed[k] = scrub_audit_details(v)
            elif isinstance(v, str) and BEARER_PATTERN.search(v):
                scrubbed[k] = BEARER_PATTERN.sub("Bearer [REDACTED]", v)
            else:
                scrubbed[k] = v
        return scrubbed
    elif isinstance(data, list):
        return [scrub_audit_details(item) for item in data]
    elif isinstance(data, str) and BEARER_PATTERN.search(data):
        return BEARER_PATTERN.sub("Bearer [REDACTED]", data)
    return data


class ActionAuditEvent(BaseModel):
    """
    Immutable audit record for governed action lifecycle events.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    audit_id: UUIDv7
    occurred_at: UtcDateTime
    event_type: str = Field(min_length=1)
    tenant_id: TenantId
    actor_id: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    action: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)


class ActionAuditLogger:
    """
    Unsampled, immutable audit recorder for governed action events.
    Enforces secret scrubbing before recording.
    """

    def __init__(self) -> None:
        self._journal: list[ActionAuditEvent] = []

    def log_event(
        self,
        tenant_id: TenantId,
        actor_id: str,
        event_type: str,
        resource: str,
        action: str,
        outcome: str = "SUCCESS",
        details: dict[str, Any] | None = None,
    ) -> ActionAuditEvent:
        """Record an unsampled, sanitized audit event (INV-AUD-001)."""
        safe_details = scrub_audit_details(details or {})
        event = ActionAuditEvent(
            audit_id=UUIDv7.generate(),
            occurred_at=UtcDateTime.now(),
            event_type=event_type,
            tenant_id=tenant_id,
            actor_id=actor_id.strip(),
            resource=resource.strip(),
            action=action.strip(),
            outcome=outcome.strip(),
            details=safe_details,
        )
        self._journal.append(event)
        logger.info(
            "AUDIT [%s] tenant=%s actor=%s resource=%s outcome=%s",
            event_type,
            tenant_id,
            actor_id,
            resource,
            outcome,
        )
        return event

    def get_events(
        self,
        tenant_id: TenantId | None = None,
        event_type: str | None = None,
    ) -> list[ActionAuditEvent]:
        events = self._journal
        if tenant_id:
            events = [e for e in events if str(e.tenant_id) == str(tenant_id)]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return list(events)

    def clear(self) -> None:
        self._journal.clear()


GLOBAL_AUDIT_LOGGER = ActionAuditLogger()
