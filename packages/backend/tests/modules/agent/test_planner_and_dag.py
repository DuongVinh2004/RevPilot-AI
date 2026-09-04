"""
RevPilot AI — Unit and Contract Tests for Agent Planner and DAG Validation
Specification: docs/06-agent-platform/MULTI-AGENT-SPEC.md §2.1, §4, §7
Enforces AC-P03-006-01: DAG validation rejects cyclical graphs, depth > 4,
fan-out > 8, or total tasks > 20 (FR-INV-001).
"""

from __future__ import annotations
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_agent_module():
    """Ensure agent and investigation modules are isolated and cleaned up between test cases."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.agent") or mod.startswith("revpilot.modules.investigation"):
            sys.modules.pop(mod, None)


@pytest.fixture
def agent_module():
    """Lazily load agent module to avoid top-level test collection contamination."""
    import revpilot.modules.agent as mod
    return mod


@pytest.fixture
def investigation_models():
    """Lazily load investigation models to avoid top-level test collection contamination."""
    from revpilot.modules.investigation.domain.models import InvestigationScope, BudgetState
    return InvestigationScope, BudgetState


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_alpha_corp")


@pytest.fixture
def sample_investigation_id() -> UUIDv7:
    return UUIDv7.generate()


def _make_task(agent_mod, task_id: str, depends_on: list[str] | None = None):
    """Helper to generate a minimal AgentTask."""
    return agent_mod.AgentTask(
        task_id=task_id,
        task_type=agent_mod.TaskType.SQL_DRILLDOWN,
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        parameters={"dimension": "tier"},
        depends_on=depends_on or [],
        estimated_cost_usd=Decimal("0.05"),
    )


def _make_plan(agent_mod, tasks, tenant_id: TenantId, investigation_id: UUIDv7):
    """Helper to assemble a Plan from tasks."""
    return agent_mod.Plan(
        plan_id=UUIDv7.generate(),
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        anomaly_id="anm_12345",
        metric_name="mrr_drop",
        target_dimensions=["tier", "region"],
        tasks=tasks,
        max_concurrency=4,
        estimated_total_cost_usd=Decimal("0.25"),
        created_at=UtcDateTime.now(),
        version="v1.0",
    )


# =============================================================================
# AC-P03-006-01: DAG Validation and Invariant Enforcement
# =============================================================================

def test_valid_dag_plan_passes_validation(agent_module, sample_tenant, sample_investigation_id):
    """A well-formed acyclic DAG within complexity bounds must pass validation."""
    tasks = [
        _make_task(agent_module, "t1", depends_on=[]),
        _make_task(agent_module, "t2", depends_on=[]),
        _make_task(agent_module, "t3", depends_on=["t1", "t2"]),
        _make_task(agent_module, "t4", depends_on=["t3"]),
    ]
    plan = _make_plan(agent_module, tasks, sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_success
    assert res.unwrap() is True


def test_dag_validation_rejects_cycle(agent_module, sample_tenant, sample_investigation_id):
    """AC-P03-006-01: Direct or indirect dependency cycles must be rejected with ERR_DAG_CYCLE_DETECTED."""
    # Cycle: t1 -> t2 -> t3 -> t1
    tasks = [
        _make_task(agent_module, "t1", depends_on=["t3"]),
        _make_task(agent_module, "t2", depends_on=["t1"]),
        _make_task(agent_module, "t3", depends_on=["t2"]),
    ]
    plan = _make_plan(agent_module, tasks, sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_DAG_CYCLE_DETECTED"
    assert "Cyclical task dependency detected" in err.message


def test_dag_validation_rejects_self_loop(agent_module, sample_tenant, sample_investigation_id):
    """AC-P03-006-01: Self-referencing task must be rejected as cyclical."""
    tasks = [
        _make_task(agent_module, "t1", depends_on=["t1"]),
    ]
    plan = _make_plan(agent_module, tasks, sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_DAG_CYCLE_DETECTED"


def test_dag_validation_rejects_depth_exceeding_four(agent_module, sample_tenant, sample_investigation_id):
    """AC-P03-006-01: Graph depth > 4 must be rejected with ERR_DAG_LIMIT_EXCEEDED."""
    # Chain of 5 tasks: depth = 5
    tasks = [
        _make_task(agent_module, "t1", depends_on=[]),
        _make_task(agent_module, "t2", depends_on=["t1"]),
        _make_task(agent_module, "t3", depends_on=["t2"]),
        _make_task(agent_module, "t4", depends_on=["t3"]),
        _make_task(agent_module, "t5", depends_on=["t4"]),
    ]
    plan = _make_plan(agent_module, tasks, sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_DAG_LIMIT_EXCEEDED"
    assert "exceeds maximum depth limit of 4" in err.message


def test_dag_validation_rejects_fan_out_exceeding_eight(agent_module, sample_tenant, sample_investigation_id):
    """AC-P03-006-01: A single node with out-degree > 8 must be rejected with ERR_DAG_LIMIT_EXCEEDED."""
    root = _make_task(agent_module, "root", depends_on=[])
    # 9 dependents of root -> fan_out = 9
    dependents = [_make_task(agent_module, f"child_{i}", depends_on=["root"]) for i in range(1, 10)]
    tasks = [root] + dependents
    plan = _make_plan(agent_module, tasks, sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_DAG_LIMIT_EXCEEDED"
    assert "exceeds maximum limit of 8" in err.message or "fan-out" in err.message


def test_dag_validation_rejects_root_fan_out_exceeding_eight(agent_module, sample_tenant, sample_investigation_id):
    """AC-P03-006-01: More than 8 initial independent root tasks must be rejected."""
    roots = [_make_task(agent_module, f"root_{i}", depends_on=[]) for i in range(1, 10)]
    plan = _make_plan(agent_module, roots, sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_DAG_LIMIT_EXCEEDED"
    assert "exceeds maximum limit of 8" in err.message


def test_dag_validation_rejects_total_tasks_exceeding_twenty(agent_module, sample_tenant, sample_investigation_id):
    """AC-P03-006-01: Investigation plan exceeding 20 total tasks must be rejected."""
    # 21 tasks: 3 parallel tiers
    tasks = []
    # 7 roots
    for i in range(7):
        tasks.append(_make_task(agent_module, f"r_{i}", depends_on=[]))
    # 7 tier-2 tasks
    for i in range(7):
        tasks.append(_make_task(agent_module, f"m_{i}", depends_on=[f"r_{i}"]))
    # 7 tier-3 tasks (total 21)
    for i in range(7):
        tasks.append(_make_task(agent_module, f"e_{i}", depends_on=[f"m_{i}"]))

    plan = _make_plan(agent_module, tasks, sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_DAG_LIMIT_EXCEEDED"
    assert "exceeds maximum limit of 20" in err.message


def test_dag_validation_rejects_unknown_dependency(agent_module, sample_tenant, sample_investigation_id):
    """Plan referencing non-existent prerequisite task must be rejected with ERR_INVALID_PLAN_DAG."""
    tasks = [
        _make_task(agent_module, "t1", depends_on=["phantom_task"]),
    ]
    plan = _make_plan(agent_module, tasks, sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_INVALID_PLAN_DAG"
    assert "unknown prerequisite task" in err.message


def test_dag_validation_rejects_duplicate_task_id(agent_module, sample_tenant, sample_investigation_id):
    """Duplicate task_id must be rejected with ERR_INVALID_PLAN_DAG."""
    tasks = [
        _make_task(agent_module, "t1", depends_on=[]),
        _make_task(agent_module, "t1", depends_on=[]),
    ]
    plan = _make_plan(agent_module, tasks, sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_INVALID_PLAN_DAG"
    assert "Duplicate task_id" in err.message


def test_dag_validation_rejects_empty_tasks(agent_module, sample_tenant, sample_investigation_id):
    """Empty plan must be rejected with ERR_INVALID_PLAN_DAG."""
    plan = _make_plan(agent_module, [], sample_tenant, sample_investigation_id)

    res = agent_module.validate_investigation_dag(plan)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_INVALID_PLAN_DAG"


# =============================================================================
# InvestigationPlanner Unit Tests
# =============================================================================

@pytest.mark.asyncio
async def test_investigation_planner_generates_valid_dag(agent_module, investigation_models, sample_tenant, sample_investigation_id):
    """InvestigationPlanner generates a structured plan passing all DAG validation bounds."""
    InvestigationScope, BudgetState = investigation_models
    planner = agent_module.InvestigationPlanner(
        tenant_id=sample_tenant,
        investigation_id=sample_investigation_id,
    )
    scope = InvestigationScope(
        region="us-east",
        tier="enterprise",
        dimension_filters={"tier": "enterprise"},
    )
    budget = BudgetState(
        allocated_usd=Decimal("2.00"),
        spent_usd=Decimal("0.00"),
        hard_stop_usd=Decimal("5.00"),
    )

    res = await planner.generate_plan(scope=scope, metric_name="churn_rate", budget=budget)
    assert res.is_success
    plan = res.unwrap()
    assert plan.investigation_id == sample_investigation_id
    assert plan.tenant_id == sample_tenant
    assert len(plan.tasks) == 5
    assert plan.estimated_total_cost_usd <= budget.allocated_usd

    # Ensure generated plan passes strict DAG validation
    val_res = agent_module.validate_investigation_dag(plan)
    assert val_res.is_success


@pytest.mark.asyncio
async def test_investigation_planner_rejects_exhausted_budget(agent_module, investigation_models, sample_tenant, sample_investigation_id):
    """Planner halts if budget is exhausted or hard stop is reached (INV-COST-001)."""
    InvestigationScope, BudgetState = investigation_models
    planner = agent_module.InvestigationPlanner(
        tenant_id=sample_tenant,
        investigation_id=sample_investigation_id,
    )
    scope = InvestigationScope(region="us-east")
    exhausted_budget = BudgetState(
        allocated_usd=Decimal("2.00"),
        spent_usd=Decimal("2.00"),
        hard_stop_usd=Decimal("5.00"),
    )

    res = await planner.generate_plan(scope=scope, metric_name="churn_rate", budget=exhausted_budget)
    assert res.is_failure
    err = res.unwrap_error()
    assert err.code == "ERR_BUDGET_EXCEEDED"
