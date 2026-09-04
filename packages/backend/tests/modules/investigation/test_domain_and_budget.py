"""
RevPilot AI — Investigation Domain and Budget Unit Tests (Phase 03)
Verifies AC-P03-001-01, AC-P03-001-02, INV-WF-001, INV-COST-001, INV-TEN-001..002, and INV-DATA-001.
"""

from __future__ import annotations
import sys
from decimal import Decimal
import pytest

from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.investigation.domain.models import (
    Investigation,
    InvestigationStatus,
    InvestigationScope,
    InvestigationManifest,
    BudgetState,
)
from revpilot.modules.investigation.domain.state_machine import (
    transition_investigation_state,
)
from revpilot.modules.investigation.domain.errors import (
    InvalidStateTransitionError,
    BudgetExceededError,
    TemporalValidationException,
)


@pytest.fixture(autouse=True)
def _isolate_investigation_module():
    """Ensure investigation module is clean between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.investigation"):
            sys.modules.pop(mod, None)


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha")


@pytest.fixture
def principal_analyst() -> PrincipalId:
    return PrincipalId("usr_analyst_001")


@pytest.fixture
def valid_temporal_window() -> tuple[UtcDateTime, UtcDateTime, UtcDateTime]:
    start = UtcDateTime.from_iso("2026-05-10T00:00:00.000000Z")
    end = UtcDateTime.from_iso("2026-05-17T00:00:00.000000Z")
    as_of = UtcDateTime.from_iso("2026-05-18T00:00:00.000000Z")
    return start, end, as_of


# =============================================================================
# AC-P03-001-01: Lifecycle State Machine Transitions
# =============================================================================

def test_investigation_status_enum_contains_all_nine_states():
    """AC-P03-001-01: Verify all 9 InvestigationStatus states defined per TEMPORAL-WORKFLOW-SPEC.md §4."""
    expected_states = {
        "INITIALIZING",
        "PLANNING",
        "GATHERING_EVIDENCE",
        "VERIFYING",
        "COMPLETED",
        "NEED_MORE_EVIDENCE",
        "PAUSED",
        "CANCELLED",
        "FAILED",
    }
    actual_states = {s.value for s in InvestigationStatus}
    assert actual_states == expected_states


def test_valid_investigation_lifecycle_progression():
    """AC-P03-001-01: Happy path: INITIALIZING -> PLANNING -> GATHERING_EVIDENCE -> VERIFYING -> COMPLETED."""
    s1 = transition_investigation_state(
        InvestigationStatus.INITIALIZING,
        InvestigationStatus.PLANNING,
    )
    assert s1.is_success
    assert s1.unwrap() == InvestigationStatus.PLANNING

    s2 = transition_investigation_state(
        InvestigationStatus.PLANNING,
        InvestigationStatus.GATHERING_EVIDENCE,
    )
    assert s2.is_success
    assert s2.unwrap() == InvestigationStatus.GATHERING_EVIDENCE

    s3 = transition_investigation_state(
        InvestigationStatus.GATHERING_EVIDENCE,
        InvestigationStatus.VERIFYING,
    )
    assert s3.is_success
    assert s3.unwrap() == InvestigationStatus.VERIFYING

    s4 = transition_investigation_state(
        InvestigationStatus.VERIFYING,
        InvestigationStatus.COMPLETED,
    )
    assert s4.is_success
    assert s4.unwrap() == InvestigationStatus.COMPLETED


def test_valid_pause_and_resume_transitions():
    """AC-P03-001-01: Investigation can pause from active state and resume to prior state."""
    # Pause from GATHERING_EVIDENCE
    pause_res = transition_investigation_state(
        InvestigationStatus.GATHERING_EVIDENCE,
        InvestigationStatus.PAUSED,
    )
    assert pause_res.is_success
    assert pause_res.unwrap() == InvestigationStatus.PAUSED

    # Resume back to GATHERING_EVIDENCE
    resume_res = transition_investigation_state(
        InvestigationStatus.PAUSED,
        InvestigationStatus.GATHERING_EVIDENCE,
        prior_active_state=InvestigationStatus.GATHERING_EVIDENCE,
    )
    assert resume_res.is_success
    assert resume_res.unwrap() == InvestigationStatus.GATHERING_EVIDENCE

    # Cancel while paused
    cancel_res = transition_investigation_state(
        InvestigationStatus.PAUSED,
        InvestigationStatus.CANCELLED,
    )
    assert cancel_res.is_success
    assert cancel_res.unwrap() == InvestigationStatus.CANCELLED


def test_valid_verifier_loop_and_need_more_evidence():
    """AC-P03-001-01: Verifier can loop back for more evidence or conclude with NEED_MORE_EVIDENCE."""
    loop_res = transition_investigation_state(
        InvestigationStatus.VERIFYING,
        InvestigationStatus.GATHERING_EVIDENCE,
    )
    assert loop_res.is_success
    assert loop_res.unwrap() == InvestigationStatus.GATHERING_EVIDENCE

    gap_res = transition_investigation_state(
        InvestigationStatus.VERIFYING,
        InvestigationStatus.NEED_MORE_EVIDENCE,
    )
    assert gap_res.is_success
    assert gap_res.unwrap() == InvestigationStatus.NEED_MORE_EVIDENCE


def test_illegal_transitions_fail_closed_with_409():
    """AC-P03-001-01: Illegal jumps must return Err(ERR_INVALID_STATE_TRANSITION, 409)."""
    # Direct jump INITIALIZING -> COMPLETED
    res1 = transition_investigation_state(
        InvestigationStatus.INITIALIZING,
        InvestigationStatus.COMPLETED,
    )
    assert res1.is_failure
    err1 = res1.unwrap_error()
    assert isinstance(err1, InvalidStateTransitionError)
    assert err1.code == "ERR_INVALID_STATE_TRANSITION"
    assert err1.http_status == 409

    # Terminal state mutation: COMPLETED -> PLANNING
    res2 = transition_investigation_state(
        InvestigationStatus.COMPLETED,
        InvestigationStatus.PLANNING,
    )
    assert res2.is_failure
    assert res2.unwrap_error().code == "ERR_INVALID_STATE_TRANSITION"

    # Terminal state mutation: NEED_MORE_EVIDENCE -> VERIFYING
    res3 = transition_investigation_state(
        InvestigationStatus.NEED_MORE_EVIDENCE,
        InvestigationStatus.VERIFYING,
    )
    assert res3.is_failure

    # Terminal state mutation: CANCELLED -> PLANNING
    res4 = transition_investigation_state(
        InvestigationStatus.CANCELLED,
        InvestigationStatus.PLANNING,
    )
    assert res4.is_failure

    # Terminal state mutation: FAILED -> INITIALIZING
    res5 = transition_investigation_state(
        InvestigationStatus.FAILED,
        InvestigationStatus.INITIALIZING,
    )
    assert res5.is_failure


# =============================================================================
# AC-P03-001-02: BudgetState and Resource Quota Contracts
# =============================================================================

def test_budget_state_defaults_and_incremental_spend():
    """AC-P03-001-02: Verify default allocations ($2.00 allocated, $5.00 hard stop) and spend tracking."""
    budget = BudgetState()
    assert budget.allocated_usd == Decimal("2.00")
    assert budget.spent_usd == Decimal("0.00")
    assert budget.hard_stop_usd == Decimal("5.00")
    assert budget.allocated_tokens == 100_000
    assert budget.spent_tokens == 0
    assert budget.allocated_tool_calls == 20
    assert budget.spent_tool_calls == 0

    # Record valid spend within bounds
    budget.record_spend(usd=Decimal("1.50"), tokens=25_000, tool_calls=5)
    assert budget.spent_usd == Decimal("1.50")
    assert budget.spent_tokens == 25_000
    assert budget.spent_tool_calls == 5

    # Record additional spend up to exact hard stop limit ($5.00)
    budget.record_spend(usd=Decimal("3.50"), tokens=50_000, tool_calls=10)
    assert budget.spent_usd == Decimal("5.00")


def test_budget_state_exceeding_hard_stop_raises_429():
    """AC-P03-001-02: Spend exceeding $5.00 USD hard stop limit halts and raises ERR_BUDGET_EXCEEDED (429)."""
    budget = BudgetState()
    budget.record_spend(usd=Decimal("4.50"), tokens=50_000, tool_calls=10)

    # Attempting to spend $0.51 (bringing total to $5.01 > $5.00) must fail closed
    with pytest.raises(BudgetExceededError) as exc_info:
        budget.record_spend(usd=Decimal("0.51"), tokens=5_000, tool_calls=1)

    err = exc_info.value
    assert err.code == "ERR_BUDGET_EXCEEDED"
    assert err.http_status == 429
    assert "hard stop limit" in err.message.lower()
    assert budget.spent_usd == Decimal("4.50")  # Prior spend remains unchanged


def test_budget_state_constructor_rejects_initial_overspend():
    """AC-P03-001-02: Initializing BudgetState with spent_usd > hard_stop_usd raises BudgetExceededError."""
    with pytest.raises(BudgetExceededError) as exc_info:
        BudgetState(spent_usd=Decimal("5.50"), hard_stop_usd=Decimal("5.00"))
    assert exc_info.value.code == "ERR_BUDGET_EXCEEDED"


# =============================================================================
# Investigation Entity & Temporal Anti-Leakage Contracts
# =============================================================================

def test_investigation_aggregate_initialization(
    tenant_alpha,
    principal_analyst,
    valid_temporal_window,
):
    """Verify valid initialization of Investigation aggregate root."""
    start, end, as_of = valid_temporal_window
    inv = Investigation(
        investigation_id="inv_test_001",
        tenant_id=tenant_alpha,
        principal_id=principal_analyst,
        metric_name="cancellation_rate",
        anomaly_id="anm_test_001",
        scope=InvestigationScope(region="US-MIDWEST", tier="ENTERPRISE"),
        window_start=start,
        window_end=end,
        as_of_time=as_of,
        status=InvestigationStatus.INITIALIZING,
        budget=BudgetState(),
    )
    assert inv.investigation_id == "inv_test_001"
    assert inv.tenant_id == tenant_alpha
    assert inv.principal_id == principal_analyst
    assert inv.status == InvestigationStatus.INITIALIZING
    assert inv.scope.region == "US-MIDWEST"
    assert inv.budget.allocated_usd == Decimal("2.00")


def test_investigation_temporal_leakage_rejected(
    tenant_alpha,
    principal_analyst,
):
    """Verify INV-DATA-001: window_end > as_of_time raises ERR_TEMPORAL_LEAKAGE (400)."""
    start = UtcDateTime.from_iso("2026-05-10T00:00:00.000000Z")
    end = UtcDateTime.from_iso("2026-05-20T00:00:00.000000Z")
    as_of = UtcDateTime.from_iso("2026-05-18T00:00:00.000000Z")  # Past cutoff!

    with pytest.raises(TemporalValidationException) as exc_info:
        Investigation(
            investigation_id="inv_leak_001",
            tenant_id=tenant_alpha,
            principal_id=principal_analyst,
            metric_name="cancellation_rate",
            window_start=start,
            window_end=end,
            as_of_time=as_of,
        )

    err = exc_info.value
    assert err.code == "ERR_TEMPORAL_LEAKAGE"
    assert err.http_status == 400
    assert "exceeds as_of_time" in err.message


def test_investigation_manifest_contract(tenant_alpha):
    """Verify InvestigationManifest fields and cryptographic digest container."""
    now = UtcDateTime.now()
    manifest = InvestigationManifest(
        investigation_id="inv_manifest_001",
        tenant_id=tenant_alpha,
        top_hypothesis_id="hypo_carrier_collapse",
        bundle_digest="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        cogs_usd=Decimal("1.45"),
        duration_seconds=142,
        sealed_at=now,
    )
    assert manifest.investigation_id == "inv_manifest_001"
    assert manifest.tenant_id == tenant_alpha
    assert manifest.top_hypothesis_id == "hypo_carrier_collapse"
    assert manifest.bundle_digest.startswith("sha256:")
    assert manifest.cogs_usd == Decimal("1.45")
    assert manifest.duration_seconds == 142
    assert manifest.sealed_at == now
