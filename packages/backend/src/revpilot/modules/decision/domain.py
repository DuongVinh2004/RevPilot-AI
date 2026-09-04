"""
RevPilot AI — Decision Intelligence Domain Models and Contracts
Specification: docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md §3, §4
Conforms to BR-002, BR-005, FR-DEC-001, INV-AI-001, INV-ACT-001, INV-COST-001, INV-TEN-001..003, AC-007, and ADR-0003.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError
from revpilot.modules.constraints.domain import (
    CandidateIntervention,
    BudgetLedgerEntry,
)

RecommendationStatus = Literal["RECOMMENDED", "ABSTAINED", "NEED_MORE_EVIDENCE", "BLOCKED"]
RiskTier = Literal["LOW", "MEDIUM", "HIGH"]


class DecisionCandidate(CandidateIntervention):
    """Candidate intervention augmented with causal uplift estimates and uncertainty."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    expected_cate: float = Field(default=0.0)
    cate_standard_error: float = Field(default=0.0, ge=0.0)
    confidence_interval_95: tuple[float, float] = Field(default=(0.0, 0.0))
    overlap_satisfied: bool = True
    custom_risk_penalty_usd: Decimal | None = None


class DecisionRequest(BaseModel):
    """Canonical request payload initiating a 12-step decision intelligence run."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    request_id: UUIDv7
    tenant_id: TenantId
    customer_id: str
    customer_tier: str
    investigation_id: UUIDv7 | None = None
    as_of_time: UtcDateTime
    candidates: list[DecisionCandidate]
    customer_arr_usd: Decimal = Field(ge=Decimal("0.0"))
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
    risk_aversion_lambda: float = Field(default=0.50, ge=0.0)
    uncertainty_lambda: float = Field(default=0.50, ge=0.0)


class RankedAlternative(BaseModel):
    """Evaluation breakdown and ranking position for an eligible candidate intervention."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    candidate_id: str
    name: str
    expected_utility_usd: Decimal
    expected_cate: float
    incremental_gain_usd: Decimal
    direct_cost_usd: Decimal
    risk_penalty_usd: Decimal
    uncertainty_penalty_usd: Decimal
    confidence_interval_95: tuple[float, float]
    rank: int


class RecommendationRecord(BaseModel):
    """Canonical immutable output of the decision intelligence engine."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    recommendation_id: UUIDv7
    request_id: UUIDv7
    tenant_id: TenantId
    selected_candidate_id: str | None = None
    expected_utility_usd: Decimal
    expected_incremental_retention_rate: float
    direct_cost_usd: Decimal
    risk_penalty_usd: Decimal
    uncertainty_penalty_usd: Decimal
    confidence_interval_95: tuple[float, float]
    ranked_alternatives: list[dict[str, Any]]
    ineligible_candidates: dict[str, list[str]]
    status: RecommendationStatus
    decision_digest: str
    created_at: UtcDateTime


class DecisionError(DomainError):
    """Domain error during decision intelligence processing."""

    def __init__(
        self,
        code: str = "ERR_DECISION_ENGINE_ERROR",
        message: str = "Decision engine failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)
