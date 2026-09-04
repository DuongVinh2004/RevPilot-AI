"""
RevPilot AI — Uplift Overlap and Common Support Diagnostics Test
Specification: docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md §4, §5
Evaluation Gate: GATE-UPLIFT-OVERLAP (AC-006)
100% halts with ERR_OVERLAP_VIOLATION on unrepresented covariate regions.
"""

from __future__ import annotations
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_modules():
    """Clean modules between test runs."""
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


def test_uplift_overlap_violation_estimator_halt(uplift_module):
    """
    Uplift estimator must fail-closed with ERR_OVERLAP_VIOLATION
    when covariate region lacks common support across treatment/control.
    """
    # Only 1 treated sample (< 2 samples in treated partition)
    X_train = [[1.0], [2.0], [3.0], [4.0]]
    T_train = [0, 0, 0, 1]  # Only one treated
    Y_train = [0.1, 0.2, 0.3, 0.4]

    with pytest.raises(uplift_module.UpliftError) as exc_info:
        uplift_module.estimate_t_learner_cate(
            X_train=X_train,
            T_train=T_train,
            Y_train=Y_train,
            X_predict=[[2.5]],
        )
    assert exc_info.value.code == "ERR_OVERLAP_VIOLATION"


def test_uplift_overlap_violation_decision_engine_halts(
    decision_module, constraints_module
):
    """
    Decision engine must return NEED_MORE_EVIDENCE when candidate
    violates common support (overlap_satisfied = False).
    """
    tenant_id = TenantId("tnt_overlap_corp")
    now = UtcDateTime.now()

    engine = decision_module.DecisionEngine()

    budget_ledger = constraints_module.BudgetLedgerEntry(
        tenant_id=tenant_id,
        ledger_date="2026-09-04",
        total_allocated_usd=Decimal("5000.00"),
        committed_expenditure_usd=Decimal("0.00"),
        remaining_balance_usd=Decimal("5000.00"),
        version=1,
    )

    unsupported_candidate = decision_module.DecisionCandidate(
        candidate_id="cand_unsupported_treatment",
        name="Experimental Pricing Discount",
        action_type="DISCOUNT",
        estimated_cost_usd=Decimal("50.00"),
        eligible_tiers=["ENTERPRISE"],
        max_frequency_days=7,
        risk_tier="LOW",
        expected_cate=0.15,
        cate_standard_error=0.01,
        overlap_satisfied=False,  # Violated common support!
    )

    req = decision_module.DecisionRequest(
        request_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        customer_id="cust_overlap_01",
        customer_tier="ENTERPRISE",
        as_of_time=now,
        candidates=[unsupported_candidate],
        customer_arr_usd=Decimal("15000.00"),
        budget_ledger=budget_ledger,
        feature_timestamp=now,
    )

    rec = engine.execute_decision_pipeline(req)

    # GATE-UPLIFT-OVERLAP: Halts and outputs NEED_MORE_EVIDENCE
    assert rec.status == "NEED_MORE_EVIDENCE"
    assert rec.selected_candidate_id is None
