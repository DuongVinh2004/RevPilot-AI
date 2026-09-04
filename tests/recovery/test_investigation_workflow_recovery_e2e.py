"""
RevPilot AI — Investigation Workflow Recovery and Durability E2E Tests
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §5, §7
Verifies INV-WF-001, INV-WF-002, INV-REL-001, NFR-DUR-001, and AC-P03-008-01.
"""

from __future__ import annotations
from decimal import Decimal
import sys
from typing import Any
import pytest


@pytest.fixture(autouse=True)
def _isolate_modules():
    """Ensure modules are isolated between test runs."""
    yield
    for mod in list(sys.modules.keys()):
        if any(
            mod.startswith(p)
            for p in (
                "revpilot.modules.investigation",
                "revpilot.modules.analytics",
                "revpilot.modules.evidence",
                "revpilot.modules.retrieval",
                "revpilot.modules.agent",
                "revpilot.modules.tickets",
            )
        ):
            sys.modules.pop(mod, None)


@pytest.mark.asyncio
async def test_investigation_workflow_transient_failure_recovery():
    """
    INV-WF-002: Workflow survives transient activity crashes and resumes cleanly
    according to TRANSIENT_ACTIVITY_RETRY_POLICY.
    """
    from temporalio import activity
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        InvestigationWorkflowInput,
        INVESTIGATION_WORKFLOW_QUEUE,
        INVESTIGATION_ANALYTICS_QUEUE,
        INVESTIGATION_RETRIEVAL_QUEUE,
        INVESTIGATION_AGENT_QUEUE,
        ValidateInvestigationScopeResult,
        package_evidence_bundle_activity,
        execute_read_only_sql_capability_activity,
        execute_governed_retrieval_activity,
        ingest_ticket_intelligence_activity,
        generate_investigation_plan_activity,
        synthesize_hypotheses_activity,
        verify_evidence_and_hypotheses_activity,
    )
    from revpilot.modules.investigation.domain.models import InvestigationStatus

    attempt_count = 0

    @activity.defn(name="ValidateInvestigationScopeActivity")
    async def flaky_validate_scope(input_data: Any) -> Any:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise RuntimeError("CRASH_INJECTED: Simulated worker crash during scope validation")
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

    wf_input = InvestigationWorkflowInput(
        investigation_id="inv_recovery_e2e_01",
        tenant_id="tnt_recovery",
        principal_id="usr_tester",
        metric_name="order_cancellation_rate",
        investigation_scope={"region": "US-MIDWEST", "facility": "WH-MIDWEST-01"},
        window_start="2026-05-10T00:00:00.000000Z",
        window_end="2026-05-17T00:00:00.000000Z",
        as_of_time="2026-05-18T00:00:00.000000Z",
        cost_budget_usd=Decimal("2.50"),
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
            wf_id = f"tenant/{wf_input.tenant_id}/investigation/{wf_input.investigation_id}"
            handle = await env.client.start_workflow(
                InvestigationWorkflow.run,
                wf_input,
                id=wf_id,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            )

            manifest = await handle.result()
            assert manifest is not None
            assert manifest.top_hypothesis_id is not None
            assert manifest.bundle_digest is not None
            assert attempt_count == 2

            state = await handle.query(InvestigationWorkflow.get_investigation_state)
            assert state.status == InvestigationStatus.COMPLETED
            assert state.error_code is None
