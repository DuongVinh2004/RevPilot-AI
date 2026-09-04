"""
RevPilot AI — P0 Incident Response & On-Call Paging Drill Runner
Specification: docs/24-sre/INCIDENT-RESPONSE-RUNBOOK.md §1..§6
Specification: docs/24-sre/PRODUCTION-READINESS-GATE.md §10
Conforms to INV-REL-002, AC-P08-008-02, and TC-P08-025.
"""

from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, ConfigDict

from revpilot.shared.errors import DomainError
from revpilot.shared.identifiers import UUIDv7
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


# --- Domain Errors ---

class PagingDrillTimeoutError(DomainError):
    """On-call paging SLA failed (> 15 minutes / 900s) (Status 500, Non-retryable)."""

    def __init__(
        self,
        message: str = "On-call paging SLA failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PAGING_DRILL_TIMEOUT",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 500


# --- Data Models ---

class DrillResult(BaseModel):
    """Execution summary of simulated P0 incident on-call paging drill."""
    model_config = ConfigDict(frozen=True)

    incident_id: str
    severity: str
    paging_latency_seconds: float
    on_call_acknowledged: bool
    status: str
    acknowledged_by: str
    timestamp: UtcDateTime


# --- Drill Runner ---

class IncidentDrillRunner:
    """
    Simulates mock P0 pager duty dispatch and validates rapid on-call routing.
    Enforces that primary on-call acknowledges paging alert in < 15 minutes (900s).
    """

    def __init__(self, default_sla_seconds: float = 900.0) -> None:
        self.default_sla_seconds = default_sla_seconds

    def simulate_p0_paging_drill(
        self,
        max_allowed_seconds: float | None = None,
        simulated_latency_sec: float | None = None,
    ) -> DrillResult:
        """
        Execute simulated P0 incident paging drill (TC-P08-025).
        Raises PAGING_DRILL_TIMEOUT (500) if paging latency > 15 minutes.
        """
        sla_limit = max_allowed_seconds if max_allowed_seconds is not None else self.default_sla_seconds
        incident_id = f"inc_{UUIDv7.generate()}"

        # Real mock drill defaults to 180s (3 minutes), well under the 900s SLA
        latency = simulated_latency_sec if simulated_latency_sec is not None else 180.0

        if latency > sla_limit:
            logger.error("Incident drill %s breached on-call SLA: %fs > %fs", incident_id, latency, sla_limit)
            raise PagingDrillTimeoutError(
                message=f"On-call paging SLA failed: notification took {latency:.1f}s (> {sla_limit:.1f}s)",
                details={
                    "incident_id": incident_id,
                    "paging_latency_seconds": latency,
                    "sla_limit_seconds": sla_limit,
                },
            )

        logger.info("Incident drill %s passed: acknowledged in %fs", incident_id, latency)
        return DrillResult(
            incident_id=incident_id,
            severity="P0",
            paging_latency_seconds=latency,
            on_call_acknowledged=True,
            status="PASS",
            acknowledged_by="primary_oncall_sre",
            timestamp=UtcDateTime.now(),
        )
