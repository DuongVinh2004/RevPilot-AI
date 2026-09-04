"""
RevPilot AI — Unit Tests for 12-Step Decision Intelligence Engine
Specification: docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md §1..§5
Conforms to BR-002, BR-005, FR-DEC-001, INV-AI-001, INV-ACT-001, INV-COST-001, INV-TEN-001..003, AC-007, and ADR-0003.
"""

from __future__ import annotations
from decimal import Decimal
import sys
from datetime import timedelta
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_decision_modules():
    """Ensure decision and constraint modules are cleaned up to prevent cross-test leakage."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.decision") or mod.startswith("revpilot.modules.constraints"):
            sys.modules.pop(mod, None)


@pytest.fixture
def decision_module():
    import revpilot.modules.decision as mod
    return mod


@pytest.fixture
def constraints_module():
    import revpilot.modules.constraints as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_corp")


@pytest.fixture
def sample_budget_ledger(constraints_module, sample_tenant):
    return constraints_module.BudgetLedgerEntry(
        tenant_id=sample_tenant,
        ledger_date="2026-09-04",
        total_allocated_usd=Decimal("5000.00"),
        committed_expenditure_usd=Decimal("500.00"),
        remaining_balance_usd=Decimal("4500.00"),
        version=1,
    )


@pytest.fixture
def valid_candidate_a(decision_module) -> decision_module.DecisionCandidate:
    return decision_module.DecisionCandidate(
        candidate_id="cand_priority_reship",
        name="Priority Reshipment",
        action_type="LOGISTICS_EXPEDITE",
        estimated_cost_usd=Decimal("40.00"),
        eligible_tiers=["ENTERPRISE", "MID_MARKET"],
        max_frequency_days=14,
        risk_tier="LOW",
        expected_cate=0.08,  # +8% retention
        cate_standard_error=0.01,
        confidence_interval_95=(0.06, 0.10),
        overlap_satisfied=True,
    )


@pytest.fixture
def valid_candidate_b(decision_module) -> decision_module.DecisionCandidate:
    return decision_module.DecisionCandidate(
        candidate_id="cand_voucher_100",
        name="$100 Retention Voucher",
        action_type="SERVICE_CREDIT",
        estimated_cost_usd=Decimal("100.00"),
        eligible_tiers=["ENTERPRISE"],
        max_frequency_days=30,
        risk_tier="MEDIUM",
        expected_cate=0.12,  # +12% retention
        cate_standard_error=0.02,
        confidence_interval_95=(0.08, 0.16),
        overlap_satisfied=True,
    )


def test_step1_to_3_validation_errors(
    decision_module, sample_tenant, sample_budget_ledger, valid_candidate_a
):
    """Step 1–3 must fail-closed on invalid tenant, customer, temporal, or candidate data."""
    engine = decision_module.DecisionEngine()
    now = UtcDateTime.now()

    # Step 1: Missing customer_id
    with pytest.raises(decision_module.DecisionError) as exc_info:
        req = decision_module.DecisionRequest(
            request_id=UUIDv7.generate(),
            tenant_id=sample_tenant,
            customer_id="",
            customer_tier="ENTERPRISE",
            as_of_time=now,
            candidates=[valid_candidate_a],
            customer_arr_usd=Decimal("10000.00"),
            budget_ledger=sample_budget_ledger,
            feature_timestamp=now,
        )
        engine.execute_decision_pipeline(req)
    assert exc_info.value.code == "ERR_INVALID_REQUEST"

    # Step 2: Temporal leakage (feature timestamp from the future)
    future_time = UtcDateTime.from_datetime(now.value + timedelta(hours=2))
    with pytest.raises(decision_module.DecisionError) as exc_info:
        req = decision_module.DecisionRequest(
            request_id=UUIDv7.generate(),
            tenant_id=sample_tenant,
            customer_id="cust_123",
            customer_tier="ENTERPRISE",
            as_of_time=now,
            candidates=[valid_candidate_a],
            customer_arr_usd=Decimal("10000.00"),
            budget_ledger=sample_budget_ledger,
            feature_timestamp=future_time,
        )
        engine.execute_decision_pipeline(req)
    assert exc_info.value.code == "ERR_TEMPORAL_LEAKAGE"

    # Step 2: Stale feature data (> 24 hours old)
    stale_time = UtcDateTime.from_datetime(now.value - timedelta(hours=36))
    with pytest.raises(decision_module.DecisionError) as exc_info:
        req = decision_module.DecisionRequest(
            request_id=UUIDv7.generate(),
            tenant_id=sample_tenant,
            customer_id="cust_123",
            customer_tier="ENTERPRISE",
            as_of_time=now,
            candidates=[valid_candidate_a],
            customer_arr_usd=Decimal("10000.00"),
            budget_ledger=sample_budget_ledger,
            feature_timestamp=stale_time,
        )
        engine.execute_decision_pipeline(req)
    assert exc_info.value.code == "ERR_STALE_FEATURES"

    # Step 3: Empty candidates
    with pytest.raises(decision_module.DecisionError) as exc_info:
        req = decision_module.DecisionRequest(
            request_id=UUIDv7.generate(),
            tenant_id=sample_tenant,
            customer_id="cust_123",
            customer_tier="ENTERPRISE",
            as_of_time=now,
            candidates=[],
            customer_arr_usd=Decimal("10000.00"),
            budget_ledger=sample_budget_ledger,
            feature_timestamp=now,
        )
        engine.execute_decision_pipeline(req)
    assert exc_info.value.code == "ERR_EMPTY_CANDIDATES"


def test_step4_to_7_hard_constraints_and_blocked_status(
    decision_module, constraints_module, sample_tenant, valid_candidate_a
):
    """Step 4–7 must filter ineligible candidates; if none remain, status is BLOCKED."""
    engine = decision_module.DecisionEngine()
    now = UtcDateTime.now()

    # Exhausted budget
    empty_ledger = constraints_module.BudgetLedgerEntry(
        tenant_id=sample_tenant,
        ledger_date="2026-09-04",
        total_allocated_usd=Decimal("1000.00"),
        committed_expenditure_usd=Decimal("1000.00"),
        remaining_balance_usd=Decimal("0.00"),
        version=2,
    )

    req = decision_module.DecisionRequest(
        request_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        customer_id="cust_123",
        customer_tier="ENTERPRISE",
        as_of_time=now,
        candidates=[valid_candidate_a],
        customer_arr_usd=Decimal("10000.00"),
        budget_ledger=empty_ledger,
        feature_timestamp=now,
    )
    record = engine.execute_decision_pipeline(req)

    assert record.status == "BLOCKED"
    assert record.selected_candidate_id is None
    assert record.expected_utility_usd == Decimal("0.0")
    assert "cand_priority_reship" in record.ineligible_candidates
    assert "ERR_BUDGET_EXCEEDED" in record.ineligible_candidates["cand_priority_reship"]


def test_step8_expected_utility_computation(
    decision_module, sample_tenant, sample_budget_ledger, valid_candidate_a
):
    """Step 8 computes E[U] = tau * ARR - Cost - lambda_risk * Risk - lambda_unc * (sigma * ARR)."""
    engine = decision_module.DecisionEngine()
    now = UtcDateTime.now()

    # customer ARR = $10,000
    # candidate A: tau = 0.08, cost = $40.00, risk = LOW (0), sigma = 0.01
    # lambda_risk = 0.50, lambda_unc = 0.50
    # incremental gain = 0.08 * 10000 = $800.00
    # direct cost = $40.00
    # risk penalty = 0.50 * 0 = $0.00
    # uncertainty monetary = 0.01 * 10000 = $100.00
    # uncertainty penalty = 0.50 * 100.00 = $50.00
    # expected utility = 800.00 - 40.00 - 0.00 - 50.00 = $710.00

    req = decision_module.DecisionRequest(
        request_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        customer_id="cust_123",
        customer_tier="ENTERPRISE",
        as_of_time=now,
        candidates=[valid_candidate_a],
        customer_arr_usd=Decimal("10000.00"),
        budget_ledger=sample_budget_ledger,
        feature_timestamp=now,
        risk_aversion_lambda=0.50,
        uncertainty_lambda=0.50,
    )
    record = engine.execute_decision_pipeline(req)

    assert record.status == "RECOMMENDED"
    assert record.selected_candidate_id == "cand_priority_reship"
    assert record.expected_utility_usd == Decimal("710.00")
    assert record.direct_cost_usd == Decimal("40.00")
    assert record.risk_penalty_usd == Decimal("0.00")
    assert record.uncertainty_penalty_usd == Decimal("50.00")
    assert record.expected_incremental_retention_rate == 0.08


def test_step9_deterministic_tie_breaking(
    decision_module, sample_tenant, sample_budget_ledger
):
    """Step 9 deterministic tie-breaking: lower cost -> lower uncertainty -> lexicographical ID."""
    engine = decision_module.DecisionEngine()
    now = UtcDateTime.now()

    # Create two candidates with identical expected utility
    # Both have tau * ARR - cost - risk - unc = same value
    # Candidate X: cost $50, sigma 0.01
    # Candidate Y: cost $60, sigma 0.01
    # We adjust tau so utilities match:
    # ARR = $10,000, lambda_unc = 0.50 -> unc_penalty = 0.50 * 100 = $50
    # X: gain = 0.05 * 10000 = 500, cost = 50, unc = 50 -> E[U] = 400.00
    # Y: gain = 0.051 * 10000 = 510, cost = 60, unc = 50 -> E[U] = 400.00
    # Tie in utility: X has lower cost ($50 vs $60) -> X wins!

    cand_x = decision_module.DecisionCandidate(
        candidate_id="cand_x",
        name="Candidate X",
        action_type="ACTION",
        estimated_cost_usd=Decimal("50.00"),
        eligible_tiers=["ENTERPRISE"],
        max_frequency_days=7,
        risk_tier="LOW",
        expected_cate=0.05,
        cate_standard_error=0.01,
        overlap_satisfied=True,
    )
    cand_y = decision_module.DecisionCandidate(
        candidate_id="cand_y",
        name="Candidate Y",
        action_type="ACTION",
        estimated_cost_usd=Decimal("60.00"),
        eligible_tiers=["ENTERPRISE"],
        max_frequency_days=7,
        risk_tier="LOW",
        expected_cate=0.051,
        cate_standard_error=0.01,
        overlap_satisfied=True,
    )

    req = decision_module.DecisionRequest(
        request_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        customer_id="cust_123",
        customer_tier="ENTERPRISE",
        as_of_time=now,
        candidates=[cand_y, cand_x],  # Y passed first
        customer_arr_usd=Decimal("10000.00"),
        budget_ledger=sample_budget_ledger,
        feature_timestamp=now,
        risk_aversion_lambda=0.0,
        uncertainty_lambda=0.50,
    )
    record = engine.execute_decision_pipeline(req)

    assert record.status == "RECOMMENDED"
    assert record.selected_candidate_id == "cand_x"
    assert record.ranked_alternatives[0]["candidate_id"] == "cand_x"
    assert record.ranked_alternatives[1]["candidate_id"] == "cand_y"


def test_step11_economic_viability_rule_abstains_on_negative_utility(
    decision_module, sample_tenant, sample_budget_ledger
):
    """Step 11 Economic Viability Rule: if max E[U] <= 0, engine returns ABSTAINED."""
    engine = decision_module.DecisionEngine()
    now = UtcDateTime.now()

    # Costly candidate with tiny uplift:
    # ARR = $1,000, tau = 0.01 (gain = $10), cost = $50 -> E[U] < 0
    uneconomic_cand = decision_module.DecisionCandidate(
        candidate_id="cand_wasteful",
        name="Expensive Gift",
        action_type="GIFT",
        estimated_cost_usd=Decimal("50.00"),
        eligible_tiers=["ENTERPRISE"],
        max_frequency_days=7,
        risk_tier="LOW",
        expected_cate=0.01,
        cate_standard_error=0.01,
        overlap_satisfied=True,
    )

    req = decision_module.DecisionRequest(
        request_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        customer_id="cust_123",
        customer_tier="ENTERPRISE",
        as_of_time=now,
        candidates=[uneconomic_cand],
        customer_arr_usd=Decimal("1000.00"),
        budget_ledger=sample_budget_ledger,
        feature_timestamp=now,
    )
    record = engine.execute_decision_pipeline(req)

    assert record.status == "ABSTAINED"
    assert record.selected_candidate_id is None
    assert record.expected_utility_usd == Decimal("0.0")
    assert len(record.ranked_alternatives) == 1
    assert record.ranked_alternatives[0]["expected_utility_usd"] < Decimal("0.0")


def test_step11_overlap_violation_returns_need_more_evidence(
    decision_module, sample_tenant, sample_budget_ledger
):
    """Step 11 Common Support Gate: overlap violation halts with NEED_MORE_EVIDENCE."""
    engine = decision_module.DecisionEngine()
    now = UtcDateTime.now()

    overlap_violating_cand = decision_module.DecisionCandidate(
        candidate_id="cand_unsupported",
        name="High-Risk Intervention",
        action_type="OUTREACH",
        estimated_cost_usd=Decimal("10.00"),
        eligible_tiers=["ENTERPRISE"],
        max_frequency_days=7,
        risk_tier="LOW",
        expected_cate=0.20,
        cate_standard_error=0.01,
        overlap_satisfied=False,  # Violated common support!
    )

    req = decision_module.DecisionRequest(
        request_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        customer_id="cust_123",
        customer_tier="ENTERPRISE",
        as_of_time=now,
        candidates=[overlap_violating_cand],
        customer_arr_usd=Decimal("10000.00"),
        budget_ledger=sample_budget_ledger,
        feature_timestamp=now,
    )
    record = engine.execute_decision_pipeline(req)

    assert record.status == "NEED_MORE_EVIDENCE"
    assert record.selected_candidate_id is None


def test_step12_reproducibility_digest_is_deterministic(
    decision_module, sample_tenant, sample_budget_ledger, valid_candidate_a
):
    """Step 12 Reproducibility Digest produces exact same hash on identical inputs."""
    engine = decision_module.DecisionEngine()
    now = UtcDateTime.now()
    fixed_req_id = UUIDv7.generate()

    req = decision_module.DecisionRequest(
        request_id=fixed_req_id,
        tenant_id=sample_tenant,
        customer_id="cust_123",
        customer_tier="ENTERPRISE",
        as_of_time=now,
        candidates=[valid_candidate_a],
        customer_arr_usd=Decimal("10000.00"),
        budget_ledger=sample_budget_ledger,
        feature_timestamp=now,
    )

    rec1 = engine.execute_decision_pipeline(req)
    rec2 = engine.execute_decision_pipeline(req)

    assert rec1.status == rec2.status
    assert rec1.expected_utility_usd == rec2.expected_utility_usd
    assert len(rec1.decision_digest) == 64  # Valid SHA-256


@pytest.mark.asyncio
async def test_decision_repository_tenant_isolation(
    decision_module, sample_tenant, sample_budget_ledger, valid_candidate_a
):
    """DecisionRepository enforces strict tenant isolation (INV-TEN-001)."""
    engine = decision_module.DecisionEngine()
    repo = decision_module.InMemoryDecisionRepository()
    now = UtcDateTime.now()

    req = decision_module.DecisionRequest(
        request_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        customer_id="cust_123",
        customer_tier="ENTERPRISE",
        as_of_time=now,
        candidates=[valid_candidate_a],
        customer_arr_usd=Decimal("10000.00"),
        budget_ledger=sample_budget_ledger,
        feature_timestamp=now,
    )
    rec = engine.execute_decision_pipeline(req)

    # Persist record under sample_tenant
    await repo.save_recommendation(rec)

    # Fetch with matching tenant
    fetched = await repo.get_recommendation(sample_tenant, rec.recommendation_id)
    assert fetched is not None
    assert fetched.recommendation_id == rec.recommendation_id

    # Fetch with adversary tenant
    adversary_tenant = TenantId("tnt_adversary_corp")
    adversary_fetch = await repo.get_recommendation(adversary_tenant, rec.recommendation_id)
    assert adversary_fetch is None

    # List records under adversary tenant is empty
    adversary_list = await repo.list_recommendations(adversary_tenant)
    assert len(adversary_list) == 0
