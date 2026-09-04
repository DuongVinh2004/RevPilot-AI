"""
RevPilot AI — Investigation Workflow Signals, Inputs, and State Contracts
Conforms to docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §3, §4, §6 and INV-WF-001..002.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.modules.investigation.domain.models import (
    InvestigationStatus,
    BudgetState,
    InvestigationManifest,
)
from revpilot.modules.investigation.domain.errors import (
    BudgetExceededError,
    TemporalValidationException,
)
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import TenancyViolationError


class PauseInvestigationSignal(BaseModel):
    """Signal payload requesting workflow pause."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    reason: str
    paused_by: str


class ResumeInvestigationSignal(BaseModel):
    """Signal payload requesting workflow resume."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    resumed_by: str


class CancelInvestigationSignal(BaseModel):
    """Signal payload requesting immediate workflow cancellation."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    reason: str
    cancelled_by: str


class InvestigationWorkflowInput(BaseModel):
    """
    Immutable input envelope provided upon investigation initiation.
    Conforms to TEMPORAL-WORKFLOW-SPEC.md §3.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    investigation_id: str
    tenant_id: str
    principal_id: str
    correlation_id: str = ""
    causation_id: str = ""
    trigger_type: str = "ANALYST_REQUEST"
    anomaly_id: Optional[str] = None
    metric_name: str = ""
    investigation_scope: dict[str, Any] = Field(default_factory=dict)
    window_start: str = ""
    window_end: str = ""
    as_of_time: str = ""
    time_budget_seconds: int = 300
    cost_budget_usd: Decimal = Field(default_factory=lambda: Decimal("2.00"))
    tool_call_budget: int = 20
    workflow_version: str = "v1.0"

    def validate(self, workflow_id: Optional[str] = None) -> None:
        """
        Fail-closed input validation.
        Enforces INV-TEN-001..003, INV-DATA-001, and INV-COST-001.
        """
        if not self.tenant_id or not self.tenant_id.strip():
            raise TenancyViolationError(
                "tenant_id cannot be null or empty",
                details={"investigation_id": self.investigation_id},
            )

        if not self.investigation_id or not self.investigation_id.strip():
            raise ValueError("investigation_id cannot be null or empty")

        if not self.principal_id or not self.principal_id.strip():
            raise ValueError("principal_id cannot be null or empty")

        # Canonical workflow ID format: tenant/{tenant_id}/investigation/{investigation_id}
        if workflow_id:
            expected_prefix = f"tenant/{self.tenant_id}/investigation/{self.investigation_id}"
            if workflow_id != expected_prefix:
                raise TenancyViolationError(
                    f"Workflow ID '{workflow_id}' violates canonical tenant format '{expected_prefix}'",
                    details={
                        "workflow_id": workflow_id,
                        "expected_prefix": expected_prefix,
                        "tenant_id": self.tenant_id,
                    },
                )

        # Budget hard stop ceiling check (hard ceiling $5.00)
        cost = Decimal(str(self.cost_budget_usd))
        if cost > Decimal("5.00"):
            raise BudgetExceededError(
                f"cost_budget_usd ${cost} exceeds maximum hard limit of $5.00",
                details={"cost_budget_usd": str(cost), "hard_ceiling_usd": "5.00"},
            )
        if cost < Decimal("0.00"):
            raise BudgetExceededError("cost_budget_usd cannot be negative")

        # Temporal boundaries ordering: window_start < window_end <= as_of_time
        if self.window_start and self.window_end:
            ws = UtcDateTime.from_iso(self.window_start)
            we = UtcDateTime.from_iso(self.window_end)
            if ws.value >= we.value:
                raise TemporalValidationException(
                    f"window_start ({self.window_start}) must precede window_end ({self.window_end})",
                    details={"window_start": self.window_start, "window_end": self.window_end},
                )
            if self.as_of_time:
                asof = UtcDateTime.from_iso(self.as_of_time)
                if we.value > asof.value:
                    raise TemporalValidationException(
                        f"window_end ({self.window_end}) exceeds as_of_time ({self.as_of_time})",
                        details={"window_end": self.window_end, "as_of_time": self.as_of_time},
                    )


class InvestigationState(BaseModel):
    """
    Sanitized read-only projection returned by get_investigation_state query.
    Conforms to TEMPORAL-WORKFLOW-SPEC.md §6.2.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    investigation_id: str
    tenant_id: str
    status: InvestigationStatus = InvestigationStatus.INITIALIZING
    prior_active_state: Optional[InvestigationStatus] = None
    budget: BudgetState = Field(default_factory=BudgetState)
    current_step: str = "INITIALIZING"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    pause_reason: Optional[str] = None
    paused_by: Optional[str] = None
    cancel_reason: Optional[str] = None
    cancelled_by: Optional[str] = None
    manifest: Optional[InvestigationManifest] = None


class InvestigationProgress(BaseModel):
    """
    Progress metrics returned by get_progress query.
    Conforms to TEMPORAL-WORKFLOW-SPEC.md §6.2.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    total_tasks: int = 0
    completed_tasks: int = 0
    running_tasks: int = 0
    pending_tasks: int = 0
    status: str = "INITIALIZING"

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


__all__ = [
    "PauseInvestigationSignal",
    "ResumeInvestigationSignal",
    "CancelInvestigationSignal",
    "InvestigationWorkflowInput",
    "InvestigationState",
    "InvestigationProgress",
]
