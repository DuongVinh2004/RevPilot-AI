"""
RevPilot AI — Hard Business Constraints Domain Models and Invariants
Specification: docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md §2, §3
Specification: docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md §4
Conforms to BR-005, FR-DEC-001, INV-COST-001, INV-TEN-001..003, NFR-COST-001, and AC-007.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError


class CandidateIntervention(BaseModel):
    """Business intervention candidate evaluated for eligibility and utility."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    candidate_id: str
    name: str
    action_type: str
    estimated_cost_usd: Decimal = Field(ge=Decimal("0.0"))
    eligible_tiers: list[str]
    max_frequency_days: int = Field(ge=0)
    risk_tier: Literal["LOW", "MEDIUM", "HIGH"]


class BudgetLedgerEntry(BaseModel):
    """Monetary ledger entry recording available and committed funds."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    tenant_id: TenantId
    ledger_date: str
    total_allocated_usd: Decimal = Field(ge=Decimal("0.0"))
    committed_expenditure_usd: Decimal = Field(ge=Decimal("0.0"))
    remaining_balance_usd: Decimal = Field(ge=Decimal("0.0"))
    version: int = Field(ge=1)


class ConstraintEvaluatorRequest(BaseModel):
    """Context and parameters required to audit a candidate against hard constraints."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    tenant_id: TenantId
    customer_id: str
    customer_tier: str
    intervention: CandidateIntervention
    current_time: UtcDateTime
    budget_ledger: BudgetLedgerEntry
    active_capacity_count: int = Field(default=0, ge=0)
    max_capacity_limit: int = Field(default=10, ge=1)
    customer_history_timestamps: list[UtcDateTime] = Field(default_factory=list)
    quarterly_history_timestamps: list[UtcDateTime] = Field(default_factory=list)
    max_quarterly_frequency: int = Field(default=3, ge=1)
    customer_opt_out: bool = False
    is_excluded: bool = False
    incident_treated_count: int = Field(default=0, ge=0)
    max_blast_radius: int = Field(default=500, ge=1)
    feature_timestamp: UtcDateTime
    max_feature_staleness_hours: int = Field(default=24, ge=1)


class ConstraintEvaluationOutcome(BaseModel):
    """Audit result documenting eligibility status, passed checks, and violations."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    is_eligible: bool
    passed_constraints: list[str]
    violated_constraints: list[str]
    evaluated_at: UtcDateTime


class ConstraintViolationError(DomainError):
    """Domain error during constraint evaluation."""

    def __init__(
        self,
        code: str = "ERR_CONSTRAINT_VIOLATION",
        message: str = "Constraint evaluation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)
