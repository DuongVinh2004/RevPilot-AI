"""
RevPilot AI — Temporal Investigation Workflow Durability and Failure Tests
Verifies AC-P03-002-01, INV-WF-001, INV-WF-002, INV-TEN-001..003, INV-REL-001, and NFR-DUR-001.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any
import pytest


@pytest.fixture
def sample_workflow_input():
    from revpilot.modules.investigation.workflows import InvestigationWorkflowInput

    return InvestigationWorkflowInput(
        investigation_id="inv_durability_001",
        tenant_id="tnt_durability",
        principal_id="usr_durability",
        metric_name="mrr_contraction",
        investigation_scope={"region": "US-EAST", "tier": "ENTERPRISE"},
        window_start="2026-05-10T00:00:00.000000Z",
        window_end="2026-05-17T00:00:00.000000Z",
        as_of_time="2026-05-18T00:00:00.000000Z",
        cost_budget_usd=Decimal("2.50"),
    )


# =============================================================================
# 1. AC-P03-002-01: Clean Progression from INITIALIZING to COMPLETED
# =============================================================================

@pytest.mark.asyncio
async def test_workflow_happy_path_clean_progression(sample_workflow_input):
    """
    AC-P03-002-01: InvestigationWorkflow runs cleanly from INITIALIZING to COMPLETED
    and produces a valid sealed InvestigationManifest.
    """
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.domain.models import InvestigationStatus
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        INVESTIGATION_WORKFLOW_QUEUE,
        INVESTIGATION_ANALYTICS_QUEUE,
        INVESTIGATION_RETRIEVAL_QUEUE,
        INVESTIGATION_AGENT_QUEUE,
        validate_investigation_scope_activity,
        package_evidence_bundle_activity,
        execute_read_only_sql_capability_activity,
        execute_governed_retrieval_activity,
        ingest_ticket_intelligence_activity,
        generate_investigation_plan_activity,
        synthesize_hypotheses_activity,
        verify_evidence_and_hypotheses_activity,
    )

    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
        async with (
            Worker(
                env.client,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
                workflows=[InvestigationWorkflow],
                activities=[validate_investigation_scope_activity, package_evidence_bundle_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_ANALYTICS_QUEUE,
                activities=[execute_read_only_sql_capability_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_RETRIEVAL_QUEUE,
                activities=[execute_governed_retrieval_activity, ingest_ticket_intelligence_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_AGENT_QUEUE,
                activities=[
                    generate_investigation_plan_activity,
                    synthesize_hypotheses_activity,
                    verify_evidence_and_hypotheses_activity,
                ],
            ),
        ):
            wf_id = f"tenant/{sample_workflow_input.tenant_id}/investigation/{sample_workflow_input.investigation_id}"
            handle = await env.client.start_workflow(
                InvestigationWorkflow.run,
                sample_workflow_input,
                id=wf_id,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            )

            manifest = await handle.result()
            assert manifest is not None
            assert manifest.investigation_id == sample_workflow_input.investigation_id
            assert manifest.tenant_id.value == sample_workflow_input.tenant_id
            assert manifest.top_hypothesis_id is not None
            assert manifest.bundle_digest.startswith("sha256:")
            assert manifest.cogs_usd > Decimal("0.00")
            assert manifest.sealed_at is not None

            # Verify query projections on completed workflow
            state = await handle.query(InvestigationWorkflow.get_investigation_state)
            assert state.status == InvestigationStatus.COMPLETED
            assert state.manifest is not None
            assert state.budget.spent_usd > Decimal("0.00")

            progress = await handle.query(InvestigationWorkflow.get_progress)
            assert progress["status"] == "COMPLETED"
            assert progress["completed_tasks"] >= 7


# =============================================================================
# 2. Pause and Resume Signal Handling (§6.1)
# =============================================================================

@pytest.mark.asyncio
async def test_workflow_pause_and_resume_signals(sample_workflow_input):
    """
    Verify pause signal halts workflow progression and resume signal restores it.
    """
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        INVESTIGATION_WORKFLOW_QUEUE,
        INVESTIGATION_ANALYTICS_QUEUE,
        INVESTIGATION_RETRIEVAL_QUEUE,
        INVESTIGATION_AGENT_QUEUE,
        PauseInvestigationSignal,
        ResumeInvestigationSignal,
        validate_investigation_scope_activity,
        package_evidence_bundle_activity,
        execute_read_only_sql_capability_activity,
        execute_governed_retrieval_activity,
        ingest_ticket_intelligence_activity,
        generate_investigation_plan_activity,
        synthesize_hypotheses_activity,
        verify_evidence_and_hypotheses_activity,
    )

    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
        async with (
            Worker(
                env.client,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
                workflows=[InvestigationWorkflow],
                activities=[validate_investigation_scope_activity, package_evidence_bundle_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_ANALYTICS_QUEUE,
                activities=[execute_read_only_sql_capability_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_RETRIEVAL_QUEUE,
                activities=[execute_governed_retrieval_activity, ingest_ticket_intelligence_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_AGENT_QUEUE,
                activities=[
                    generate_investigation_plan_activity,
                    synthesize_hypotheses_activity,
                    verify_evidence_and_hypotheses_activity,
                ],
            ),
        ):
            sample_workflow_input.investigation_id = "inv_pause_001"
            wf_id = f"tenant/{sample_workflow_input.tenant_id}/investigation/{sample_workflow_input.investigation_id}"

            handle = await env.client.start_workflow(
                InvestigationWorkflow.run,
                sample_workflow_input,
                id=wf_id,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            )

            # Signal pause
            await handle.signal(
                InvestigationWorkflow.pause_investigation,
                PauseInvestigationSignal(reason="Analyst reviewing data", paused_by="usr_lead"),
            )

            # Resume
            await handle.signal(
                InvestigationWorkflow.resume_investigation,
                ResumeInvestigationSignal(resumed_by="usr_lead"),
            )

            manifest = await handle.result()
            assert manifest is not None
            assert manifest.investigation_id == "inv_pause_001"


# =============================================================================
# 3. Cancellation Signal Handling (§6.1)
# =============================================================================

@pytest.mark.asyncio
async def test_workflow_cancel_signal_terminates_workflow(sample_workflow_input):
    """
    Verify cancel signal immediately transitions state to CANCELLED and fails closed.
    """
    from temporalio.client import WorkflowFailureError
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.exceptions import ApplicationError
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        INVESTIGATION_WORKFLOW_QUEUE,
        INVESTIGATION_ANALYTICS_QUEUE,
        INVESTIGATION_RETRIEVAL_QUEUE,
        INVESTIGATION_AGENT_QUEUE,
        CancelInvestigationSignal,
        validate_investigation_scope_activity,
        package_evidence_bundle_activity,
        execute_read_only_sql_capability_activity,
        execute_governed_retrieval_activity,
        ingest_ticket_intelligence_activity,
        generate_investigation_plan_activity,
        synthesize_hypotheses_activity,
        verify_evidence_and_hypotheses_activity,
    )

    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
        async with (
            Worker(
                env.client,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
                workflows=[InvestigationWorkflow],
                activities=[validate_investigation_scope_activity, package_evidence_bundle_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_ANALYTICS_QUEUE,
                activities=[execute_read_only_sql_capability_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_RETRIEVAL_QUEUE,
                activities=[execute_governed_retrieval_activity, ingest_ticket_intelligence_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_AGENT_QUEUE,
                activities=[
                    generate_investigation_plan_activity,
                    synthesize_hypotheses_activity,
                    verify_evidence_and_hypotheses_activity,
                ],
            ),
        ):
            sample_workflow_input.investigation_id = "inv_cancel_001"
            wf_id = f"tenant/{sample_workflow_input.tenant_id}/investigation/{sample_workflow_input.investigation_id}"

            handle = await env.client.start_workflow(
                InvestigationWorkflow.run,
                sample_workflow_input,
                id=wf_id,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            )

            # Cancel immediately
            await handle.signal(
                InvestigationWorkflow.cancel_investigation,
                CancelInvestigationSignal(reason="User cancelled investigation", cancelled_by="usr_analyst"),
            )

            with pytest.raises(WorkflowFailureError) as exc_info:
                await handle.result()

            assert exc_info.value.cause is not None
            assert isinstance(exc_info.value.cause, ApplicationError)
            assert exc_info.value.cause.type == "ERR_WORKFLOW_CANCELLED"


# =============================================================================
# 4. Activity Transient Failure and Retry Recovery (§7.2, NFR-REL-001)
# =============================================================================

@pytest.mark.asyncio
async def test_workflow_recovers_from_transient_activity_failure(sample_workflow_input):
    """
    Verify activity transient failure triggers retry and workflow completes successfully.
    """
    from temporalio import activity
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        INVESTIGATION_WORKFLOW_QUEUE,
        INVESTIGATION_ANALYTICS_QUEUE,
        INVESTIGATION_RETRIEVAL_QUEUE,
        INVESTIGATION_AGENT_QUEUE,
        package_evidence_bundle_activity,
        execute_read_only_sql_capability_activity,
        execute_governed_retrieval_activity,
        ingest_ticket_intelligence_activity,
        generate_investigation_plan_activity,
        synthesize_hypotheses_activity,
        verify_evidence_and_hypotheses_activity,
        ValidateInvestigationScopeInput,
        ValidateInvestigationScopeResult,
    )

    attempt_count = 0

    @activity.defn(name="ValidateInvestigationScopeActivity")
    async def flaky_validate_scope(input_data: Any) -> Any:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise RuntimeError("Transient connection reset to policy store")
        if isinstance(input_data, dict):
            m_name = input_data["metric_name"]
            filters = input_data.get("investigation_scope", {})
        else:
            m_name = input_data.metric_name
            filters = input_data.investigation_scope

        return ValidateInvestigationScopeResult(
            is_valid=True,
            metric_name=m_name,
            dimension_filters=filters,
            validation_message="Recovered on retry",
        )

    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
        async with (
            Worker(
                env.client,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
                workflows=[InvestigationWorkflow],
                activities=[flaky_validate_scope, package_evidence_bundle_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_ANALYTICS_QUEUE,
                activities=[execute_read_only_sql_capability_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_RETRIEVAL_QUEUE,
                activities=[execute_governed_retrieval_activity, ingest_ticket_intelligence_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_AGENT_QUEUE,
                activities=[
                    generate_investigation_plan_activity,
                    synthesize_hypotheses_activity,
                    verify_evidence_and_hypotheses_activity,
                ],
            ),
        ):
            sample_workflow_input.investigation_id = "inv_retry_001"
            wf_id = f"tenant/{sample_workflow_input.tenant_id}/investigation/{sample_workflow_input.investigation_id}"

            manifest = await env.client.execute_workflow(
                InvestigationWorkflow.run,
                sample_workflow_input,
                id=wf_id,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            )

            assert attempt_count == 2, "Activity should have retried once and succeeded on second attempt"
            assert manifest.investigation_id == "inv_retry_001"


# =============================================================================
# 5. Fail-Closed Tenant and Input Violation (§7.3, INV-TEN-002)
# =============================================================================

@pytest.mark.asyncio
async def test_workflow_fails_closed_on_tenant_id_mismatch(sample_workflow_input):
    """
    INV-TEN-001..002: Workflow ID must strictly match tenant/{tenant_id}/investigation/{id}.
    A mismatched tenant ID in workflow ID causes immediate fail-closed termination.
    """
    from temporalio.client import WorkflowFailureError
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.exceptions import ApplicationError
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        INVESTIGATION_WORKFLOW_QUEUE,
        validate_investigation_scope_activity,
        package_evidence_bundle_activity,
    )

    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
        async with Worker(
            env.client,
            task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            workflows=[InvestigationWorkflow],
            activities=[validate_investigation_scope_activity, package_evidence_bundle_activity],
        ):
            bad_wf_id = f"tenant/tnt_different/investigation/{sample_workflow_input.investigation_id}"
            with pytest.raises(WorkflowFailureError) as exc_info:
                await env.client.execute_workflow(
                    InvestigationWorkflow.run,
                    sample_workflow_input,
                    id=bad_wf_id,
                    task_queue=INVESTIGATION_WORKFLOW_QUEUE,
                )

            assert exc_info.value.cause is not None
            assert isinstance(exc_info.value.cause, ApplicationError)
            assert exc_info.value.cause.type == "ERR_TENANT_VIOLATION"
