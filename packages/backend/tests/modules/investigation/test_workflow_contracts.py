"""
RevPilot AI — Investigation Workflow Contract and Interface Tests
Verifies TASK-P03-002, TEMPORAL-WORKFLOW-SPEC.md §2–§8, INV-WF-001..002, INV-TEN-001..003, and INV-COST-001.
"""

from __future__ import annotations
from decimal import Decimal
import pytest


# =============================================================================
# 1. Workflow Input Contracts and Validation (§3)
# =============================================================================

def test_workflow_input_valid_passes():
    """Verify well-formed InvestigationWorkflowInput passes validation."""
    from revpilot.modules.investigation.workflows import InvestigationWorkflowInput

    inp = InvestigationWorkflowInput(
        investigation_id="inv_001",
        tenant_id="tnt_alpha",
        principal_id="usr_analyst",
        metric_name="mrr_drop",
        window_start="2026-05-10T00:00:00.000000Z",
        window_end="2026-05-17T00:00:00.000000Z",
        as_of_time="2026-05-18T00:00:00.000000Z",
        cost_budget_usd=Decimal("2.50"),
    )
    inp.validate(workflow_id="tenant/tnt_alpha/investigation/inv_001")


@pytest.mark.parametrize("bad_tenant", ["", "   "])
def test_workflow_input_rejects_empty_tenant(bad_tenant):
    """INV-TEN-001: Fail closed if tenant_id is missing or whitespace."""
    from revpilot.modules.investigation.workflows import InvestigationWorkflowInput
    from revpilot.shared.errors import TenancyViolationError

    inp = InvestigationWorkflowInput(
        investigation_id="inv_001",
        tenant_id=bad_tenant,
        principal_id="usr_analyst",
    )
    with pytest.raises(TenancyViolationError, match="tenant_id cannot be null or empty"):
        inp.validate()


def test_workflow_input_rejects_mismatched_workflow_id():
    """INV-TEN-001: Fail closed if workflow_id does not strictly match tenant/{tnt}/investigation/{inv}."""
    from revpilot.modules.investigation.workflows import InvestigationWorkflowInput
    from revpilot.shared.errors import TenancyViolationError

    inp = InvestigationWorkflowInput(
        investigation_id="inv_001",
        tenant_id="tnt_alpha",
        principal_id="usr_analyst",
    )
    with pytest.raises(TenancyViolationError, match="violates canonical tenant format"):
        inp.validate(workflow_id="tenant/tnt_evil/investigation/inv_001")


def test_workflow_input_rejects_inverted_time_window():
    """INV-DATA-001: Fail closed if window_start >= window_end."""
    from revpilot.modules.investigation.workflows import InvestigationWorkflowInput
    from revpilot.modules.investigation.domain.errors import TemporalValidationException

    inp = InvestigationWorkflowInput(
        investigation_id="inv_001",
        tenant_id="tnt_alpha",
        principal_id="usr_analyst",
        window_start="2026-05-18T00:00:00.000000Z",
        window_end="2026-05-10T00:00:00.000000Z",
        as_of_time="2026-05-19T00:00:00.000000Z",
    )
    with pytest.raises(TemporalValidationException, match="must precede window_end"):
        inp.validate()


def test_workflow_input_rejects_window_exceeding_as_of_time():
    """INV-DATA-001: Fail closed if window_end > as_of_time (future data leakage prevention)."""
    from revpilot.modules.investigation.workflows import InvestigationWorkflowInput
    from revpilot.modules.investigation.domain.errors import TemporalValidationException

    inp = InvestigationWorkflowInput(
        investigation_id="inv_001",
        tenant_id="tnt_alpha",
        principal_id="usr_analyst",
        window_start="2026-05-10T00:00:00.000000Z",
        window_end="2026-05-20T00:00:00.000000Z",
        as_of_time="2026-05-15T00:00:00.000000Z",
    )
    with pytest.raises(TemporalValidationException, match="exceeds as_of_time"):
        inp.validate()


def test_workflow_input_rejects_budget_over_hard_ceiling():
    """INV-COST-001: Fail closed if cost_budget_usd exceeds $5.00 ceiling."""
    from revpilot.modules.investigation.workflows import InvestigationWorkflowInput
    from revpilot.modules.investigation.domain.errors import BudgetExceededError

    inp = InvestigationWorkflowInput(
        investigation_id="inv_001",
        tenant_id="tnt_alpha",
        principal_id="usr_analyst",
        cost_budget_usd=Decimal("5.01"),
    )
    with pytest.raises(BudgetExceededError, match="exceeds maximum hard limit of \\$5.00"):
        inp.validate()


def test_workflow_input_rejects_negative_budget():
    """INV-COST-001: Fail closed on negative budget spend limit."""
    from revpilot.modules.investigation.workflows import InvestigationWorkflowInput
    from revpilot.modules.investigation.domain.errors import BudgetExceededError

    inp = InvestigationWorkflowInput(
        investigation_id="inv_001",
        tenant_id="tnt_alpha",
        principal_id="usr_analyst",
        cost_budget_usd=Decimal("-1.00"),
    )
    with pytest.raises(BudgetExceededError, match="cannot be negative"):
        inp.validate()


# =============================================================================
# 2. Signals and Query Contract Objects (§6)
# =============================================================================

def test_signals_instantiation():
    """Verify pause, resume, and cancel signal contracts."""
    from revpilot.modules.investigation.workflows import (
        PauseInvestigationSignal,
        ResumeInvestigationSignal,
        CancelInvestigationSignal,
    )

    pause = PauseInvestigationSignal(reason="Awaiting customer escalation", paused_by="usr_lead")
    assert pause.reason == "Awaiting customer escalation"
    assert pause.paused_by == "usr_lead"

    resume = ResumeInvestigationSignal(resumed_by="usr_lead")
    assert resume.resumed_by == "usr_lead"

    cancel = CancelInvestigationSignal(reason="Duplicate ticket", cancelled_by="usr_admin")
    assert cancel.reason == "Duplicate ticket"
    assert cancel.cancelled_by == "usr_admin"


def test_progress_contract_metrics():
    """Verify progress reporting projection."""
    from revpilot.modules.investigation.workflows import InvestigationProgress

    progress = InvestigationProgress(
        total_tasks=8,
        completed_tasks=4,
        running_tasks=1,
        pending_tasks=3,
        status="GATHERING_EVIDENCE",
    )
    p_dict = progress.to_dict()
    assert p_dict["total_tasks"] == 8
    assert p_dict["completed_tasks"] == 4
    assert p_dict["running_tasks"] == 1
    assert p_dict["pending_tasks"] == 3
    assert p_dict["status"] == "GATHERING_EVIDENCE"


# =============================================================================
# 3. Activity Partitioning and Retry Policies (§2.2, §5, §7.2)
# =============================================================================

def test_task_queue_partitioning_constants():
    """§2.2: Verify canonical queue names."""
    from revpilot.modules.investigation.workflows import (
        INVESTIGATION_WORKFLOW_QUEUE,
        INVESTIGATION_ANALYTICS_QUEUE,
        INVESTIGATION_RETRIEVAL_QUEUE,
        INVESTIGATION_AGENT_QUEUE,
    )

    assert INVESTIGATION_WORKFLOW_QUEUE == "investigation-workflow-queue"
    assert INVESTIGATION_ANALYTICS_QUEUE == "investigation-analytics-activity-queue"
    assert INVESTIGATION_RETRIEVAL_QUEUE == "investigation-retrieval-activity-queue"
    assert INVESTIGATION_AGENT_QUEUE == "investigation-agent-activity-queue"


def test_transient_activity_retry_policy():
    """§7.2: Verify retry policy parameters and non-retryable exceptions."""
    from revpilot.modules.investigation.workflows import TRANSIENT_ACTIVITY_RETRY_POLICY

    assert TRANSIENT_ACTIVITY_RETRY_POLICY.maximum_attempts == 2
    assert TRANSIENT_ACTIVITY_RETRY_POLICY.backoff_coefficient == 2.0
    non_retryable = set(TRANSIENT_ACTIVITY_RETRY_POLICY.non_retryable_error_types or [])
    expected_non_retryable = {
        "TenantViolationError",
        "AuthorizationDeniedError",
        "SchemaValidationError",
        "BudgetExceededError",
        "PromptInjectionDetectedError",
    }
    assert expected_non_retryable.issubset(non_retryable)


def test_all_eight_activities_are_temporal_activity_definitions():
    """§5: Verify all 8 activities are decorated with @activity.defn."""
    from temporalio import activity
    from revpilot.modules.investigation.workflows import (
        ValidateInvestigationScopeActivity,
        GenerateInvestigationPlanActivity,
        ExecuteReadOnlySqlCapabilityActivity,
        ExecuteGovernedRetrievalActivity,
        IngestTicketIntelligenceActivity,
        SynthesizeHypothesesActivity,
        VerifyEvidenceAndHypothesesActivity,
        PackageEvidenceBundleActivity,
    )

    activities = [
        ValidateInvestigationScopeActivity,
        GenerateInvestigationPlanActivity,
        ExecuteReadOnlySqlCapabilityActivity,
        ExecuteGovernedRetrievalActivity,
        IngestTicketIntelligenceActivity,
        SynthesizeHypothesesActivity,
        VerifyEvidenceAndHypothesesActivity,
        PackageEvidenceBundleActivity,
    ]
    for act in activities:
        defn = activity._Definition.from_callable(act)
        assert defn is not None
        assert defn.name is not None
        assert len(defn.name) > 0
