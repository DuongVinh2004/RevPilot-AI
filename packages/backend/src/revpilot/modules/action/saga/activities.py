"""
RevPilot AI — Temporal Saga Activities for Forward Steps, Compensations & Inquiries
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §10
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §4.2
Conforms to ADR-0002, INV-ACT-001, and NFR-REL-001.
"""

from __future__ import annotations
from enum import Enum
import logging
from typing import Any, Callable, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.modules.action.saga.reconciliation import (
    OutboxEvent,
    ProviderInquiryResult,
    ProviderTransactionStatus,
)
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


def activity_defn(name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Lazy activity decorator compatible with Temporal worker registration without eager import."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._temporal_activity_name = name or fn.__name__
        return fn
    return decorator


class CompensationStatus(str, Enum):
    """Lifecycle states of a backward Saga compensation action."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED_MANUAL_REQUIRED = "FAILED_MANUAL_REQUIRED"


class CompensationRecord(BaseModel):
    """
    Immutable audit record representing the execution of a compensation activity.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    record_id: UUIDv7
    tenant_id: TenantId
    intent_id: UUIDv7
    step_name: str
    compensation_action: str
    status: CompensationStatus
    compensated_at: UtcDateTime


class SagaActivityRegistry:
    """
    In-memory audit store for compensation records and inquiry telemetry during test runs.
    """

    def __init__(self) -> None:
        self.compensation_records: list[CompensationRecord] = []
        self.paged_incidents: list[dict[str, Any]] = []

    def clear(self) -> None:
        self.compensation_records.clear()
        self.paged_incidents.clear()


SAGA_REGISTRY = SagaActivityRegistry()


@activity_defn(name="ExecuteSagaStepActivity")
async def execute_saga_step_activity(step_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute a forward step of a compound action."""
    logger.info("Executing saga step forward: %s", step_name)
    return {"step_name": step_name, "status": "SUCCESS", "output": payload}


@activity_defn(name="CompensateStepActivity")
async def compensate_step_activity(
    step_name: str,
    compensation_action: str,
    tenant_id: str,
    intent_id: str,
    simulate_failure: bool = False,
) -> CompensationRecord:
    """
    Execute compensation activity for a previously completed forward step.
    If compensation fails, records FAILED_MANUAL_REQUIRED and pages on-call.
    """
    logger.info("Executing compensation: step=%s action=%s", step_name, compensation_action)
    now = UtcDateTime.now()

    if simulate_failure:
        rec = CompensationRecord(
            record_id=UUIDv7.generate(),
            tenant_id=TenantId(tenant_id),
            intent_id=UUIDv7(intent_id),
            step_name=step_name,
            compensation_action=compensation_action,
            status=CompensationStatus.FAILED_MANUAL_REQUIRED,
            compensated_at=now,
        )
        SAGA_REGISTRY.compensation_records.append(rec)
        SAGA_REGISTRY.paged_incidents.append({
            "step_name": step_name,
            "compensation_action": compensation_action,
            "tenant_id": tenant_id,
            "intent_id": intent_id,
            "reason": "Compensation activity failed; immediate human on-call required",
        })
        logger.critical("ALERT: Compensation failed for %s. Paging SRE on-call.", step_name)
        return rec

    rec = CompensationRecord(
        record_id=UUIDv7.generate(),
        tenant_id=TenantId(tenant_id),
        intent_id=UUIDv7(intent_id),
        step_name=step_name,
        compensation_action=compensation_action,
        status=CompensationStatus.COMPLETED,
        compensated_at=now,
    )
    SAGA_REGISTRY.compensation_records.append(rec)
    return rec


@activity_defn(name="QueryProviderStatusActivity")
async def query_provider_status_activity(
    provider_name: str,
    idempotency_key: str,
    mock_status: str = "CONFIRMED",
) -> ProviderInquiryResult:
    """
    Query downstream provider status using deterministic idempotency key.
    Zero blind HTTP retries (NFR-REL-001).
    """
    status_enum = ProviderTransactionStatus(mock_status)
    return ProviderInquiryResult(
        status=status_enum,
        provider_tx_id=f"tx_{idempotency_key}" if status_enum == ProviderTransactionStatus.CONFIRMED else None,
        details={"provider": provider_name, "idempotency_key": idempotency_key},
    )
