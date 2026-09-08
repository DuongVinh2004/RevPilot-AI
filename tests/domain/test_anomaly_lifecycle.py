"""
RevPilot AI — Anomaly Aggregate Lifecycle State Machine Unit Tests (Phase 02)
Verifies AC-P02-005-01, AC-P02-005-04, and ANOMALY-DOMAIN-SPEC.md §4.
"""

from __future__ import annotations
import sys
from typing import Any
import pytest

from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import PrincipalContext


@pytest.fixture(autouse=True)
def _isolate_analytics_module():
    """Ensure analytics module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.analytics"):
            sys.modules.pop(mod, None)


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha")


@pytest.fixture
def analyst_principal(tenant_alpha) -> PrincipalContext:
    return PrincipalContext(
        principal_id=PrincipalId("usr_analyst_01"),
        tenant_id=tenant_alpha,
        roles=frozenset({"analyst"}),
        permissions=frozenset({"analytics:write"}),
    )


@pytest.fixture
def system_principal(tenant_alpha) -> PrincipalContext:
    return PrincipalContext(
        principal_id=PrincipalId("usr_system_worker"),
        tenant_id=tenant_alpha,
        is_system=True,
    )


@pytest.fixture
def sample_anomaly(tenant_alpha) -> Any:
    from revpilot.modules.analytics.lifecycle import AnomalyAggregate
    now = UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z")
    return AnomalyAggregate.create_detected(
        id="anm_lifecycle_001",
        tenant_id=tenant_alpha,
        metric_id="METRIC-001",
        metric_version="1.0.0",
        detector_id="DET-STL-RESIDUAL-001",
        detector_version="1.0.0",
        baseline_id="BASE-SEASONAL-NAIVE-001",
        baseline_version="1.0.0",
        observation_window_start=UtcDateTime.from_iso("2026-02-14T00:00:00.000000Z"),
        observation_window_end=UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z"),
        as_of_time=now,
        actual_value=0.0842,
        expected_value=0.0180,
        expected_interval=(0.0110, 0.0250),
        anomaly_score=0.8840,
        severity="CRITICAL",
        created_at=now,
    )


# =============================================================================
# AC-P02-005-01 & AC-P02-005-04: Full Valid State Progression
# =============================================================================

def test_valid_lifecycle_progression(sample_anomaly, analyst_principal, system_principal):
    """
    AC-P02-005-01: Valid transitions (DETECTED -> VALIDATED -> LOCALIZED -> ACKNOWLEDGED -> RESOLVED) succeed
    and emit corresponding outbox domain events.
    AC-P02-005-04: Every state transition logs an immutable AnomalyTransitionRecord with actor and reason.
    """
    from revpilot.modules.analytics.lifecycle import AnomalyState

    anm = sample_anomaly
    assert anm.state == AnomalyState.DETECTED
    assert anm.version == 1
    assert len(anm.transitions) == 1
    assert len(anm.pending_outbox_events) == 1
    assert anm.pending_outbox_events[0].event_type == "anomaly.detected.v1"

    # 1. DETECTED -> VALIDATED
    res1 = anm.transition_to(
        target_state=AnomalyState.VALIDATED,
        actor=system_principal,
        reason="DQ_CHECK_PASSED",
        metadata={"dq_state": "PASSED"},
    )
    assert res1.is_success
    assert anm.state == AnomalyState.VALIDATED
    assert anm.version == 2
    rec1 = res1.unwrap()
    assert rec1.from_state == AnomalyState.DETECTED
    assert rec1.to_state == AnomalyState.VALIDATED
    assert rec1.reason == "DQ_CHECK_PASSED"
    assert rec1.actor_type == "SYSTEM_WORKER"

    # 2. VALIDATED -> LOCALIZED
    res2 = anm.transition_to(
        target_state=AnomalyState.LOCALIZED,
        actor=system_principal,
        reason="LOCALIZATION_COMPLETE",
        metadata={"dimension": "carrier_id", "top_segment": "CARRIER_REGIONAL_LOGISTICS"},
    )
    assert res2.is_success
    assert anm.state == AnomalyState.LOCALIZED
    assert anm.version == 3
    rec2 = res2.unwrap()
    assert rec2.from_state == AnomalyState.VALIDATED
    assert rec2.to_state == AnomalyState.LOCALIZED

    # 3. LOCALIZED -> ACKNOWLEDGED
    res3 = anm.transition_to(
        target_state=AnomalyState.ACKNOWLEDGED,
        actor=analyst_principal,
        reason="ANALYST_INVESTIGATION_OPENED",
        metadata={"investigation_id": "inv_01h8abcde"},
    )
    assert res3.is_success
    assert anm.state == AnomalyState.ACKNOWLEDGED
    assert anm.version == 4
    rec3 = res3.unwrap()
    assert rec3.from_state == AnomalyState.LOCALIZED
    assert rec3.to_state == AnomalyState.ACKNOWLEDGED
    assert rec3.actor_id == "usr_analyst_01"
    assert rec3.actor_type == "PRINCIPAL"

    # 4. ACKNOWLEDGED -> RESOLVED
    res4 = anm.transition_to(
        target_state=AnomalyState.RESOLVED,
        actor=analyst_principal,
        reason="METRIC_SUBSIDED_TO_BASELINE",
        metadata={"resolution_type": "INCIDENT_SUBSIDED", "final_metric_value": 0.0182},
    )
    assert res4.is_success
    assert anm.state == AnomalyState.RESOLVED
    assert anm.version == 5
    assert anm.effective_to is not None
    rec4 = res4.unwrap()
    assert rec4.from_state == AnomalyState.ACKNOWLEDGED
    assert rec4.to_state == AnomalyState.RESOLVED

    # Verify audit trail and outbox events
    assert len(anm.transitions) == 5
    assert len(anm.pending_outbox_events) == 5

    event_types = [e.event_type for e in anm.pending_outbox_events]
    assert event_types == [
        "anomaly.detected.v1",
        "anomaly.validated.v1",
        "anomaly.localized.v1",
        "anomaly.acknowledged.v1",
        "anomaly.resolved.v1",
    ]


def test_reopen_resolved_anomaly(sample_anomaly, analyst_principal, system_principal):
    """From RESOLVED state, aggregate can transition to REOPENED when metric re-diverges."""
    from revpilot.modules.analytics.lifecycle import AnomalyState

    anm = sample_anomaly
    anm.transition_to(AnomalyState.VALIDATED, system_principal, "DQ_PASSED")
    anm.transition_to(AnomalyState.LOCALIZED, system_principal, "LOCALIZED")
    anm.transition_to(AnomalyState.ACKNOWLEDGED, analyst_principal, "ACKNOWLEDGED")
    anm.transition_to(AnomalyState.RESOLVED, analyst_principal, "RESOLVED")
    assert anm.state == AnomalyState.RESOLVED

    # Transition to REOPENED
    res = anm.transition_to(
        target_state=AnomalyState.REOPENED,
        actor=system_principal,
        reason="METRIC_RE_DIVERGED_WITHIN_48H",
        metadata={"new_actual_value": 0.0910, "trigger_score": 0.92},
    )
    assert res.is_success
    assert anm.state == AnomalyState.REOPENED
    rec = res.unwrap()
    assert rec.from_state == AnomalyState.RESOLVED
    assert rec.to_state == AnomalyState.REOPENED
    assert anm.pending_outbox_events[-1].event_type == "anomaly.reopened.v1"


def test_suppress_from_validated(sample_anomaly, system_principal):
    """Transitioning to SUPPRESSED sets suppression_reason and effective_to watermark."""
    from revpilot.modules.analytics.lifecycle import AnomalyState

    anm = sample_anomaly
    anm.transition_to(AnomalyState.VALIDATED, system_principal, "DQ_PASSED")

    res = anm.transition_to(
        target_state=AnomalyState.SUPPRESSED,
        actor=system_principal,
        reason="SCHEDULED_WAREHOUSE_MAINTENANCE_FILTER",
        metadata={"suppression_rule_id": "rule_maint_001"},
    )
    assert res.is_success
    assert anm.state == AnomalyState.SUPPRESSED
    assert anm.suppression_reason == "SCHEDULED_WAREHOUSE_MAINTENANCE_FILTER"
    assert anm.effective_to is not None
    assert anm.pending_outbox_events[-1].event_type == "anomaly.suppressed.v1"
