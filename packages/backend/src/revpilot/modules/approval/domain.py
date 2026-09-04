"""
RevPilot AI — Governed Approval Domain Models and Lifecycle Invariants
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1, §3.1
Conforms to INV-ACT-001..004, INV-IAM-001..002, INV-TEN-001..003, AC-008, and ADR-0003.
"""

from __future__ import annotations
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError


class ApprovalStatus(str, Enum):
    """Canonical lifecycle states of an approval request."""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AMENDED = "AMENDED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class ApprovalRequestRecord(BaseModel):
    """
    Immutable, cryptographic record representing a human-in-the-loop approval request.
    Enforces INV-ACT-002: Exact payload digest binding to physical execution.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    approval_id: UUIDv7
    tenant_id: TenantId
    decision_id: UUIDv7
    investigation_id: UUIDv7 | None = None
    action_type: str
    action_version: str = "1.0.0"
    target_customer_id: str
    target_entity_refs: list[str]
    action_payload: dict[str, Any]
    payload_digest: str
    policy_digest: str
    estimated_cost_usd: Decimal = Field(ge=Decimal("0.0"))
    reserved_budget_usd: Decimal = Field(ge=Decimal("0.0"))
    risk_tier: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    required_approval_tier: int = Field(ge=1, le=3)
    approver_principal_id: str | None = None
    approval_timestamp: UtcDateTime | None = None
    rejection_reason: str | None = None
    revocation_reason: str | None = None
    expiry_time: UtcDateTime
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision_digest: str
    correlation_id: UUIDv7
    causation_id: UUIDv7
    created_at: UtcDateTime
    superseded_by: UUIDv7 | None = None


class ApprovalError(DomainError):
    """Base domain error for policy, approval, and safe action violations."""

    def __init__(
        self,
        code: str = "ERR_APPROVAL_ERROR",
        message: str = "Approval operation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)
