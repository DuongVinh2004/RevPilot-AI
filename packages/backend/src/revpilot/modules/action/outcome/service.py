"""
RevPilot AI — Action Outcome Measurement, FinOps Attribution & Transactional Outbox
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §2, §3
Specification: docs/26-api/EVENT-CONTRACTS.md §8
Conforms to INV-AUD-001, INV-AI-001, NFR-COST-001, and NFR-OBS-001.
"""

from __future__ import annotations
from decimal import Decimal
import logging
from typing import Any, Optional

from revpilot.modules.action.domain import ActionLedgerRecord
from revpilot.modules.action.outcome.audit import ActionAuditLogger, GLOBAL_AUDIT_LOGGER
from revpilot.modules.action.outcome.domain import (
    ActionEventEnvelope,
    ActionOutcomeError,
    ActionOutcomeRecord,
    OutcomeSegregationViolationError,
)
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import TenancyViolationError
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


class ActionOutcomeService:
    """
    Authoritative outcome measurement, FinOps ROI attribution, and outbox event publisher.
    Enforces atomic persistence and strict outcome segregation (INV-AI-001).
    """

    def __init__(
        self,
        audit_logger: ActionAuditLogger | None = None,
    ) -> None:
        self.audit_logger = audit_logger or GLOBAL_AUDIT_LOGGER
        self.outcome_store: dict[str, ActionOutcomeRecord] = {}
        self.outbox_events: list[ActionEventEnvelope] = []

    async def record_outcome(
        self,
        ctx: TenantContext,
        intent_id: UUIDv7,
        actual_cost: Decimal,
        observed_rev: Decimal,
        expected_rev: Decimal | None = None,
        customer_id: str | None = None,
        approval_id: UUIDv7 | None = None,
        trigger_model_promotion: bool = False,
        simulate_outbox_failure: bool = False,
    ) -> ActionOutcomeRecord:
        """
        Record realized revenue retention and compute Net ROI = (observed_revenue - actual_cost).
        Enforces INV-AI-001: Automated model promotion or policy relaxation from outcomes is forbidden.
        Enforces atomic rollback if outbox persistence fails.
        """
        if not ctx.is_active:
            raise TenancyViolationError(f"Tenant '{ctx.tenant_id}' is inactive")

        # Invariant: Outcome Segregation (INV-AI-001)
        if trigger_model_promotion:
            raise OutcomeSegregationViolationError(
                "Observed action outcomes cannot automatically trigger model promotion or policy relaxation (INV-AI-001)",
                details={"tenant_id": str(ctx.tenant_id), "intent_id": str(intent_id)},
            )

        now = UtcDateTime.now()
        outcome_id = UUIDv7.generate()
        exp_rev = expected_rev if expected_rev is not None else observed_rev
        app_id = approval_id or UUIDv7.generate()
        cust_id = customer_id or f"cust_{ctx.tenant_id}_generic"

        # Net ROI Calculation: (Observed Revenue - Actual Cost)
        net_roi = observed_rev - actual_cost

        record = ActionOutcomeRecord(
            outcome_id=outcome_id,
            tenant_id=ctx.tenant_id,
            intent_id=intent_id,
            approval_id=app_id,
            customer_id=cust_id,
            observed_revenue_usd=observed_rev,
            expected_revenue_usd=exp_rev,
            actual_cost_usd=actual_cost,
            net_roi_usd=net_roi,
            created_at=now,
        )

        # Atomic Transaction Simulation:
        # Prepare outbox event corresponding to outcome attribution
        outcome_event = ActionEventEnvelope(
            event_id=f"evt_{UUIDv7.generate()}",
            event_type="action.outcome.measured.v1",
            occurred_at=now,
            producer="revpilot.modules.tool_gateway",
            aggregate_id=str(outcome_id),
            tenant_id=str(ctx.tenant_id),
            correlation_id=str(UUIDv7.generate()),
            causation_id=str(intent_id),
            idempotency_key=f"outc_{intent_id}",
            payload={
                "outcome_id": str(outcome_id),
                "intent_id": str(intent_id),
                "approval_id": str(app_id),
                "net_roi_usd": str(net_roi),
                "actual_cost_usd": str(actual_cost),
                "observed_revenue_usd": str(observed_rev),
            },
        )

        # If transactional outbox insertion fails, rollback atomically
        if simulate_outbox_failure:
            logger.error("Outbox insertion failed. Rolling back transaction for outcome %s", outcome_id)
            raise ActionOutcomeError(
                "Transaction rollback: failed to append to outbox store",
                details={"outcome_id": str(outcome_id), "intent_id": str(intent_id)},
            )

        # Commit phase
        self.outcome_store[str(outcome_id)] = record
        self.outbox_events.append(outcome_event)

        # Emit unsampled audit log (INV-AUD-001)
        self.audit_logger.log_event(
            tenant_id=ctx.tenant_id,
            actor_id="system_finops_meter",
            event_type="action.outcome.measured",
            resource=f"action_outcome/{outcome_id}",
            action="record_outcome",
            outcome="SUCCESS",
            details={
                "outcome_id": str(outcome_id),
                "intent_id": str(intent_id),
                "approval_id": str(app_id),
                "net_roi_usd": str(net_roi),
            },
        )

        return record

    async def publish_completion_event(
        self,
        ctx: TenantContext,
        ledger: ActionLedgerRecord,
        approval_id: UUIDv7 | None = None,
        actual_cost_usd: Decimal | None = None,
        simulate_outbox_failure: bool = False,
    ) -> ActionEventEnvelope:
        """
        Publish action.completed.v1 event strictly conforming to EVENT-CONTRACTS.md §8.
        Fails closed and rolls back if outbox insertion fails.
        """
        if str(ctx.tenant_id) != str(ledger.tenant_id):
            raise TenancyViolationError(
                f"Tenant context '{ctx.tenant_id}' does not match ledger tenant '{ledger.tenant_id}'"
            )

        now = UtcDateTime.now()
        app_id = approval_id or UUIDv7.generate()
        cost_usd = actual_cost_usd if actual_cost_usd is not None else Decimal("0.00")

        event = ActionEventEnvelope(
            event_id=f"evt_{UUIDv7.generate()}",
            event_type="action.completed.v1",
            occurred_at=now,
            producer="revpilot.modules.tool_gateway",
            aggregate_id=str(ledger.ledger_id),
            aggregate_version=1,
            tenant_id=str(ctx.tenant_id),
            correlation_id=str(UUIDv7.generate()),
            causation_id=str(ledger.intent_id),
            idempotency_key=ledger.idempotency_key,
            payload={
                "intent_id": str(ledger.intent_id),
                "approval_id": str(app_id),
                "provider_name": ledger.provider_name,
                "provider_tx_id": ledger.provider_tx_id or f"tx_{ledger.idempotency_key}",
                "execution_status": ledger.execution_status,
                "http_status_code": ledger.http_status_code or 200,
                "actual_cost_usd": float(cost_usd),
            },
        )

        if simulate_outbox_failure:
            raise ActionOutcomeError(
                "Failed to publish completion event to outbox",
                details={"ledger_id": str(ledger.ledger_id)},
            )

        self.outbox_events.append(event)

        # Audit emission (INV-AUD-001)
        self.audit_logger.log_event(
            tenant_id=ctx.tenant_id,
            actor_id="tool_gateway_dispatch",
            event_type="action.completed",
            resource=f"action_ledger/{ledger.ledger_id}",
            action="publish_completion",
            outcome="SUCCESS",
            details={
                "ledger_id": str(ledger.ledger_id),
                "intent_id": str(ledger.intent_id),
                "provider_tx_id": ledger.provider_tx_id,
            },
        )

        return event
