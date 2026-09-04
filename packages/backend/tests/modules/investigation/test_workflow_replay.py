"""
RevPilot AI — Temporal Investigation Workflow Replay Compatibility Tests
Verifies AC-P03-002-02, INV-WF-002, AC-003, and TEMPORAL-WORKFLOW-SPEC.md §8.
"""

from __future__ import annotations
from decimal import Decimal
import pytest


@pytest.fixture
def replay_workflow_input():
    from revpilot.modules.investigation.workflows import InvestigationWorkflowInput

    return InvestigationWorkflowInput(
        investigation_id="inv_replay_001",
        tenant_id="tnt_replay",
        principal_id="usr_replay",
        metric_name="churn_rate_spike",
        investigation_scope={"region": "EU-CENTRAL", "tier": "ENTERPRISE"},
        window_start="2026-05-10T00:00:00.000000Z",
        window_end="2026-05-17T00:00:00.000000Z",
        as_of_time="2026-05-18T00:00:00.000000Z",
        cost_budget_usd=Decimal("3.00"),
    )


# =============================================================================
# AC-P03-002-02: Workflow Replay Compatibility without Determinism Violations
# =============================================================================

@pytest.mark.asyncio
async def test_workflow_replay_compatibility_happy_path(replay_workflow_input):
    """
    AC-P03-002-02: WorkflowReplayer confirms full replay compatibility
    against recorded execution history without non-deterministic errors (INV-WF-002, AC-003).
    """
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        WorkflowReplayer,
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
            wf_id = f"tenant/{replay_workflow_input.tenant_id}/investigation/{replay_workflow_input.investigation_id}"
            handle = await env.client.start_workflow(
                InvestigationWorkflow.run,
                replay_workflow_input,
                id=wf_id,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            )

            manifest = await handle.result()
            assert manifest.investigation_id == replay_workflow_input.investigation_id

            # 1. Fetch complete Temporal history
            history = await handle.fetch_history()
            assert len(history.events) > 10, "History must capture multi-activity lifecycle events"

            # 2. Replay history through WorkflowReplayer
            replayer = WorkflowReplayer(
                workflows=[InvestigationWorkflow],
                data_converter=pydantic_data_converter,
            )
            replay_result = await replayer.replay_workflow(history, raise_on_replay_failure=True)

            assert replay_result.replay_failure is None, (
                f"Replay failed with non-deterministic error: {replay_result.replay_failure}"
            )


@pytest.mark.asyncio
async def test_workflow_replay_compatibility_with_pause_resume_signals(replay_workflow_input):
    """
    Verify replay compatibility when workflow execution history contains Pause and Resume signals.
    """
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        WorkflowReplayer,
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
            replay_workflow_input.investigation_id = "inv_replay_pause_001"
            wf_id = f"tenant/{replay_workflow_input.tenant_id}/investigation/{replay_workflow_input.investigation_id}"

            handle = await env.client.start_workflow(
                InvestigationWorkflow.run,
                replay_workflow_input,
                id=wf_id,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            )

            await handle.signal(
                InvestigationWorkflow.pause_investigation,
                PauseInvestigationSignal(reason="Analyst verification", paused_by="usr_lead"),
            )
            await handle.signal(
                InvestigationWorkflow.resume_investigation,
                ResumeInvestigationSignal(resumed_by="usr_lead"),
            )

            await handle.result()
            history = await handle.fetch_history()

            replayer = WorkflowReplayer(
                workflows=[InvestigationWorkflow],
                data_converter=pydantic_data_converter,
            )
            replay_result = await replayer.replay_workflow(history, raise_on_replay_failure=True)
            assert replay_result.replay_failure is None


@pytest.mark.asyncio
async def test_workflow_replay_compatibility_with_cancellation_signal(replay_workflow_input):
    """
    Verify replay compatibility when workflow execution history contains Cancel signal.
    """
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        WorkflowReplayer,
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
            replay_workflow_input.investigation_id = "inv_replay_cancel_001"
            wf_id = f"tenant/{replay_workflow_input.tenant_id}/investigation/{replay_workflow_input.investigation_id}"

            handle = await env.client.start_workflow(
                InvestigationWorkflow.run,
                replay_workflow_input,
                id=wf_id,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            )

            await handle.signal(
                InvestigationWorkflow.cancel_investigation,
                CancelInvestigationSignal(reason="Analyst aborted", cancelled_by="usr_lead"),
            )

            try:
                await handle.result()
            except Exception:
                pass

            history = await handle.fetch_history()

            replayer = WorkflowReplayer(
                workflows=[InvestigationWorkflow],
                data_converter=pydantic_data_converter,
            )
            replay_result = await replayer.replay_workflow(history, raise_on_replay_failure=True)
            assert replay_result.replay_failure is None
