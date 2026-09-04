"""
RevPilot AI — Unit Tests for Hard Business Constraints & Budget Inviolability
Specification: docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md §1..§4
Specification: docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md §1.1 Invariant 2, §2 Step 4–7
Conforms to BR-005, FR-DEC-001, INV-COST-001, INV-TEN-001, and AC-007.
"""

from __future__ import annotations
from decimal import Decimal
import sys
from datetime import timedelta
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_constraints_module():
    """Ensure constraints module is cleaned between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.constraints"):
            sys.modules.pop(mod, None)


@pytest.fixture
def constraints_module():
    import revpilot.modules.constraints as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_corp")


@pytest.fixture
def base_intervention(constraints_module) -> constraints_module.CandidateIntervention:
    return constraints_module.CandidateIntervention(
        candidate_id="int_voucher_50",
        name="$50 Retention Voucher",
        action_type="SERVICE_CREDIT",
        estimated_cost_usd=Decimal("50.00"),
        eligible_tiers=["ENTERPRISE", "MID_MARKET"],
        max_frequency_days=14,
        risk_tier="LOW",
    )


@pytest.fixture
def base_budget_ledger(constraints_module, sample_tenant) -> constraints_module.BudgetLedgerEntry:
    return constraints_module.BudgetLedgerEntry(
        tenant_id=sample_tenant,
        ledger_date="2026-02-21",
        total_allocated_usd=Decimal("1000.00"),
        committed_expenditure_usd=Decimal("200.00"),
        remaining_balance_usd=Decimal("800.00"),
        version=1,
    )


def test_fully_compliant_candidate_passes(
    constraints_module, sample_tenant, base_intervention, base_budget_ledger
):
    """Candidate satisfying all 10 hard constraints is marked eligible."""
    now = UtcDateTime.now()
    req = constraints_module.ConstraintEvaluatorRequest(
        tenant_id=sample_tenant,
        customer_id="cust_1001",
        customer_tier="ENTERPRISE",
        intervention=base_intervention,
        current_time=now,
        budget_ledger=base_budget_ledger,
        active_capacity_count=2,
        max_capacity_limit=10,
        customer_history_timestamps=[UtcDateTime(now.value - timedelta(days=30))],
        quarterly_history_timestamps=[UtcDateTime(now.value - timedelta(days=30))],
        max_quarterly_frequency=3,
        customer_opt_out=False,
        is_excluded=False,
        incident_treated_count=10,
        max_blast_radius=500,
        feature_timestamp=UtcDateTime(now.value - timedelta(hours=2)),
        max_feature_staleness_hours=24,
    )

    outcome = constraints_module.evaluate_hard_constraints(req)

    assert outcome.is_eligible is True
    assert len(outcome.violated_constraints) == 0
    assert len(outcome.passed_constraints) == 10


def test_tenant_mismatch_violation(
    constraints_module, sample_tenant, base_intervention, base_budget_ledger
):
    """Different tenant in budget ledger triggers ERR_TENANT_MISMATCH."""
    now = UtcDateTime.now()
    req = constraints_module.ConstraintEvaluatorRequest(
        tenant_id=TenantId("tnt_other_tenant"),
        customer_id="cust_1001",
        customer_tier="ENTERPRISE",
        intervention=base_intervention,
        current_time=now,
        budget_ledger=base_budget_ledger,  # Owned by sample_tenant
        feature_timestamp=now,
    )

    outcome = constraints_module.evaluate_hard_constraints(req)
    assert outcome.is_eligible is False
    assert "ERR_TENANT_MISMATCH" in outcome.violated_constraints


def test_tier_ineligible_violation(
    constraints_module, sample_tenant, base_intervention, base_budget_ledger
):
    """Customer tier not in eligible_tiers triggers ERR_TIER_INELIGIBLE."""
    now = UtcDateTime.now()
    req = constraints_module.ConstraintEvaluatorRequest(
        tenant_id=sample_tenant,
        customer_id="cust_1001",
        customer_tier="FREE_TIER",  # Not in ["ENTERPRISE", "MID_MARKET"]
        intervention=base_intervention,
        current_time=now,
        budget_ledger=base_budget_ledger,
        feature_timestamp=now,
    )

    outcome = constraints_module.evaluate_hard_constraints(req)
    assert outcome.is_eligible is False
    assert "ERR_TIER_INELIGIBLE" in outcome.violated_constraints


def test_budget_exceeded_violation(
    constraints_module, sample_tenant, base_intervention
):
    """Intervention cost exceeding remaining budget triggers ERR_BUDGET_EXCEEDED."""
    now = UtcDateTime.now()
    exhausted_ledger = constraints_module.BudgetLedgerEntry(
        tenant_id=sample_tenant,
        ledger_date="2026-02-21",
        total_allocated_usd=Decimal("1000.00"),
        committed_expenditure_usd=Decimal("980.00"),
        remaining_balance_usd=Decimal("20.00"),  # Cost is $50.00
        version=2,
    )
    req = constraints_module.ConstraintEvaluatorRequest(
        tenant_id=sample_tenant,
        customer_id="cust_1001",
        customer_tier="ENTERPRISE",
        intervention=base_intervention,
        current_time=now,
        budget_ledger=exhausted_ledger,
        feature_timestamp=now,
    )

    outcome = constraints_module.evaluate_hard_constraints(req)
    assert outcome.is_eligible is False
    assert "ERR_BUDGET_EXCEEDED" in outcome.violated_constraints


def test_cooldown_and_frequency_cap_violations(
    constraints_module, sample_tenant, base_intervention, base_budget_ledger
):
    """Active cooldown and quarterly frequency caps trigger appropriate errors."""
    now = UtcDateTime.now()
    # Treated 5 days ago (cooldown is 14 days)
    recent_treatment = UtcDateTime(now.value - timedelta(days=5))

    req = constraints_module.ConstraintEvaluatorRequest(
        tenant_id=sample_tenant,
        customer_id="cust_1001",
        customer_tier="ENTERPRISE",
        intervention=base_intervention,
        current_time=now,
        budget_ledger=base_budget_ledger,
        customer_history_timestamps=[recent_treatment],
        quarterly_history_timestamps=[recent_treatment, recent_treatment, recent_treatment],
        max_quarterly_frequency=3,  # Already at max 3
        feature_timestamp=now,
    )

    outcome = constraints_module.evaluate_hard_constraints(req)
    assert outcome.is_eligible is False
    assert "ERR_COOLDOWN_ACTIVE" in outcome.violated_constraints
    assert "ERR_FREQUENCY_CAP_EXCEEDED" in outcome.violated_constraints


def test_consent_opt_out_and_exclusion_violations(
    constraints_module, sample_tenant, base_intervention, base_budget_ledger
):
    """Opt-out and legal exclusion trigger hard rejections."""
    now = UtcDateTime.now()
    req = constraints_module.ConstraintEvaluatorRequest(
        tenant_id=sample_tenant,
        customer_id="cust_1001",
        customer_tier="ENTERPRISE",
        intervention=base_intervention,
        current_time=now,
        budget_ledger=base_budget_ledger,
        customer_opt_out=True,
        is_excluded=True,
        feature_timestamp=now,
    )

    outcome = constraints_module.evaluate_hard_constraints(req)
    assert outcome.is_eligible is False
    assert "ERR_CUSTOMER_OPTED_OUT" in outcome.violated_constraints
    assert "ERR_CUSTOMER_EXCLUDED" in outcome.violated_constraints


def test_blast_radius_and_stale_features_violations(
    constraints_module, sample_tenant, base_intervention, base_budget_ledger
):
    """Incident blast radius ceiling and feature staleness trigger rejections."""
    now = UtcDateTime.now()
    req = constraints_module.ConstraintEvaluatorRequest(
        tenant_id=sample_tenant,
        customer_id="cust_1001",
        customer_tier="ENTERPRISE",
        intervention=base_intervention,
        current_time=now,
        budget_ledger=base_budget_ledger,
        incident_treated_count=500,  # Max 500 reached
        max_blast_radius=500,
        feature_timestamp=UtcDateTime(now.value - timedelta(hours=36)),  # 36h > 24h
        max_feature_staleness_hours=24,
    )

    outcome = constraints_module.evaluate_hard_constraints(req)
    assert outcome.is_eligible is False
    assert "ERR_BLAST_RADIUS_EXCEEDED" in outcome.violated_constraints
    assert "ERR_STALE_FEATURES" in outcome.violated_constraints


def test_filter_eligible_candidates_splitting(
    constraints_module, sample_tenant, base_intervention, base_budget_ledger
):
    """Verify filter_eligible_candidates properly partitions eligible from disqualified."""
    now = UtcDateTime.now()

    int_expensive = constraints_module.CandidateIntervention(
        candidate_id="int_expensive",
        name="Expensive Action",
        action_type="VIP_COMP",
        estimated_cost_usd=Decimal("5000.00"),  # Exceeds $800 balance
        eligible_tiers=["ENTERPRISE"],
        max_frequency_days=7,
        risk_tier="HIGH",
    )

    req_valid = constraints_module.ConstraintEvaluatorRequest(
        tenant_id=sample_tenant,
        customer_id="cust_valid",
        customer_tier="ENTERPRISE",
        intervention=base_intervention,
        current_time=now,
        budget_ledger=base_budget_ledger,
        feature_timestamp=now,
    )

    req_invalid = constraints_module.ConstraintEvaluatorRequest(
        tenant_id=sample_tenant,
        customer_id="cust_invalid",
        customer_tier="ENTERPRISE",
        intervention=int_expensive,
        current_time=now,
        budget_ledger=base_budget_ledger,
        feature_timestamp=now,
    )

    eligible, ineligible = constraints_module.filter_eligible_candidates([req_valid, req_invalid])

    assert len(eligible) == 1
    assert eligible[0].candidate_id == "int_voucher_50"
    assert "int_expensive" in ineligible
    assert "ERR_BUDGET_EXCEEDED" in ineligible["int_expensive"]


def test_in_memory_budget_ledger_atomic_reservation(constraints_module, sample_tenant):
    """Verify atomic ledger updates, OCC version incrementing, and overdraft prevention."""
    repo = constraints_module.InMemoryBudgetLedgerRepository()
    ledger = repo.init_ledger(sample_tenant, "2026-02-21", Decimal("500.00"))
    assert ledger.remaining_balance_usd == Decimal("500.00")
    assert ledger.version == 1

    # Successful reservation
    updated = repo.reserve_budget(sample_tenant, "2026-02-21", Decimal("200.00"))
    assert updated.remaining_balance_usd == Decimal("300.00")
    assert updated.committed_expenditure_usd == Decimal("200.00")
    assert updated.version == 2

    # Overdraft rejection
    with pytest.raises(constraints_module.ConstraintViolationError) as exc_info:
        repo.reserve_budget(sample_tenant, "2026-02-21", Decimal("350.00"))
    assert exc_info.value.code == "ERR_BUDGET_EXCEEDED"

    # Release funds
    released = repo.release_budget(sample_tenant, "2026-02-21", Decimal("100.00"))
    assert released.remaining_balance_usd == Decimal("400.00")
    assert released.committed_expenditure_usd == Decimal("100.00")
    assert released.version == 3
