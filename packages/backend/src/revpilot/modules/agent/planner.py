"""
RevPilot AI — Typed Investigation Agent Planner and Task DAG Contracts
Specification: docs/06-agent-platform/MULTI-AGENT-SPEC.md §2.1, §3, §4
Implements InvestigationPlanner producing bounded, typed DAGs (FR-INV-001, AC-P03-006-01).
"""

from __future__ import annotations
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure
from revpilot.modules.investigation.domain.models import InvestigationScope, BudgetState
from revpilot.modules.agent.dag_validator import validate_investigation_dag


class TaskType(str, Enum):
    """
    Canonical investigation activity task types.
    Conforms to MULTI-AGENT-SPEC.md §2.1.
    """
    SQL_DRILLDOWN = "SQL_DRILLDOWN"
    GOVERNED_RETRIEVAL = "GOVERNED_RETRIEVAL"
    TICKET_INTELLIGENCE = "TICKET_INTELLIGENCE"
    SYNTHESIZE_HYPOTHESES = "SYNTHESIZE_HYPOTHESES"
    VERIFY_EVIDENCE = "VERIFY_EVIDENCE"


class AgentTask(BaseModel):
    """
    Typed unit of execution within an investigation plan DAG.
    Conforms to MULTI-AGENT-SPEC.md §2.1.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    task_id: str
    task_type: TaskType
    capability_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    estimated_cost_usd: Decimal = Field(default=Decimal("0.05"))
    timeout_seconds: int = Field(default=30, le=60)
    retry_limit: int = Field(default=1, le=1)


class Plan(BaseModel):
    """
    Structured, acyclic investigation plan containing typed tasks.
    Conforms to MULTI-AGENT-SPEC.md §2.1 and §4.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    plan_id: UUIDv7
    investigation_id: UUIDv7
    tenant_id: TenantId
    anomaly_id: Optional[str] = None
    metric_name: str
    target_dimensions: list[str]
    tasks: list[AgentTask]
    max_concurrency: int = Field(default=4, le=8)
    estimated_total_cost_usd: Decimal
    created_at: UtcDateTime
    version: str = "v1.0"


class PlannerError(DomainError):
    """Encapsulates planning and DAG generation domain errors."""

    def __init__(
        self,
        code: str = "ERR_PLANNER_FAILURE",
        message: str = "Investigation planning failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)


class InvestigationPlanner:
    """
    Stateless cognitive planner that generates bounded, typed task DAGs
    for investigating revenue and metric anomalies.
    """

    def __init__(
        self,
        tenant_id: TenantId | None = None,
        investigation_id: UUIDv7 | None = None,
    ) -> None:
        self._tenant_id = tenant_id
        self._investigation_id = investigation_id

    async def generate_plan(
        self,
        scope: InvestigationScope,
        metric_name: str,
        budget: BudgetState,
        tenant_id: TenantId | None = None,
        investigation_id: UUIDv7 | None = None,
        anomaly_id: str | None = None,
    ) -> Result[Plan, PlannerError]:
        """
        Synthesize a validated DAG plan conforming to budget caps and complexity limits.
        """
        effective_tenant = tenant_id or self._tenant_id or TenantId("tnt_system")
        effective_investigation = investigation_id or self._investigation_id or UUIDv7.generate()

        remaining_budget = budget.allocated_usd - budget.spent_usd
        if remaining_budget <= Decimal("0.00") or budget.spent_usd >= budget.hard_stop_usd:
            return Failure(
                PlannerError(
                    code="ERR_BUDGET_EXCEEDED",
                    message="Insufficient budget remaining to generate or execute investigation plan",
                    details={
                        "allocated_usd": str(budget.allocated_usd),
                        "spent_usd": str(budget.spent_usd),
                        "hard_stop_usd": str(budget.hard_stop_usd),
                    },
                )
            )

        # Determine target dimensions
        target_dimensions: list[str] = []
        if scope.dimension_filters:
            target_dimensions.extend(list(scope.dimension_filters.keys()))
        if scope.tier and "tier" not in target_dimensions:
            target_dimensions.append("tier")
        if scope.region and "region" not in target_dimensions:
            target_dimensions.append("region")
        if not target_dimensions:
            target_dimensions = ["tier", "region"]

        primary_dim = target_dimensions[0]

        # Construct standard DAG nodes:
        # Layer 1: Parallel Evidence Gathering (SQL, Retrieval, Tickets)
        # Layer 2: Hypothesis Synthesis
        # Layer 3: Deterministic Evidence Verification
        task_sql = AgentTask(
            task_id="task_01_sql",
            task_type=TaskType.SQL_DRILLDOWN,
            capability_id="CAP-SQL-DRILLDOWN-DIM",
            parameters={
                "metric": metric_name,
                "dimension": primary_dim,
                "dimension_filters": scope.dimension_filters,
            },
            depends_on=[],
            estimated_cost_usd=Decimal("0.05"),
        )
        task_retrieval = AgentTask(
            task_id="task_02_retrieval",
            task_type=TaskType.GOVERNED_RETRIEVAL,
            capability_id="CAP-GOVERNED-RETRIEVAL",
            parameters={
                "query": f"Policy or contract anomalies affecting {metric_name}",
            },
            depends_on=[],
            estimated_cost_usd=Decimal("0.05"),
        )
        task_tickets = AgentTask(
            task_id="task_03_tickets",
            task_type=TaskType.TICKET_INTELLIGENCE,
            capability_id="CAP-TICKET-INTELLIGENCE",
            parameters={
                "metric": metric_name,
                "region": scope.region,
                "tier": scope.tier,
            },
            depends_on=[],
            estimated_cost_usd=Decimal("0.05"),
        )
        task_synth = AgentTask(
            task_id="task_04_synth",
            task_type=TaskType.SYNTHESIZE_HYPOTHESES,
            capability_id="CAP-SYNTHESIZE-ROOT-CAUSE",
            parameters={"metric_name": metric_name},
            depends_on=["task_01_sql", "task_02_retrieval", "task_03_tickets"],
            estimated_cost_usd=Decimal("0.05"),
        )
        task_verify = AgentTask(
            task_id="task_05_verify",
            task_type=TaskType.VERIFY_EVIDENCE,
            capability_id="CAP-VERIFY-HYPOTHESES",
            parameters={"metric_name": metric_name},
            depends_on=["task_04_synth"],
            estimated_cost_usd=Decimal("0.05"),
        )

        tasks = [task_sql, task_retrieval, task_tickets, task_synth, task_verify]
        estimated_total = sum((t.estimated_cost_usd for t in tasks), Decimal("0.00"))

        if estimated_total > remaining_budget:
            return Failure(
                PlannerError(
                    code="ERR_BUDGET_EXCEEDED",
                    message="Plan cost exceeds available budget allocation",
                    details={
                        "estimated_total_usd": str(estimated_total),
                        "remaining_budget_usd": str(remaining_budget),
                    },
                )
            )

        plan = Plan(
            plan_id=UUIDv7.generate(),
            investigation_id=effective_investigation,
            tenant_id=effective_tenant,
            anomaly_id=anomaly_id,
            metric_name=metric_name,
            target_dimensions=target_dimensions,
            tasks=tasks,
            max_concurrency=4,
            estimated_total_cost_usd=estimated_total,
            created_at=UtcDateTime.now(),
            version="v1.0",
        )

        val_result = validate_investigation_dag(plan)
        if val_result.is_failure:
            err = val_result.unwrap_error()
            return Failure(
                PlannerError(
                    code=err.code,
                    message=err.message,
                    details=err.details,
                )
            )

        return Success(plan)
