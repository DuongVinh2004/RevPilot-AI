"""
RevPilot AI — Investigation Domain Entities, Value Objects, and Manifest Contracts
Conforms to docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §3–§4,
docs/06-agent-platform/MULTI-AGENT-SPEC.md §2, and TASK-P03-001.
"""

from __future__ import annotations
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from typing_extensions import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.investigation.domain.errors import (
    BudgetExceededError,
    TemporalValidationException,
)


class InvestigationStatus(str, Enum):
    """
    Strict 9-state lifecycle status for investigations.
    Conforms to TEMPORAL-WORKFLOW-SPEC.md §4 and INV-WF-001.
    """
    INITIALIZING = "INITIALIZING"
    PLANNING = "PLANNING"
    GATHERING_EVIDENCE = "GATHERING_EVIDENCE"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class BudgetState(BaseModel):
    """
    Tracks and enforces financial and compute resource quotas for an investigation.
    Enforces INV-COST-001 with default $2.00 allocated and $5.00 hard stop limit.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    allocated_usd: Decimal = Field(default=Decimal("2.00"))
    spent_usd: Decimal = Field(default=Decimal("0.00"))
    hard_stop_usd: Decimal = Field(default=Decimal("5.00"))
    allocated_tokens: int = Field(default=100_000)
    spent_tokens: int = Field(default=0)
    allocated_tool_calls: int = Field(default=20)
    spent_tool_calls: int = Field(default=0)

    @model_validator(mode="after")
    def validate_budget_bounds(self) -> Self:
        if self.spent_usd > self.hard_stop_usd:
            raise BudgetExceededError(
                f"Budget spend ${self.spent_usd} exceeds hard stop limit of ${self.hard_stop_usd}",
                details={
                    "spent_usd": str(self.spent_usd),
                    "hard_stop_usd": str(self.hard_stop_usd),
                },
            )
        return self

    def record_spend(
        self,
        usd: Decimal = Decimal("0.00"),
        tokens: int = 0,
        tool_calls: int = 0,
    ) -> None:
        """
        Record operational spend and halt if hard stop limit is breached.
        Raises BudgetExceededError when spend > hard_stop_usd.
        """
        candidate_usd = self.spent_usd + Decimal(str(usd))
        if candidate_usd > self.hard_stop_usd:
            raise BudgetExceededError(
                f"Recording spend of ${usd} brings total ${candidate_usd} over hard stop limit of ${self.hard_stop_usd}",
                details={
                    "current_spent_usd": str(self.spent_usd),
                    "attempted_usd": str(usd),
                    "hard_stop_usd": str(self.hard_stop_usd),
                },
            )
        self.spent_usd = candidate_usd
        self.spent_tokens += tokens
        self.spent_tool_calls += tool_calls


class InvestigationScope(BaseModel):
    """Categorical dimension filters and regional boundaries for an investigation."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    region: Optional[str] = None
    tier: Optional[str] = None
    dimension_filters: dict[str, Any] = Field(default_factory=dict)


class Investigation(BaseModel):
    """
    Core aggregate root representing a governed, tenant-isolated investigation.
    Enforces INV-TEN-001, INV-WF-001, and anti-leakage temporal bounds (INV-DATA-001).
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    investigation_id: str
    tenant_id: TenantId
    principal_id: PrincipalId
    metric_name: str
    anomaly_id: Optional[str] = None
    scope: InvestigationScope = Field(default_factory=InvestigationScope)
    window_start: UtcDateTime
    window_end: UtcDateTime
    as_of_time: UtcDateTime
    status: InvestigationStatus = InvestigationStatus.INITIALIZING
    budget: BudgetState = Field(default_factory=BudgetState)
    created_at: UtcDateTime = Field(default_factory=UtcDateTime.now)
    updated_at: UtcDateTime = Field(default_factory=UtcDateTime.now)

    @model_validator(mode="after")
    def validate_temporal_boundaries(self) -> Self:
        if self.window_end.value > self.as_of_time.value:
            raise TemporalValidationException(
                f"Temporal window end ({self.window_end.isoformat()}) exceeds as_of_time ({self.as_of_time.isoformat()})",
                details={
                    "window_end": self.window_end.isoformat(),
                    "as_of_time": self.as_of_time.isoformat(),
                },
            )
        return self


class InvestigationManifest(BaseModel):
    """
    Cryptographically sealed summary manifest emitted upon investigation conclusion.
    Conforms to TEMPORAL-WORKFLOW-SPEC.md §3 and EVENT-CONTRACTS.md §5.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    investigation_id: str
    tenant_id: TenantId
    top_hypothesis_id: Optional[str]
    bundle_digest: str
    cogs_usd: Decimal
    duration_seconds: int
    sealed_at: UtcDateTime


__all__ = [
    "InvestigationStatus",
    "BudgetState",
    "InvestigationScope",
    "Investigation",
    "InvestigationManifest",
]
