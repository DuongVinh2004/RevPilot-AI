"""
Unit tests for Approval State Machine with atomic transitions (TASK-AR-012).
Conforms to docs/14-iam/IAM-SPEC.md#approval-lifecycle, INV-ACT-001, INV-ACT-003.
"""

from datetime import datetime, timezone
import pytest

from revpilot.modules.approval.state_machine import (
    ApprovalState,
    TransitionEvent,
    transition,
)


def test_01_pending_to_approved_succeeds():
    """PENDING → APPROVED succeeds."""
    res = transition(
        current_state=ApprovalState.PENDING,
        new_state=ApprovalState.APPROVED,
        actor="usr_operator_1",
    )
    assert res.is_success
    event = res.unwrap()
    assert event.from_state == ApprovalState.PENDING
    assert event.to_state == ApprovalState.APPROVED
    assert event.actor == "usr_operator_1"


def test_02_pending_to_rejected_succeeds():
    """PENDING → REJECTED succeeds."""
    res = transition(
        current_state=ApprovalState.PENDING,
        new_state=ApprovalState.REJECTED,
        actor="usr_operator_2",
        reason="Budget exceeded",
    )
    assert res.is_success
    event = res.unwrap()
    assert event.from_state == ApprovalState.PENDING
    assert event.to_state == ApprovalState.REJECTED
    assert event.reason == "Budget exceeded"


def test_03_approved_to_dispatching_succeeds():
    """APPROVED → DISPATCHING succeeds."""
    res = transition(
        current_state=ApprovalState.APPROVED,
        new_state=ApprovalState.DISPATCHING,
        actor="system_gateway",
    )
    assert res.is_success
    event = res.unwrap()
    assert event.from_state == ApprovalState.APPROVED
    assert event.to_state == ApprovalState.DISPATCHING


def test_04_approved_to_approved_fails():
    """APPROVED → APPROVED fails (invalid self-transition)."""
    res = transition(
        current_state=ApprovalState.APPROVED,
        new_state=ApprovalState.APPROVED,
        actor="usr_operator_1",
    )
    assert res.is_failure
    error_msg = res.unwrap_error()
    assert "Invalid transition" in error_msg


def test_05_succeeded_to_cancelled_fails():
    """SUCCEEDED → CANCELLED fails (terminal state cannot transition)."""
    res = transition(
        current_state=ApprovalState.SUCCEEDED,
        new_state=ApprovalState.CANCELLED,
        actor="usr_operator_1",
    )
    assert res.is_failure
    error_msg = res.unwrap_error()
    assert "Invalid transition" in error_msg


def test_06_dispatching_to_succeeded_succeeds():
    """DISPATCHING → SUCCEEDED succeeds."""
    res = transition(
        current_state=ApprovalState.DISPATCHING,
        new_state=ApprovalState.SUCCEEDED,
        actor="system_gateway",
    )
    assert res.is_success
    event = res.unwrap()
    assert event.from_state == ApprovalState.DISPATCHING
    assert event.to_state == ApprovalState.SUCCEEDED


def test_07_dispatching_to_provider_failed_succeeds():
    """DISPATCHING → PROVIDER_FAILED succeeds."""
    res = transition(
        current_state=ApprovalState.DISPATCHING,
        new_state=ApprovalState.PROVIDER_FAILED,
        actor="system_gateway",
        reason="Upstream HTTP 500 error",
    )
    assert res.is_success
    event = res.unwrap()
    assert event.from_state == ApprovalState.DISPATCHING
    assert event.to_state == ApprovalState.PROVIDER_FAILED
    assert event.reason == "Upstream HTTP 500 error"


def test_08_transition_event_records_actor_and_timestamp():
    """TransitionEvent records actor, from_state, to_state, and recent UTC timestamp."""
    before = datetime.now(timezone.utc)
    res = transition(
        current_state=ApprovalState.PENDING,
        new_state=ApprovalState.APPROVED,
        actor="usr_lead_approver",
        reason="Signed by lead",
    )
    after = datetime.now(timezone.utc)

    assert res.is_success
    event: TransitionEvent = res.unwrap()
    assert event.actor == "usr_lead_approver"
    assert event.from_state == ApprovalState.PENDING
    assert event.to_state == ApprovalState.APPROVED
    assert event.reason == "Signed by lead"
    assert isinstance(event.timestamp, datetime)
    assert before <= event.timestamp <= after
