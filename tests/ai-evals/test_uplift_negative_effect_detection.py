"""
RevPilot AI — Sleeping Dog and Negative Effect Rejection Test
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md §4, §5
Evaluation Gate: GATE-SLEEPING-DOGS (FR-ML-003)
Negative Uplift Detection >= 95%:
  - Identifies negative effect cohort (tau < -0.05).
  - Strictly prevents treatment allocation (0% allocation to sleeping dogs).
"""

from __future__ import annotations
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_modules():
    """Clean uplift, constraint, and decision modules between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if (
            mod.startswith("revpilot.modules.uplift")
            or mod.startswith("revpilot.modules.constraints")
            or mod.startswith("revpilot.modules.decision")
        ):
            sys.modules.pop(mod, None)


@pytest.fixture
def uplift_module():
    import revpilot.modules.uplift as mod
    return mod


@pytest.fixture
def decision_module():
    import revpilot.modules.decision as mod
    return mod


@pytest.fixture
def constraints_module():
    import revpilot.modules.constraints as mod
    return mod


def test_sleeping_dog_detection_and_treatment_prevention(
    uplift_module, decision_module, constraints_module
):
    """
    Evaluates GATE-SLEEPING-DOGS:
    1. Detection rate of negative-effect cohort >= 95%.
    2. Decision engine prevents treatment allocation to sleeping dogs (allocation = 0).
    """
    tenant_id = TenantId("tnt_retention_gov")
    now = UtcDateTime.now()

    # 1. Test 100 synthetic sleeping dogs with true negative uplift (tau in [-0.20, -0.06])
    detected_sleeping_dogs = 0
    total_sleeping_dogs = 100

    for i in range(total_sleeping_dogs):
        # Negative uplift with varying baseline churn risk
        tau_val = -0.06 - (i % 15) * 0.01  # -0.06 down to -0.20
        churn_risk = 0.20 + (i % 50) * 0.01

        segment = uplift_module.classify_persuadability(
            cate_estimate=tau_val,
            churn_risk=churn_risk,
        )
        if segment == uplift_module.PersuadabilitySegment.SLEEPING_DOG:
            detected_sleeping_dogs += 1

    detection_rate = detected_sleeping_dogs / total_sleeping_dogs
    # GATE-SLEEPING-DOGS: Detection rate >= 95%
    assert detection_rate >= 0.95, f"Sleeping dog detection rate {detection_rate:.2%} < 95%"

    # 2. Decision Engine Treatment Rejection Barrier:
    # Attempting to allocate an intervention to a sleeping dog customer
    engine = decision_module.DecisionEngine()

    budget_ledger = constraints_module.BudgetLedgerEntry(
        tenant_id=tenant_id,
        ledger_date="2026-09-04",
        total_allocated_usd=Decimal("10000.00"),
        committed_expenditure_usd=Decimal("0.00"),
        remaining_balance_usd=Decimal("10000.00"),
        version=1,
    )

    # Candidate with negative CATE (sleeping dog reaction)
    sleeping_dog_candidate = decision_module.DecisionCandidate(
        candidate_id="cand_unsolicited_call",
        name="Aggressive Sales Outreach",
        action_type="OUTREACH",
        estimated_cost_usd=Decimal("25.00"),
        eligible_tiers=["ENTERPRISE"],
        max_frequency_days=7,
        risk_tier="HIGH",
        expected_cate=-0.12,  # Increases churn by 12%!
        cate_standard_error=0.01,
        overlap_satisfied=True,
    )

    req = decision_module.DecisionRequest(
        request_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        customer_id="cust_sleeping_dog_01",
        customer_tier="ENTERPRISE",
        as_of_time=now,
        candidates=[sleeping_dog_candidate],
        customer_arr_usd=Decimal("20000.00"),
        budget_ledger=budget_ledger,
        feature_timestamp=now,
    )

    rec = engine.execute_decision_pipeline(req)

    # Must ABSTAIN: Zero treatment allocation to sleeping dogs (FR-ML-003)
    assert rec.status == "ABSTAINED"
    assert rec.selected_candidate_id is None
    assert rec.expected_utility_usd == Decimal("0.0")
