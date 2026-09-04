"""
RevPilot AI — Action Outcome and Outbox Event Domain Contracts
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §2, §3
Specification: docs/26-api/EVENT-CONTRACTS.md §8
Conforms to INV-AUD-001, INV-AI-001, and NFR-OBS-001.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.errors import DomainError
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


class ActionOutcomeError(DomainError):
    """Base domain error for action outcome recording and evaluation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="ERR_ACTION_OUTCOME_ERROR", message=message, details=details, retryable=False)


class OutcomeSegregationViolationError(DomainError):
    """Action outcome cannot trigger automated model promotion or policy relaxation (INV-AI-001)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="ERR_OUTCOME_SEGREGATION_VIOLATION",
            message=message,
            details=details,
            retryable=False,
        )


class ActionOutcomeRecord(BaseModel):
    """
    Realized financial and retention outcome attributed to an approved action intent.
    Net ROI is strictly computed as (observed_revenue_usd - actual_cost_usd).
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    outcome_id: UUIDv7
    tenant_id: TenantId
    intent_id: UUIDv7
    approval_id: UUIDv7
    customer_id: str = Field(min_length=1)
    observed_revenue_usd: Decimal
    expected_revenue_usd: Decimal
    actual_cost_usd: Decimal
    net_roi_usd: Decimal
    created_at: UtcDateTime


class ActionEventEnvelope(BaseModel):
    """
    Canonical transactional event envelope strictly conforming to EVENT-CONTRACTS.md §8.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    event_id: str = Field(min_length=1)
    event_type: str = Field(default="action.completed.v1")
    occurred_at: UtcDateTime
    producer: str = Field(default="revpilot.modules.tool_gateway")
    aggregate_id: str = Field(min_length=1)
    aggregate_version: int = Field(default=1, ge=1)
    tenant_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    causation_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    payload: dict[str, Any]
