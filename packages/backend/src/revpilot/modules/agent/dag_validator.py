"""
RevPilot AI — Agent Investigation Plan DAG Validator
Specification: docs/06-agent-platform/MULTI-AGENT-SPEC.md §4, §7
Enforces acyclicity (Kahn's topological sort), max depth <= 4, max fan-out <= 8,
and max total tasks <= 20 (FR-INV-001, AC-P03-006-01).
"""

from __future__ import annotations
from collections import deque
from typing import Any, TYPE_CHECKING

from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure

if TYPE_CHECKING:
    from revpilot.modules.agent.planner import Plan


class DagValidationError(DomainError):
    """
    Encapsulates investigation plan DAG validation failures.
    Conforms to MULTI-AGENT-SPEC.md §4 error contract.
    """

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)


def validate_investigation_dag(plan: Plan) -> Result[bool, DagValidationError]:
    """
    Deterministically validate that an investigation plan forms a well-formed DAG
    strictly meeting all complexity and acyclicity invariants:
    1. Total task count <= 20
    2. Dependency referential integrity (all prerequisite tasks exist and are unique)
    3. Maximum fan-out <= 8 (both direct outgoing dependents and root concurrency)
    4. Strict acyclicity via Kahn's topological sort algorithm
    5. Maximum DAG depth <= 4
    6. Max concurrency bounds <= 8
    """
    tasks = plan.tasks

    # 1. Total task count checks
    if not tasks:
        return Failure(
            DagValidationError(
                code="ERR_INVALID_PLAN_DAG",
                message="Plan must contain at least one task",
                details={"investigation_id": str(plan.investigation_id)},
            )
        )

    if len(tasks) > 20:
        return Failure(
            DagValidationError(
                code="ERR_DAG_LIMIT_EXCEEDED",
                message=f"Plan total task count ({len(tasks)}) exceeds maximum limit of 20",
                details={"task_count": len(tasks), "limit": 20},
            )
        )

    if getattr(plan, "max_concurrency", 4) > 8:
        return Failure(
            DagValidationError(
                code="ERR_DAG_LIMIT_EXCEEDED",
                message=f"Plan max_concurrency ({plan.max_concurrency}) exceeds limit of 8",
                details={"max_concurrency": plan.max_concurrency, "limit": 8},
            )
        )

    # 2. Duplicate task IDs and dependency existence
    task_map: dict[str, Any] = {}
    for task in tasks:
        if task.task_id in task_map:
            return Failure(
                DagValidationError(
                    code="ERR_INVALID_PLAN_DAG",
                    message=f"Duplicate task_id detected: {task.task_id}",
                    details={"duplicate_task_id": task.task_id},
                )
            )
        task_map[task.task_id] = task

    for task in tasks:
        for dep in task.depends_on:
            if dep == task.task_id:
                return Failure(
                    DagValidationError(
                        code="ERR_DAG_CYCLE_DETECTED",
                        message=f"Self-referencing cycle detected in task {task.task_id}",
                        details={"task_id": task.task_id},
                    )
                )
            if dep not in task_map:
                return Failure(
                    DagValidationError(
                        code="ERR_INVALID_PLAN_DAG",
                        message=f"Task {task.task_id} depends on unknown prerequisite task: {dep}",
                        details={"task_id": task.task_id, "missing_dependency": dep},
                    )
                )

    # 3. Adjacency list and in-degrees
    adj: dict[str, list[str]] = {t_id: [] for t_id in task_map}
    in_degree: dict[str, int] = {t_id: 0 for t_id in task_map}

    for task in tasks:
        for dep in task.depends_on:
            adj[dep].append(task.task_id)
            in_degree[task.task_id] += 1

    # 4. Fan-out limits
    for t_id, dependents in adj.items():
        if len(dependents) > 8:
            return Failure(
                DagValidationError(
                    code="ERR_DAG_LIMIT_EXCEEDED",
                    message=f"Task {t_id} fan-out ({len(dependents)}) exceeds maximum limit of 8",
                    details={"task_id": t_id, "fan_out": len(dependents), "limit": 8},
                )
            )

    roots = [t_id for t_id, deg in in_degree.items() if deg == 0]
    if len(roots) > 8:
        return Failure(
            DagValidationError(
                code="ERR_DAG_LIMIT_EXCEEDED",
                message=f"Root concurrency fan-out ({len(roots)}) exceeds maximum limit of 8",
                details={"root_count": len(roots), "limit": 8},
            )
        )

    # 5. Kahn's Topological Sort & Longest Path (Depth) Calculation
    depth: dict[str, int] = {t_id: 1 for t_id in roots}
    queue: deque[str] = deque(roots)
    visited_count = 0

    while queue:
        curr = queue.popleft()
        visited_count += 1
        curr_depth = depth[curr]

        if curr_depth > 4:
            return Failure(
                DagValidationError(
                    code="ERR_DAG_LIMIT_EXCEEDED",
                    message=f"Plan depth ({curr_depth}) exceeds maximum depth limit of 4",
                    details={"task_id": curr, "depth": curr_depth, "limit": 4},
                )
            )

        for nxt in adj[curr]:
            depth[nxt] = max(depth.get(nxt, 1), curr_depth + 1)
            if depth[nxt] > 4:
                return Failure(
                    DagValidationError(
                        code="ERR_DAG_LIMIT_EXCEEDED",
                        message=f"Plan depth ({depth[nxt]}) exceeds maximum depth limit of 4",
                        details={"task_id": nxt, "depth": depth[nxt], "limit": 4},
                    )
                )

            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    # 6. Cycle detection
    if visited_count < len(tasks):
        return Failure(
            DagValidationError(
                code="ERR_DAG_CYCLE_DETECTED",
                message="Cyclical task dependency detected in investigation plan DAG",
                details={
                    "total_tasks": len(tasks),
                    "acyclic_visited_tasks": visited_count,
                },
            )
        )

    max_depth = max(depth.values()) if depth else 0
    if max_depth > 4:
        return Failure(
            DagValidationError(
                code="ERR_DAG_LIMIT_EXCEEDED",
                message=f"Plan maximum depth ({max_depth}) exceeds limit of 4",
                details={"max_depth": max_depth, "limit": 4},
            )
        )

    return Success(True)
