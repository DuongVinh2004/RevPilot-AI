"""
RevPilot AI — Action Outcome Measurement, FinOps Attribution and Audit Submodule
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §2, §3
Specification: docs/26-api/EVENT-CONTRACTS.md §8
"""

from revpilot.modules.action.outcome.domain import (
    ActionOutcomeRecord,
    ActionEventEnvelope,
    ActionOutcomeError,
    OutcomeSegregationViolationError,
)
from revpilot.modules.action.outcome.audit import (
    ActionAuditLogger,
    ActionAuditEvent,
    GLOBAL_AUDIT_LOGGER,
    scrub_audit_details,
)
from revpilot.modules.action.outcome.service import ActionOutcomeService

__all__ = [
    "ActionOutcomeRecord",
    "ActionEventEnvelope",
    "ActionOutcomeError",
    "OutcomeSegregationViolationError",
    "ActionAuditLogger",
    "ActionAuditEvent",
    "GLOBAL_AUDIT_LOGGER",
    "scrub_audit_details",
    "ActionOutcomeService",
]
