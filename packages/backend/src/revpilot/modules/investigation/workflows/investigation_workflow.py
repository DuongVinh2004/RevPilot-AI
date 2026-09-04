"""
RevPilot AI — Temporal Durable Investigation Workflow Implementation
Conforms to docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §2–§8,
ADR-0002, and INVARIANT-REGISTRY.md (INV-WF-001, INV-WF-002, INV-TEN-001..003, INV-REL-001).
"""

from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
from typing import Any, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from revpilot.modules.investigation.domain.models import (
    InvestigationStatus,
    BudgetState,
    InvestigationManifest,
)
from revpilot.modules.investigation.domain.state_machine import (
    transition_investigation_state,
)
from revpilot.modules.investigation.domain.errors import (
    BudgetExceededError,
    TemporalValidationException,
    InvalidStateTransitionError,
)
from revpilot.shared.errors import TenancyViolationError

with workflow.unsafe.imports_passed_through():
    from revpilot.modules.investigation.workflows.signals import (
        PauseInvestigationSignal,
        ResumeInvestigationSignal,
        CancelInvestigationSignal,
        InvestigationWorkflowInput,
        InvestigationState,
        InvestigationProgress,
    )
    from revpilot.modules.investigation.workflows.activities import (
        INVESTIGATION_WORKFLOW_QUEUE,
        INVESTIGATION_ANALYTICS_QUEUE,
        INVESTIGATION_RETRIEVAL_QUEUE,
        INVESTIGATION_AGENT_QUEUE,
        TRANSIENT_ACTIVITY_RETRY_POLICY,
        ValidateInvestigationScopeInput,
        ValidateInvestigationScopeResult,
        validate_investigation_scope_activity,
        GenerateInvestigationPlanInput,
        GenerateInvestigationPlanResult,
        generate_investigation_plan_activity,
        ExecuteReadOnlySqlCapabilityInput,
        ExecuteReadOnlySqlCapabilityResult,
        execute_read_only_sql_capability_activity,
        ExecuteGovernedRetrievalInput,
        ExecuteGovernedRetrievalResult,
        execute_governed_retrieval_activity,
        IngestTicketIntelligenceInput,
        IngestTicketIntelligenceResult,
        ingest_ticket_intelligence_activity,
        SynthesizeHypothesesInput,
        SynthesizeHypothesesResult,
        synthesize_hypotheses_activity,
        VerifyEvidenceAndHypothesesInput,
        VerifyEvidenceAndHypothesesResult,
        verify_evidence_and_hypotheses_activity,
        PackageEvidenceBundleInput,
        package_evidence_bundle_activity,
    )


@workflow.defn(name="InvestigationWorkflow")
class InvestigationWorkflow:
    """
    Temporal durable investigation workflow orchestrating multi-step investigation DAG.
    Guarantees fault-tolerant execution, atomic signal handling, and deterministic replay.
    """

    def __init__(self) -> None:
        self._status: InvestigationStatus = InvestigationStatus.INITIALIZING
        self._prior_active_state: Optional[InvestigationStatus] = None
        self._budget: BudgetState = BudgetState()
        self._is_paused: bool = False
        self._is_cancelled: bool = False
        self._pause_reason: Optional[str] = None
        self._paused_by: Optional[str] = None
        self._cancel_reason: Optional[str] = None
        self._cancelled_by: Optional[str] = None
        self._error_code: Optional[str] = None
        self._error_message: Optional[str] = None
        self._current_step: str = "INITIALIZING"
        self._total_tasks: int = 8
        self._completed_tasks: int = 0
        self._running_tasks: int = 0
        self._manifest: Optional[InvestigationManifest] = None
        self._input: Optional[InvestigationWorkflowInput] = None

    def _transition(self, target: InvestigationStatus) -> None:
        """Enforce deterministic state machine transition."""
        res = transition_investigation_state(
            current=self._status,
            target=target,
            prior_active_state=self._prior_active_state,
        )
        if res.is_failure:
            err = res.unwrap_err()
            raise ApplicationError(
                str(err),
                type="ERR_INVALID_STATE_TRANSITION",
                non_retryable=True,
            )
        self._status = res.unwrap()

    async def _check_pause_and_cancellation(self) -> None:
        """Atomic gate for pause and cancellation signals."""
        if self._is_cancelled:
            if self._status != InvestigationStatus.CANCELLED:
                self._transition(InvestigationStatus.CANCELLED)
            raise ApplicationError(
                self._cancel_reason or "Investigation cancelled by user",
                type="ERR_WORKFLOW_CANCELLED",
                non_retryable=True,
            )

        if self._is_paused:
            if self._status != InvestigationStatus.PAUSED:
                self._prior_active_state = self._status
                self._transition(InvestigationStatus.PAUSED)

            # Await unpause or cancellation deterministically
            await workflow.wait_condition(lambda: not self._is_paused or self._is_cancelled)

            if self._is_cancelled:
                self._transition(InvestigationStatus.CANCELLED)
                raise ApplicationError(
                    self._cancel_reason or "Investigation cancelled by user",
                    type="ERR_WORKFLOW_CANCELLED",
                    non_retryable=True,
                )

            # Resumed: restore active state
            if self._prior_active_state is not None:
                self._transition(self._prior_active_state)

    @workflow.run
    async def run(self, input_data: InvestigationWorkflowInput) -> InvestigationManifest:
        """
        Execute durable investigation lifecycle from INITIALIZING to COMPLETED.
        Enforces INV-WF-001, INV-WF-002, INV-TEN-001..003, INV-REL-001.
        """
        self._input = input_data
        self._budget = BudgetState(
            allocated_usd=Decimal(str(input_data.cost_budget_usd)),
            allocated_tool_calls=input_data.tool_call_budget,
        )

        # 1. Enforce canonical workflow ID format and input validation (§2.1, §3)
        workflow_id = workflow.info().workflow_id
        try:
            input_data.validate(workflow_id=workflow_id)
        except (TenancyViolationError, ValueError, BudgetExceededError, TemporalValidationException) as ex:
            self._error_code = (
                "ERR_TENANT_VIOLATION"
                if isinstance(ex, TenancyViolationError)
                else "ERR_INVALID_INPUT"
            )
            self._error_message = str(ex)
            self._transition(InvestigationStatus.FAILED)
            raise ApplicationError(
                f"Investigation validation failed: {ex}",
                type=self._error_code,
                non_retryable=True,
            ) from ex

        await self._check_pause_and_cancellation()

        # 2. Transition to PLANNING state (§4)
        self._transition(InvestigationStatus.PLANNING)
        self._current_step = "VALIDATING_SCOPE"

        try:
            # 2.1 Validate Scope Activity (§5.1)
            scope_input = ValidateInvestigationScopeInput(
                investigation_id=input_data.investigation_id,
                tenant_id=input_data.tenant_id,
                metric_name=input_data.metric_name,
                investigation_scope=input_data.investigation_scope,
            )
            self._running_tasks = 1
            scope_result = await workflow.execute_activity(
                validate_investigation_scope_activity,
                scope_input,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
                schedule_to_close_timeout=timedelta(seconds=10),
                retry_policy=TRANSIENT_ACTIVITY_RETRY_POLICY,
            )
            self._completed_tasks += 1
            self._running_tasks = 0
            self._budget.record_spend(usd=Decimal("0.05"), tool_calls=1)

            await self._check_pause_and_cancellation()

            # 2.2 Generate Investigation Plan Activity (§5.2)
            self._current_step = "GENERATING_PLAN"
            plan_input = GenerateInvestigationPlanInput(
                investigation_id=input_data.investigation_id,
                tenant_id=input_data.tenant_id,
                metric_name=input_data.metric_name,
                scope=input_data.investigation_scope,
                window_start=input_data.window_start,
                window_end=input_data.window_end,
            )
            self._running_tasks = 1
            plan_result = await workflow.execute_activity(
                generate_investigation_plan_activity,
                plan_input,
                task_queue=INVESTIGATION_AGENT_QUEUE,
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            self._completed_tasks += 1
            self._running_tasks = 0
            self._budget.record_spend(usd=Decimal("0.20"), tool_calls=1)

            await self._check_pause_and_cancellation()

            # 3. Evidence Gathering & Verification Loop (§4)
            loop_count = 0
            verified = False
            top_hypothesis_id: Optional[str] = None
            evidence_digests: list[str] = []

            while loop_count < 2 and not verified:
                loop_count += 1
                self._transition(InvestigationStatus.GATHERING_EVIDENCE)
                self._current_step = f"GATHERING_EVIDENCE_LOOP_{loop_count}"

                # 3.1 Execute Read-Only SQL Capability Activity (§5.3)
                await self._check_pause_and_cancellation()
                self._running_tasks = 1
                sql_input = ExecuteReadOnlySqlCapabilityInput(
                    investigation_id=input_data.investigation_id,
                    tenant_id=input_data.tenant_id,
                    capability_name="mrr_breakdown_by_segment",
                    parameters={"metric": input_data.metric_name},
                )
                sql_result = await workflow.execute_activity(
                    execute_read_only_sql_capability_activity,
                    sql_input,
                    task_queue=INVESTIGATION_ANALYTICS_QUEUE,
                    schedule_to_close_timeout=timedelta(seconds=15),
                    heartbeat_timeout=timedelta(seconds=5),
                    retry_policy=TRANSIENT_ACTIVITY_RETRY_POLICY,
                )
                self._completed_tasks += 1
                self._running_tasks = 0
                evidence_digests.append(sql_result.row_digest)
                self._budget.record_spend(usd=Decimal("0.10"), tool_calls=1)

                # 3.2 Execute Governed Retrieval Activity (§5.4)
                await self._check_pause_and_cancellation()
                self._running_tasks = 1
                retrieval_input = ExecuteGovernedRetrievalInput(
                    investigation_id=input_data.investigation_id,
                    tenant_id=input_data.tenant_id,
                    query=f"anomalies for {input_data.metric_name}",
                    filters=input_data.investigation_scope,
                    as_of_time=input_data.as_of_time,
                )
                retrieval_result = await workflow.execute_activity(
                    execute_governed_retrieval_activity,
                    retrieval_input,
                    task_queue=INVESTIGATION_RETRIEVAL_QUEUE,
                    schedule_to_close_timeout=timedelta(seconds=20),
                    retry_policy=TRANSIENT_ACTIVITY_RETRY_POLICY,
                )
                self._completed_tasks += 1
                self._running_tasks = 0
                evidence_digests.append(retrieval_result.bundle_digest)
                self._budget.record_spend(usd=Decimal("0.15"), tool_calls=1)

                # 3.3 Ingest Ticket Intelligence Activity (§5.5)
                await self._check_pause_and_cancellation()
                self._running_tasks = 1
                ticket_input = IngestTicketIntelligenceInput(
                    investigation_id=input_data.investigation_id,
                    tenant_id=input_data.tenant_id,
                    scope=input_data.investigation_scope,
                    window_start=input_data.window_start,
                    window_end=input_data.window_end,
                )
                ticket_result = await workflow.execute_activity(
                    ingest_ticket_intelligence_activity,
                    ticket_input,
                    task_queue=INVESTIGATION_RETRIEVAL_QUEUE,
                    schedule_to_close_timeout=timedelta(seconds=15),
                    retry_policy=TRANSIENT_ACTIVITY_RETRY_POLICY,
                )
                self._completed_tasks += 1
                self._running_tasks = 0
                self._budget.record_spend(usd=Decimal("0.10"), tool_calls=1)

                # 3.4 Synthesize Hypotheses Activity (§5.6)
                await self._check_pause_and_cancellation()
                self._running_tasks = 1
                synth_input = SynthesizeHypothesesInput(
                    investigation_id=input_data.investigation_id,
                    tenant_id=input_data.tenant_id,
                    evidence_bundle_ids=evidence_digests,
                    plan_id=plan_result.plan_id,
                )
                synth_result = await workflow.execute_activity(
                    synthesize_hypotheses_activity,
                    synth_input,
                    task_queue=INVESTIGATION_AGENT_QUEUE,
                    schedule_to_close_timeout=timedelta(seconds=45),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )
                self._completed_tasks += 1
                self._running_tasks = 0
                self._budget.record_spend(usd=Decimal("0.25"), tool_calls=1)

                # 3.5 Verify Evidence & Hypotheses Activity (§5.7)
                await self._check_pause_and_cancellation()
                self._transition(InvestigationStatus.VERIFYING)
                self._current_step = "VERIFYING_HYPOTHESES"
                self._running_tasks = 1

                verify_input = VerifyEvidenceAndHypothesesInput(
                    investigation_id=input_data.investigation_id,
                    tenant_id=input_data.tenant_id,
                    hypotheses=synth_result.hypotheses,
                    evidence_digests=evidence_digests,
                )
                verify_result = await workflow.execute_activity(
                    verify_evidence_and_hypotheses_activity,
                    verify_input,
                    task_queue=INVESTIGATION_AGENT_QUEUE,
                    schedule_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )
                self._completed_tasks += 1
                self._running_tasks = 0

                if verify_result.status == "VERIFIED":
                    verified = True
                    top_hypothesis_id = verify_result.top_hypothesis_id
                    break
                elif verify_result.status == "NEED_MORE_EVIDENCE":
                    if loop_count >= 2:
                        self._transition(InvestigationStatus.NEED_MORE_EVIDENCE)
                        top_hypothesis_id = verify_result.top_hypothesis_id
                        break
                    # Loop back to GATHERING_EVIDENCE
                else:
                    self._transition(InvestigationStatus.FAILED)
                    self._error_code = "ERR_VERIFICATION_REFUTED"
                    self._error_message = "All root cause hypotheses refuted"
                    raise ApplicationError(
                        "Root cause hypotheses refuted by verifier",
                        type="ERR_VERIFICATION_REFUTED",
                        non_retryable=True,
                    )

            await self._check_pause_and_cancellation()

            # 4. Package Evidence Bundle Activity (§5.8)
            self._current_step = "PACKAGING_EVIDENCE"
            self._running_tasks = 1
            pkg_input = PackageEvidenceBundleInput(
                investigation_id=input_data.investigation_id,
                tenant_id=input_data.tenant_id,
                top_hypothesis_id=top_hypothesis_id,
                evidence_digests=evidence_digests,
                cogs_usd=str(self._budget.spent_usd),
                duration_seconds=int(workflow.now().timestamp()),
                sealed_at=workflow.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            )
            manifest = await workflow.execute_activity(
                package_evidence_bundle_activity,
                pkg_input,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
                schedule_to_close_timeout=timedelta(seconds=10),
                retry_policy=TRANSIENT_ACTIVITY_RETRY_POLICY,
            )
            self._completed_tasks += 1
            self._running_tasks = 0
            self._manifest = manifest

            if self._status != InvestigationStatus.NEED_MORE_EVIDENCE:
                self._transition(InvestigationStatus.COMPLETED)
            self._current_step = "SEALED"
            return manifest

        except ApplicationError:
            raise
        except Exception as ex:
            if self._status not in (
                InvestigationStatus.COMPLETED,
                InvestigationStatus.CANCELLED,
                InvestigationStatus.FAILED,
            ):
                try:
                    self._transition(InvestigationStatus.FAILED)
                except Exception:
                    self._status = InvestigationStatus.FAILED
            self._error_code = "ERR_WORKFLOW_EXECUTION_FAILURE"
            self._error_message = str(ex)
            raise ApplicationError(
                f"Workflow unhandled failure: {ex}",
                type=self._error_code,
                non_retryable=True,
            ) from ex

    # =========================================================================
    # Signal Handlers (§6.1)
    # =========================================================================

    @workflow.signal
    def pause_investigation(self, signal: PauseInvestigationSignal) -> None:
        """Atomic pause signal handler."""
        if self._status in (
            InvestigationStatus.COMPLETED,
            InvestigationStatus.FAILED,
            InvestigationStatus.CANCELLED,
        ):
            return
        self._is_paused = True
        self._pause_reason = signal.reason
        self._paused_by = signal.paused_by
        if self._status != InvestigationStatus.PAUSED:
            self._prior_active_state = self._status
            self._status = InvestigationStatus.PAUSED

    @workflow.signal
    def resume_investigation(self, signal: ResumeInvestigationSignal) -> None:
        """Atomic resume signal handler."""
        if self._status == InvestigationStatus.PAUSED:
            self._is_paused = False
            target = self._prior_active_state or InvestigationStatus.PLANNING
            self._status = target

    @workflow.signal
    def cancel_investigation(self, signal: CancelInvestigationSignal) -> None:
        """Atomic cancellation signal handler."""
        if self._status in (
            InvestigationStatus.COMPLETED,
            InvestigationStatus.FAILED,
            InvestigationStatus.CANCELLED,
        ):
            return
        self._is_cancelled = True
        self._cancel_reason = signal.reason
        self._cancelled_by = signal.cancelled_by
        self._status = InvestigationStatus.CANCELLED

    # =========================================================================
    # Query Handlers (§6.2)
    # =========================================================================

    @workflow.query
    def get_investigation_state(self) -> InvestigationState:
        """Query handler returning current sanitized lifecycle state."""
        return InvestigationState(
            investigation_id=self._input.investigation_id if self._input else "",
            tenant_id=self._input.tenant_id if self._input else "",
            status=self._status,
            prior_active_state=self._prior_active_state,
            budget=self._budget,
            current_step=self._current_step,
            error_code=self._error_code,
            error_message=self._error_message,
            pause_reason=self._pause_reason,
            paused_by=self._paused_by,
            cancel_reason=self._cancel_reason,
            cancelled_by=self._cancelled_by,
            manifest=self._manifest,
        )

    @workflow.query
    def get_progress(self) -> dict[str, Any]:
        """Query handler returning progress counters."""
        pending = max(0, self._total_tasks - self._completed_tasks - self._running_tasks)
        return {
            "total_tasks": self._total_tasks,
            "completed_tasks": self._completed_tasks,
            "running_tasks": self._running_tasks,
            "pending_tasks": pending,
            "status": self._status.value,
            "current_step": self._current_step,
        }


__all__ = ["InvestigationWorkflow"]
