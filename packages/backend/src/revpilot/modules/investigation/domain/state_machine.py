"""
RevPilot AI — Investigation Lifecycle State Machine
Conforms to docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §4 and INV-WF-001.
"""

from __future__ import annotations
from typing import Optional
from revpilot.shared.results import Result, Success, Failure
from revpilot.modules.investigation.domain.models import InvestigationStatus
from revpilot.modules.investigation.domain.errors import InvalidStateTransitionError

_ACTIVE_STATES = {
    InvestigationStatus.INITIALIZING,
    InvestigationStatus.PLANNING,
    InvestigationStatus.GATHERING_EVIDENCE,
    InvestigationStatus.VERIFYING,
}

_TERMINAL_STATES = {
    InvestigationStatus.COMPLETED,
    InvestigationStatus.NEED_MORE_EVIDENCE,
    InvestigationStatus.CANCELLED,
    InvestigationStatus.FAILED,
}

_STATIC_PERMITTED_TRANSITIONS: dict[InvestigationStatus, set[InvestigationStatus]] = {
    InvestigationStatus.INITIALIZING: {
        InvestigationStatus.PLANNING,
        InvestigationStatus.FAILED,
        InvestigationStatus.PAUSED,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.PLANNING: {
        InvestigationStatus.GATHERING_EVIDENCE,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
        InvestigationStatus.PAUSED,
    },
    InvestigationStatus.GATHERING_EVIDENCE: {
        InvestigationStatus.VERIFYING,
        InvestigationStatus.PAUSED,
        InvestigationStatus.CANCELLED,
        InvestigationStatus.FAILED,
    },
    InvestigationStatus.VERIFYING: {
        InvestigationStatus.COMPLETED,
        InvestigationStatus.NEED_MORE_EVIDENCE,
        InvestigationStatus.GATHERING_EVIDENCE,
        InvestigationStatus.PAUSED,
        InvestigationStatus.CANCELLED,
        InvestigationStatus.FAILED,
    },
    InvestigationStatus.COMPLETED: set(),
    InvestigationStatus.NEED_MORE_EVIDENCE: set(),
    InvestigationStatus.CANCELLED: set(),
    InvestigationStatus.FAILED: set(),
}


def transition_investigation_state(
    current: InvestigationStatus,
    target: InvestigationStatus,
    prior_active_state: Optional[InvestigationStatus] = None,
) -> Result[InvestigationStatus, InvalidStateTransitionError]:
    """
    Validate and execute state transition for an investigation workflow.
    Enforces deterministic state machine rules per TEMPORAL-WORKFLOW-SPEC.md §4.
    """
    if current == InvestigationStatus.PAUSED:
        permitted: set[InvestigationStatus] = {
            InvestigationStatus.CANCELLED,
            InvestigationStatus.FAILED,
        }
        if prior_active_state is not None:
            if prior_active_state in _ACTIVE_STATES:
                permitted.add(prior_active_state)
        else:
            permitted.update(_ACTIVE_STATES)
    else:
        permitted = _STATIC_PERMITTED_TRANSITIONS.get(current, set())

    if target not in permitted:
        return Failure(
            InvalidStateTransitionError(
                f"Cannot transition investigation from '{current.value}' to '{target.value}'",
                details={
                    "current_status": current.value,
                    "target_status": target.value,
                    "permitted_targets": [s.value for s in permitted],
                    "is_terminal": current in _TERMINAL_STATES,
                },
            )
        )

    return Success(target)


__all__ = ["transition_investigation_state"]
