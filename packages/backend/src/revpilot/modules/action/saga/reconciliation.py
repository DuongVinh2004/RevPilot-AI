"""
RevPilot AI — UNKNOWN Provider Transaction Reconciliation Protocol
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §4.1
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §10.2
Specification: docs/26-api/EVENT-CONTRACTS.md §8
Conforms to NFR-REL-001 (Zero blind retries).
"""

from __future__ import annotations
from enum import Enum
import logging
from typing import Any, Callable, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.modules.action.domain import ActionIntentRecord, ActionLedgerRecord
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


class ProviderTransactionStatus(str, Enum):
    """Deterministic resolution states returned by downstream status inquiry."""
    CONFIRMED = "CONFIRMED"
    NO_RECORD = "NO_RECORD"
    INCONCLUSIVE = "INCONCLUSIVE"


class ProviderInquiryResult(BaseModel):
    """Result of querying downstream provider transaction status by idempotency key."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    status: ProviderTransactionStatus
    provider_tx_id: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class OutboxEvent(BaseModel):
    """Immutable outbox event emitted for operator escalation."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    event_id: UUIDv7
    event_type: str = "action.reconciliation_required.v1"
    occurred_at: UtcDateTime
    tenant_id: TenantId
    aggregate_id: str
    payload: dict[str, Any]


class ReconciliationManager:
    """
    Manages deterministic inquiry loops for UNKNOWN timeout states.
    Strictly forbids blind retries (NFR-REL-001).
    """

    def __init__(self) -> None:
        self.emitted_outbox_events: list[OutboxEvent] = []
        self.inquiry_history: list[dict[str, Any]] = []

    async def reconcile_unknown(
        self,
        intent: ActionIntentRecord,
        ledger: ActionLedgerRecord,
        query_fn: Callable[[str, str], ProviderInquiryResult],
        max_attempts: int = 3,
    ) -> ActionLedgerRecord:
        """
        Execute deterministic query loop against downstream provider.
        - If CONFIRMED: ledger transitions to RECONCILED.
        - If NO_RECORD: ledger transitions to PROVIDER_ERROR with error_code FAILED_NO_DISPATCH (safe retry permitted).
        - If INCONCLUSIVE after max_attempts: ledger transitions to TIMEOUT_UNKNOWN with ERR_RECONCILIATION_REQUIRED,
          emits action.reconciliation_required.v1 outbox event, and parks workflow for SRE operations.
        """
        now = UtcDateTime.now()
        last_result: ProviderInquiryResult = ProviderInquiryResult(
            status=ProviderTransactionStatus.INCONCLUSIVE,
            details={"message": "Inquiry not started"},
        )

        for attempt in range(1, max_attempts + 1):
            self.inquiry_history.append({
                "attempt": attempt,
                "provider": ledger.provider_name,
                "idempotency_key": ledger.idempotency_key,
                "timestamp": now.isoformat(),
            })

            try:
                last_result = query_fn(ledger.provider_name, ledger.idempotency_key)
            except Exception as exc:
                logger.warning("Provider inquiry attempt %d threw error: %s", attempt, exc)
                last_result = ProviderInquiryResult(
                    status=ProviderTransactionStatus.INCONCLUSIVE,
                    details={"error": str(exc)},
                )

            # 1. Provider confirmed transaction
            if last_result.status == ProviderTransactionStatus.CONFIRMED:
                return ActionLedgerRecord(
                    ledger_id=ledger.ledger_id,
                    tenant_id=ledger.tenant_id,
                    intent_id=ledger.intent_id,
                    attempt_number=ledger.attempt_number,
                    idempotency_key=ledger.idempotency_key,
                    provider_name=ledger.provider_name,
                    request_digest=ledger.request_digest,
                    response_digest=ledger.response_digest,
                    http_status_code=200,
                    provider_tx_id=last_result.provider_tx_id or f"reconciled_{ledger.idempotency_key}",
                    execution_status="RECONCILED",
                    error_code=None,
                    started_at=ledger.started_at,
                    completed_at=UtcDateTime.now(),
                )

            # 2. Provider confirmed zero transaction occurred (safe retry permitted)
            if last_result.status == ProviderTransactionStatus.NO_RECORD:
                return ActionLedgerRecord(
                    ledger_id=ledger.ledger_id,
                    tenant_id=ledger.tenant_id,
                    intent_id=ledger.intent_id,
                    attempt_number=ledger.attempt_number,
                    idempotency_key=ledger.idempotency_key,
                    provider_name=ledger.provider_name,
                    request_digest=ledger.request_digest,
                    response_digest=ledger.response_digest,
                    http_status_code=ledger.http_status_code,
                    provider_tx_id=None,
                    execution_status="PROVIDER_ERROR",
                    error_code="FAILED_NO_DISPATCH",
                    started_at=ledger.started_at,
                    completed_at=UtcDateTime.now(),
                )

        # 3. Exhausted attempts with INCONCLUSIVE -> Escalation required
        escalation_event = OutboxEvent(
            event_id=UUIDv7.generate(),
            event_type="action.reconciliation_required.v1",
            occurred_at=UtcDateTime.now(),
            tenant_id=ledger.tenant_id,
            aggregate_id=str(ledger.ledger_id),
            payload={
                "intent_id": str(intent.intent_id),
                "ledger_id": str(ledger.ledger_id),
                "idempotency_key": ledger.idempotency_key,
                "provider_name": ledger.provider_name,
                "action_type": intent.action_type,
                "attempts": max_attempts,
                "reason": "Provider inquiry inconclusive after maximum attempts. Human SRE intervention required.",
                "last_inquiry_details": last_result.details,
            },
        )
        self.emitted_outbox_events.append(escalation_event)

        return ActionLedgerRecord(
            ledger_id=ledger.ledger_id,
            tenant_id=ledger.tenant_id,
            intent_id=ledger.intent_id,
            attempt_number=ledger.attempt_number,
            idempotency_key=ledger.idempotency_key,
            provider_name=ledger.provider_name,
            request_digest=ledger.request_digest,
            response_digest=ledger.response_digest,
            http_status_code=ledger.http_status_code,
            provider_tx_id=None,
            execution_status="TIMEOUT_UNKNOWN",
            error_code="ERR_RECONCILIATION_REQUIRED",
            started_at=ledger.started_at,
            completed_at=UtcDateTime.now(),
        )
