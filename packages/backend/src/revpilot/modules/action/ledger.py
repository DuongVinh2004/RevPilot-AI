"""
RevPilot AI — Action Intent and Ledger State Service
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.2, §3.3, §4
Conforms to INV-ACT-001..004, AC-009, and ADR-0001.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any

from revpilot.shared.identifiers import UUIDv7
from revpilot.shared.context import TenantContext
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.approval.domain import ApprovalRequestRecord, ApprovalStatus
from revpilot.modules.action.domain import (
    ActionIntentRecord,
    ActionLedgerRecord,
    ActionClassification,
    ActionLedgerStatus,
    DryRunSimulationResult,
    ActionError,
)
from revpilot.modules.action.ports import ActionIntentRepository, ActionLedgerRepository
from revpilot.modules.action.dryrun import DryRunSimulator


class ActionLedgerService:
    """
    Coordinates action intent creation with tenant-scoped idempotency,
    dry-run execution parity, and journaled dispatch attempt progression.
    """

    def __init__(
        self,
        intent_repo: ActionIntentRepository,
        ledger_repo: ActionLedgerRepository,
    ) -> None:
        self._intent_repo = intent_repo
        self._ledger_repo = ledger_repo

    async def create_intent(
        self,
        ctx: TenantContext,
        approval: ApprovalRequestRecord,
        idempotency_key: str,
        classification: ActionClassification,
        is_dry_run: bool = False,
    ) -> ActionIntentRecord:
        """
        Create a new action intent with strict idempotency (INV-ACT-001).
        Duplicate submissions with identical idempotency key return existing record.
        """
        # 1. Tenant boundary validation
        if str(ctx.tenant_id) != str(approval.tenant_id):
            raise ActionError(
                code="ERR_TENANT_MISMATCH",
                message="Tenant context does not match approval request tenant",
            )

        # 2. Idempotency check: return existing intent if key matches
        existing = await self._intent_repo.get_by_idempotency_key(
            tenant_id=ctx.tenant_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return existing

        # 3. Approval status check (must be APPROVED unless dry-run)
        if not is_dry_run and approval.status != ApprovalStatus.APPROVED:
            raise ActionError(
                code="ERR_APPROVAL_NOT_GRANTED",
                message=f"Cannot initialize action intent for unapproved request in status {approval.status}",
            )

        intent = ActionIntentRecord(
            intent_id=UUIDv7.generate(),
            tenant_id=ctx.tenant_id,
            approval_id=approval.approval_id,
            idempotency_key=idempotency_key,
            action_type=approval.action_type,
            classification=classification,
            target_set_count=len(approval.target_entity_refs),
            payload_digest=approval.payload_digest,
            is_dry_run=is_dry_run,
            status="INITIALIZED",
            created_at=UtcDateTime.now(),
        )
        await self._intent_repo.save(intent)
        return intent

    async def execute_dry_run(
        self,
        ctx: TenantContext,
        intent: ActionIntentRecord,
        payload: dict[str, Any],
        cost_usd: Decimal,
        targets: list[str],
    ) -> DryRunSimulationResult:
        """
        Execute pre-dispatch simulation for the intent (AC-009).
        Zero physical side-effects.
        """
        if str(ctx.tenant_id) != str(intent.tenant_id):
            raise ActionError(code="ERR_TENANT_MISMATCH", message="Tenant context mismatch")
        return DryRunSimulator.simulate(
            intent=intent,
            payload=payload,
            cost_usd=cost_usd,
            targets=targets,
        )

    async def record_attempt_start(
        self,
        ctx: TenantContext,
        intent_id: UUIDv7,
        idempotency_key: str,
        provider_name: str,
        request_digest: str,
    ) -> ActionLedgerRecord:
        """
        Record the start of an outbound dispatch attempt in the immutable action ledger.
        """
        intent = await self._intent_repo.get(ctx.tenant_id, intent_id)
        if intent is None:
            raise ActionError(code="ERR_INTENT_NOT_FOUND", message="Action intent not found")

        # Determine attempt number
        existing_attempts = await self._ledger_repo.list_by_intent(ctx.tenant_id, intent_id)
        attempt_number = len(existing_attempts) + 1

        ledger_rec = ActionLedgerRecord(
            ledger_id=UUIDv7.generate(),
            tenant_id=ctx.tenant_id,
            intent_id=intent_id,
            attempt_number=attempt_number,
            idempotency_key=idempotency_key,
            provider_name=provider_name,
            request_digest=request_digest,
            execution_status="STARTED",
            started_at=UtcDateTime.now(),
        )
        await self._ledger_repo.save(ledger_rec)

        # Update intent status to DISPATCHED
        if intent.status == "INITIALIZED":
            updated_intent = intent.model_copy(update={"status": "DISPATCHED"})
            await self._intent_repo.update(updated_intent)

        return ledger_rec

    async def record_attempt_completion(
        self,
        ctx: TenantContext,
        ledger_id: UUIDv7,
        status: ActionLedgerStatus,
        response_digest: str | None = None,
        http_status_code: int | None = None,
        tx_id: str | None = None,
        error_code: str | None = None,
    ) -> ActionLedgerRecord:
        """
        Record final attempt outcome and propagate progression to parent intent.
        """
        ledger_rec = await self._ledger_repo.get(ctx.tenant_id, ledger_id)
        if ledger_rec is None:
            raise ActionError(code="ERR_LEDGER_NOT_FOUND", message="Action ledger record not found")

        completed_at = UtcDateTime.now()
        updated_rec = ledger_rec.model_copy(
            update={
                "execution_status": status,
                "response_digest": response_digest,
                "http_status_code": http_status_code,
                "provider_tx_id": tx_id,
                "error_code": error_code,
                "completed_at": completed_at,
            }
        )
        await self._ledger_repo.update(updated_rec)

        # Update parent intent state
        intent = await self._intent_repo.get(ctx.tenant_id, ledger_rec.intent_id)
        if intent is not None:
            if status == "SUCCESS":
                await self._intent_repo.update(intent.model_copy(update={"status": "COMPLETED"}))
            elif status == "PROVIDER_ERROR":
                await self._intent_repo.update(intent.model_copy(update={"status": "FAILED"}))
            elif status == "TIMEOUT_UNKNOWN":
                await self._intent_repo.update(intent.model_copy(update={"status": "RECONCILING"}))

        return updated_rec
