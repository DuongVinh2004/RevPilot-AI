"""
RevPilot AI — Governed Approval State Machine
Specification: docs/14-iam/IAM-SPEC.md#approval-lifecycle
Conforms to INV-ACT-001, INV-ACT-003, AC-008.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from revpilot.shared.results import Result, Success, Failure


class ApprovalState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHING = "DISPATCHING"
    SUCCEEDED = "SUCCEEDED"
    PROVIDER_FAILED = "PROVIDER_FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


VALID_TRANSITIONS: dict[ApprovalState, frozenset[ApprovalState]] = {
    ApprovalState.PENDING: frozenset(
        {
            ApprovalState.APPROVED,
            ApprovalState.REJECTED,
            ApprovalState.EXPIRED,
            ApprovalState.CANCELLED,
        }
    ),
    ApprovalState.APPROVED: frozenset(
        {
            ApprovalState.DISPATCHING,
            ApprovalState.EXPIRED,
            ApprovalState.CANCELLED,
        }
    ),
    ApprovalState.DISPATCHING: frozenset(
        {
            ApprovalState.SUCCEEDED,
            ApprovalState.PROVIDER_FAILED,
        }
    ),
    ApprovalState.REJECTED: frozenset(),
    ApprovalState.SUCCEEDED: frozenset(),
    ApprovalState.PROVIDER_FAILED: frozenset(),
    ApprovalState.EXPIRED: frozenset(),
    ApprovalState.CANCELLED: frozenset(),
}


@dataclass
class TransitionEvent:
    from_state: ApprovalState
    to_state: ApprovalState
    actor: str
    reason: str | None
    timestamp: datetime


def transition(
    current_state: ApprovalState,
    new_state: ApprovalState,
    actor: str,
    reason: str | None = None,
) -> Result[TransitionEvent, str]:
    """Attempt state transition. Returns Success(event) or Failure(reason)."""
    if isinstance(current_state, str) and not isinstance(current_state, ApprovalState):
        try:
            current_state = ApprovalState(current_state)
        except ValueError:
            return Failure(f"Invalid current state: {current_state}")

    if isinstance(new_state, str) and not isinstance(new_state, ApprovalState):
        try:
            new_state = ApprovalState(new_state)
        except ValueError:
            return Failure(f"Invalid target state: {new_state}")

    allowed = VALID_TRANSITIONS.get(current_state, frozenset())
    if new_state not in allowed:
        return Failure(
            f"Invalid transition from {current_state.value} to {new_state.value}"
        )

    event = TransitionEvent(
        from_state=current_state,
        to_state=new_state,
        actor=actor,
        reason=reason,
        timestamp=datetime.now(timezone.utc),
    )
    return Success(event)
