"""
RevPilot AI — Action Intent, Ledger, and Dry-Run Domain Contracts
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.2, §3.3
Conforms to INV-ACT-001..004, AC-009, and ADR-0001.
"""

from __future__ import annotations
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError


class ActionClassification(str, Enum):
    """Reversibility and compensation semantics for governed actions."""
    REVERSIBLE = "REVERSIBLE"
    COMPENSATABLE = "COMPENSATABLE"
    PARTIALLY_COMPENSATABLE = "PARTIALLY_COMPENSATABLE"
    IRREVERSIBLE = "IRREVERSIBLE"
    MANUAL_RECONCILIATION = "MANUAL_RECONCILIATION"


ActionIntentStatus = Literal["INITIALIZED", "DISPATCHED", "COMPLETED", "FAILED", "RECONCILING"]
ActionLedgerStatus = Literal["STARTED", "SUCCESS", "PROVIDER_ERROR", "TIMEOUT_UNKNOWN", "RECONCILED", "COMPENSATED"]


class ActionIntentRecord(BaseModel):
    """
    Durable intent to execute an approved action, protected by tenant-scoped idempotency.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    intent_id: UUIDv7
    tenant_id: TenantId
    approval_id: UUIDv7
    idempotency_key: str = Field(min_length=1)
    action_type: str
    classification: ActionClassification
    target_set_count: int = Field(ge=0)
    payload_digest: str
    is_dry_run: bool = False
    status: ActionIntentStatus = "INITIALIZED"
    created_at: UtcDateTime


class ActionLedgerRecord(BaseModel):
    """
    Immutable journal entry tracking each physical or simulated dispatch attempt.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    ledger_id: UUIDv7
    tenant_id: TenantId
    intent_id: UUIDv7
    attempt_number: int = Field(ge=1)
    idempotency_key: str
    provider_name: str
    request_digest: str
    response_digest: str | None = None
    http_status_code: int | None = None
    provider_tx_id: str | None = None
    execution_status: ActionLedgerStatus = "STARTED"
    error_code: str | None = None
    started_at: UtcDateTime
    completed_at: UtcDateTime | None = None


class DryRunSimulationResult(BaseModel):
    """
    Output manifest of a dry-run simulation evaluating exact validation parity with 0 side effects.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    intent_id: UUIDv7
    action_type: str
    is_dry_run: bool = True
    simulated_impact: dict[str, Any]
    simulated_cost_usd: Decimal = Field(ge=Decimal("0.0"))
    simulated_blast_radius: int = Field(ge=0)
    provider_requirements: dict[str, Any]
    zero_side_effect_verified: bool = True
    simulated_at: UtcDateTime


class ActionError(DomainError):
    """Domain error during action intent, ledger, or dry-run execution."""

    def __init__(
        self,
        code: str = "ERR_ACTION_ERROR",
        message: str = "Action execution failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)
