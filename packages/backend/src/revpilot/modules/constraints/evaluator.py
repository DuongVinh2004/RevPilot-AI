"""
RevPilot AI — Hard Business Constraints Evaluator
Specification: docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md §2, §3
Specification: docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md §1.1, §2 Step 4–7
Conforms to BR-005, FR-DEC-001, INV-COST-001, INV-TEN-001, NFR-COST-001, and AC-007.
"""

from __future__ import annotations
from typing import Optional

from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.constraints.domain import (
    CandidateIntervention,
    ConstraintEvaluatorRequest,
    ConstraintEvaluationOutcome,
    ConstraintViolationError,
)


def evaluate_hard_constraints(
    request: ConstraintEvaluatorRequest,
) -> ConstraintEvaluationOutcome:
    """
    Step 4–7: Pre-Optimization Filtering over all 10 hard business constraints.
    Returns audit outcome documenting eligibility, passed constraints, and violations.
    Fails closed: violation of any constraint disqualifies candidate (AC-007).
    """
    passed: list[str] = []
    violated: list[str] = []

    # 1. Multi-Tenant Boundary
    if str(request.tenant_id) != str(request.budget_ledger.tenant_id):
        violated.append("ERR_TENANT_MISMATCH")
    else:
        passed.append("TENANT_SCOPE_VALID")

    # 2. Tier Eligibility
    if request.customer_tier not in request.intervention.eligible_tiers:
        violated.append("ERR_TIER_INELIGIBLE")
    else:
        passed.append("TIER_ELIGIBILITY_VALID")

    # 3. Monetary Budget Inviolability (INV-COST-001)
    if request.budget_ledger.remaining_balance_usd < request.intervention.estimated_cost_usd:
        violated.append("ERR_BUDGET_EXCEEDED")
    else:
        passed.append("BUDGET_REMAINING_VALID")

    # 4. Operational Dispatch Capacity
    if request.active_capacity_count >= request.max_capacity_limit:
        violated.append("ERR_CAPACITY_EXCEEDED")
    else:
        passed.append("CAPACITY_AVAILABLE_VALID")

    # 5. Customer Cooldown Period
    is_in_cooldown = False
    cooldown_seconds = request.intervention.max_frequency_days * 86400.0
    for prev_time in request.customer_history_timestamps:
        elapsed = (request.current_time.value - prev_time.value).total_seconds()
        if 0.0 <= elapsed < cooldown_seconds:
            is_in_cooldown = True
            break
    if is_in_cooldown:
        violated.append("ERR_COOLDOWN_ACTIVE")
    else:
        passed.append("COOLDOWN_PASSED")

    # 6. Quarterly Frequency Cap
    quarterly_count = len(request.quarterly_history_timestamps)
    if quarterly_count >= request.max_quarterly_frequency:
        violated.append("ERR_FREQUENCY_CAP_EXCEEDED")
    else:
        passed.append("FREQUENCY_CAP_PASSED")

    # 7. Customer Marketing/Outreach Consent
    if request.customer_opt_out:
        violated.append("ERR_CUSTOMER_OPTED_OUT")
    else:
        passed.append("CUSTOMER_CONSENT_PASSED")

    # 8. Do-Not-Disturb / Legal Exclusion List
    if request.is_excluded:
        violated.append("ERR_CUSTOMER_EXCLUDED")
    else:
        passed.append("EXCLUSION_LIST_PASSED")

    # 9. Incident Blast-Radius Limit (NFR-COST-001)
    if request.incident_treated_count >= request.max_blast_radius:
        violated.append("ERR_BLAST_RADIUS_EXCEEDED")
    else:
        passed.append("BLAST_RADIUS_PASSED")

    # 10. Feature Data Freshness Watermark (INV-DATA-001)
    staleness_seconds = (request.current_time.value - request.feature_timestamp.value).total_seconds()
    max_staleness_seconds = request.max_feature_staleness_hours * 3600.0
    if staleness_seconds > max_staleness_seconds:
        violated.append("ERR_STALE_FEATURES")
    else:
        passed.append("DATA_FRESHNESS_PASSED")

    is_eligible = len(violated) == 0

    return ConstraintEvaluationOutcome(
        is_eligible=is_eligible,
        passed_constraints=passed,
        violated_constraints=violated,
        evaluated_at=request.current_time,
    )


def filter_eligible_candidates(
    requests: list[ConstraintEvaluatorRequest],
) -> tuple[list[CandidateIntervention], dict[str, list[str]]]:
    """
    Audit multiple candidate interventions and split into eligible vs disqualified.
    Returns:
    (eligible_candidates, ineligible_reasons_dict)
    """
    eligible: list[CandidateIntervention] = []
    ineligible_reasons: dict[str, list[str]] = {}

    for req in requests:
        outcome = evaluate_hard_constraints(req)
        c_id = req.intervention.candidate_id
        if outcome.is_eligible:
            eligible.append(req.intervention)
        else:
            ineligible_reasons[c_id] = outcome.violated_constraints

    return eligible, ineligible_reasons
