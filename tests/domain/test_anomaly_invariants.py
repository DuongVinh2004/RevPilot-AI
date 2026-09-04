"""
RevPilot AI — Anomaly Lifecycle Invariants & Failure Paths Unit Tests (Phase 02)
Verifies AC-P02-005-02, INV-TEN-001, and fail-closed state machine invariants.
"""

from __future__ import annotations
import sys
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
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta")


@pytest.fixture
def alpha_principal(tenant_alpha) -> PrincipalContext:
    return PrincipalContext(
        principal_id=PrincipalId("usr_alpha_01"),
        tenant_id=tenant_alpha,
        roles=frozenset({"analyst"}),
    )


@pytest.fixture
def beta_principal(tenant_beta) -> PrincipalContext:
    return PrincipalContext(
        principal_id=PrincipalId("usr_beta_01"),
        tenant_id=tenant_beta,
        roles=frozenset({"analyst"}),
    )


@pytest.fixture
def sample_anomaly(tenant_alpha):
    from revpilot.modules.analytics.lifecycle import AnomalyAggregate
    now = UtcDateTime.from_iso("2026-02-15T00:00:00.000000Z")
    return AnomalyAggregate.create_detected(
        id="anm_invariants_001",
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
# AC-P02-005-02: Illegal State Transitions Fail Closed with Zero Mutation
# =============================================================================

@pytest.mark.parametrize(
    "illegal_target",
    ["RESOLVED", "LOCALIZED", "ACKNOWLEDGED", "REOPENED"],
)
def test_illegal_transitions_from_detected_fail_closed(
    sample_anomaly, alpha_principal, illegal_target
):
    """AC-P02-005-02: Skipping required lifecycle stages from DETECTED fails closed with INVALID_STATE_TRANSITION and zero mutation."""
    from revpilot.modules.analytics.lifecycle import AnomalyState, InvalidStateTransitionError

    anm = sample_anomaly
    initial_version = anm.version
    initial_transitions_count = len(anm.transitions)
    initial_events_count = len(anm.pending_outbox_events)

    target = AnomalyState(illegal_target)
    res = anm.transition_to(target, alpha_principal, "ATTEMPT_ILLEGAL_SKIP")

    assert res.is_failure
    err = res.unwrap_error()
    assert isinstance(err, InvalidStateTransitionError)
    assert err.code == "INVALID_STATE_TRANSITION"
    assert err.http_status == 409

    # Verify zero state mutation
    assert anm.state == AnomalyState.DETECTED
    assert anm.version == initial_version
    assert len(anm.transitions) == initial_transitions_count
    assert len(anm.pending_outbox_events) == initial_events_count


def test_illegal_skip_from_validated_to_resolved(sample_anomaly, alpha_principal):
    """Skipping LOCALIZED and ACKNOWLEDGED to jump VALIDATED -> RESOLVED is rejected."""
    from revpilot.modules.analytics.lifecycle import AnomalyState, InvalidStateTransitionError

    anm = sample_anomaly
    anm.transition_to(AnomalyState.VALIDATED, alpha_principal, "VALIDATED")

    res = anm.transition_to(AnomalyState.RESOLVED, alpha_principal, "SKIP_TO_RESOLVE")
    assert res.is_failure
    err = res.unwrap_error()
    assert isinstance(err, InvalidStateTransitionError)
    assert err.code == "INVALID_STATE_TRANSITION"
    assert anm.state == AnomalyState.VALIDATED


def test_suppressed_state_is_terminal(sample_anomaly, alpha_principal):
    """SUPPRESSED state cannot transition to any active state."""
    from revpilot.modules.analytics.lifecycle import AnomalyState, InvalidStateTransitionError

    anm = sample_anomaly
    anm.transition_to(AnomalyState.SUPPRESSED, alpha_principal, "NOISE_FILTER")
    assert anm.state == AnomalyState.SUPPRESSED

    for target in (AnomalyState.VALIDATED, AnomalyState.LOCALIZED, AnomalyState.ACKNOWLEDGED, AnomalyState.RESOLVED):
        res = anm.transition_to(target, alpha_principal, "REVIVE_SUPPRESSED")
        assert res.is_failure
        err = res.unwrap_error()
        assert isinstance(err, InvalidStateTransitionError)
        assert err.code == "INVALID_STATE_TRANSITION"
        assert anm.state == AnomalyState.SUPPRESSED


# =============================================================================
# Terminal Resolved State Guard (ANOMALY_ALREADY_RESOLVED)
# =============================================================================

def test_mutation_on_resolved_anomaly_rejected(sample_anomaly, alpha_principal):
    """Direct mutation on RESOLVED anomaly without REOPENING raises ANOMALY_ALREADY_RESOLVED (HTTP 409)."""
    from revpilot.modules.analytics.lifecycle import AnomalyState, AnomalyAlreadyResolvedError

    anm = sample_anomaly
    anm.transition_to(AnomalyState.VALIDATED, alpha_principal, "VALIDATED")
    anm.transition_to(AnomalyState.LOCALIZED, alpha_principal, "LOCALIZED")
    anm.transition_to(AnomalyState.ACKNOWLEDGED, alpha_principal, "ACKNOWLEDGED")
    anm.transition_to(AnomalyState.RESOLVED, alpha_principal, "RESOLVED")
    assert anm.state == AnomalyState.RESOLVED

    # Attempt mutation without reopening
    res = anm.transition_to(AnomalyState.ACKNOWLEDGED, alpha_principal, "ATTEMPT_RE_ACKNOWLEDGE")
    assert res.is_failure
    err = res.unwrap_error()
    assert isinstance(err, AnomalyAlreadyResolvedError)
    assert err.code == "ANOMALY_ALREADY_RESOLVED"
    assert err.http_status == 409
    assert anm.state == AnomalyState.RESOLVED


# =============================================================================
# Cross-Tenant Boundary Enforcement (INV-TEN-001)
# =============================================================================

def test_cross_tenant_actor_rejected(sample_anomaly, beta_principal):
    """INV-TEN-001: Actor belonging to another tenant cannot transition this anomaly (HTTP 403)."""
    from revpilot.modules.analytics.lifecycle import AnomalyState

    anm = sample_anomaly
    res = anm.transition_to(AnomalyState.VALIDATED, beta_principal, "CROSS_TENANT_MUTATION")

    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "TENANCY_VIOLATION"
    assert err.http_status == 403
    assert anm.state == AnomalyState.DETECTED
