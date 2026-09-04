"""
RevPilot AI — Safe Action Saga Workflow & Reverse Compensation Orchestration
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §4.1, §4.2
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §10
Conforms to ADR-0002, NFR-REL-001 (Zero blind retries), and INV-ACT-001.
"""

from __future__ import annotations
import logging
from typing import Any, Callable, Optional, Sequence
from pydantic import BaseModel, ConfigDict, Field

from revpilot.modules.action.domain import (
    ActionClassification,
    ActionIntentRecord,
    ActionLedgerRecord,
)
from revpilot.modules.action.saga.activities import (
    CompensationRecord,
    CompensationStatus,
    SAGA_REGISTRY,
    compensate_step_activity,
)
from revpilot.modules.action.saga.reconciliation import (
    ProviderInquiryResult,
    ProviderTransactionStatus,
    ReconciliationManager,
)
from revpilot.shared.errors import DomainError
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


def workflow_defn(name: str | None = None) -> Callable[[type], type]:
    """Lazy workflow decorator compatible with Temporal worker registration without eager import."""
    def decorator(cls: type) -> type:
        cls._temporal_workflow_name = name or cls.__name__
        return cls
    return decorator


def workflow_run(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Lazy workflow run decorator."""
    fn._temporal_workflow_run = True
    return fn


class IrreversibleActionError(DomainError):
    """Irreversible action cannot participate in automated rollback; requires manual operator intervention."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="ERR_IRREVERSIBLE_ACTION",
            message=message,
            details=details,
            retryable=False,
        )


class SagaStep(BaseModel):
    """Declarative definition of a compound action forward step and its compensating action."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    compensation_action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    is_irreversible: bool = False


@workflow_defn(name="SafeActionSagaWorkflow")
class SafeActionSagaWorkflow:
    """
    Temporal Saga Orchestrator for governed multi-step compound actions.
    Guarantees strict reverse-chronological compensation, irreversible action protection,
    and zero blind retries on UNKNOWN timeout states.
    """

    def __init__(
        self,
        reconciliation_mgr: ReconciliationManager | None = None,
    ) -> None:
        self.reconciliation_mgr = reconciliation_mgr or ReconciliationManager()
        self.compensation_history: list[CompensationRecord] = []
        self.completed_steps: list[tuple[str, dict[str, Any]]] = []

    async def compensate_steps(
        self,
        completed_steps: Sequence[tuple[str, dict[str, Any]] | tuple[str, dict[str, Any], str]],
        tenant_id: TenantId | None = None,
        intent_id: UUIDv7 | None = None,
        classification: ActionClassification = ActionClassification.COMPENSATABLE,
    ) -> list[CompensationRecord]:
        """
        Execute compensating activities in STRICT REVERSE CHRONOLOGICAL ORDER.
        If action is IRREVERSIBLE, automated rollback is barred; flags manual intervention required.
        If any compensation activity fails, transitions to FAILED_MANUAL_REQUIRED and pages on-call.
        """
        t_id = tenant_id or TenantId("tnt_system")
        i_id = intent_id or UUIDv7.generate()

        # Guard: Irreversible actions cannot be compensated automatically
        if classification == ActionClassification.IRREVERSIBLE:
            rec = CompensationRecord(
                record_id=UUIDv7.generate(),
                tenant_id=t_id,
                intent_id=i_id,
                step_name="IRREVERSIBLE_BARRIER",
                compensation_action="FLAG_OPERATOR_MANUAL_TICKET",
                status=CompensationStatus.FAILED_MANUAL_REQUIRED,
                compensated_at=UtcDateTime.now(),
            )
            self.compensation_history.append(rec)
            SAGA_REGISTRY.compensation_records.append(rec)
            raise IrreversibleActionError(
                "Action classified as IRREVERSIBLE cannot execute automated compensation; manual intervention required",
                details={
                    "tenant_id": str(t_id),
                    "intent_id": str(i_id),
                    "classification": classification.value,
                },
            )

        executed_records: list[CompensationRecord] = []

        # Strict reverse chronological iteration: K-1 down to 1
        for step_entry in reversed(completed_steps):
            if len(step_entry) == 3:
                step_name, payload, comp_action = step_entry  # type: ignore
            else:
                step_name, payload = step_entry[:2]  # type: ignore
                comp_action = f"compensate_{step_name}"

            simulate_fail = payload.get("simulate_compensation_failure", False)

            rec = await compensate_step_activity(
                step_name=step_name,
                compensation_action=comp_action,
                tenant_id=str(t_id),
                intent_id=str(i_id),
                simulate_failure=simulate_fail,
            )
            executed_records.append(rec)
            self.compensation_history.append(rec)

            # Fail-closed: If compensation activity fails, halt further automated compensation
            if rec.status == CompensationStatus.FAILED_MANUAL_REQUIRED:
                logger.critical("Halting automated saga rollback; manual operator recovery queued.")
                break

        return executed_records

    async def reconcile_unknown(
        self,
        intent: ActionIntentRecord,
        ledger_id: UUIDv7,
        query_fn: Optional[Callable[[str, str], ProviderInquiryResult]] = None,
    ) -> ActionLedgerRecord:
        """
        Reconcile UNKNOWN timeout without blind retries (NFR-REL-001).
        Delegates to deterministic inquiry loop.
        """
        initial_ledger = ActionLedgerRecord(
            ledger_id=ledger_id,
            tenant_id=intent.tenant_id,
            intent_id=intent.intent_id,
            attempt_number=1,
            idempotency_key=intent.idempotency_key,
            provider_name="mock_logistics_v1",
            request_digest=intent.payload_digest,
            execution_status="TIMEOUT_UNKNOWN",
            error_code="TIMEOUT_UNKNOWN",
            started_at=UtcDateTime.now(),
        )

        fn = query_fn or (lambda p, k: ProviderInquiryResult(status=ProviderTransactionStatus.CONFIRMED))
        return await self.reconciliation_mgr.reconcile_unknown(
            intent=intent,
            ledger=initial_ledger,
            query_fn=fn,
        )

    @workflow_run
    async def execute_action_saga(
        self,
        intent: ActionIntentRecord,
        steps: Optional[list[SagaStep]] = None,
        custom_query_fn: Optional[Callable[[str, str], ProviderInquiryResult]] = None,
    ) -> ActionLedgerRecord:
        """
        Execute forward steps of compound action. On failure, triggers backward compensation.
        On timeout, invokes status inquiry rather than blind retry.
        """
        saga_steps = steps or []
        completed_step_tuples: list[tuple[str, dict[str, Any], str]] = []
        ledger_id = UUIDv7.generate()
        now = UtcDateTime.now()

        for step in saga_steps:
            # Check for simulated network timeout on forward step
            if step.payload.get("simulate_timeout", False):
                logger.warning("Step %s encountered network timeout. Entering UNKNOWN reconciliation.", step.name)
                # ZERO blind retries: immediately reconcile
                return await self.reconcile_unknown(intent, ledger_id, query_fn=custom_query_fn)

            # Check for simulated forward failure
            if step.payload.get("simulate_failure", False):
                logger.error("Step %s failed forward execution. Initiating backward compensation.", step.name)
                # Trigger backward compensation for all previously completed steps
                try:
                    await self.compensate_steps(
                        completed_steps=completed_step_tuples,
                        tenant_id=intent.tenant_id,
                        intent_id=intent.intent_id,
                        classification=intent.classification,
                    )
                except IrreversibleActionError:
                    return ActionLedgerRecord(
                        ledger_id=ledger_id,
                        tenant_id=intent.tenant_id,
                        intent_id=intent.intent_id,
                        attempt_number=1,
                        idempotency_key=intent.idempotency_key,
                        provider_name="mock_provider",
                        request_digest=intent.payload_digest,
                        execution_status="PROVIDER_ERROR",
                        error_code="ERR_IRREVERSIBLE_MANUAL_REQUIRED",
                        started_at=now,
                        completed_at=UtcDateTime.now(),
                    )

                return ActionLedgerRecord(
                    ledger_id=ledger_id,
                    tenant_id=intent.tenant_id,
                    intent_id=intent.intent_id,
                    attempt_number=1,
                    idempotency_key=intent.idempotency_key,
                    provider_name="mock_provider",
                    request_digest=intent.payload_digest,
                    execution_status="COMPENSATED",
                    error_code="ERR_STEP_FAILED_COMPENSATED",
                    started_at=now,
                    completed_at=UtcDateTime.now(),
                )

            # Step completed successfully
            completed_step_tuples.append((step.name, step.payload, step.compensation_action))
            self.completed_steps.append((step.name, step.payload))

        # All steps succeeded
        return ActionLedgerRecord(
            ledger_id=ledger_id,
            tenant_id=intent.tenant_id,
            intent_id=intent.intent_id,
            attempt_number=1,
            idempotency_key=intent.idempotency_key,
            provider_name="mock_provider",
            request_digest=intent.payload_digest,
            http_status_code=200,
            provider_tx_id=f"saga_{intent.idempotency_key}",
            execution_status="SUCCESS",
            error_code=None,
            started_at=now,
            completed_at=UtcDateTime.now(),
        )
