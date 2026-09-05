"""
RevPilot AI — PostgreSQL Investigation Repository Adapter (Phase 03)
Implements persistence for Investigation aggregates and plans against PostgreSQL.
Enforces INV-WF-001, INV-TEN-001, and INV-TEN-002.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
import asyncpg

from revpilot.infrastructure.database import TenantDatabaseSession
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import NotFoundError, ValidationError
from revpilot.shared.temporal import UtcDateTime


class PostgresInvestigationRepository:
    """
    PostgreSQL persistence adapter for Investigation and InvestigationPlan records.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def create_investigation(
        self, context: TenantContext, investigation_data: dict[str, Any]
    ) -> str:
        """Create new investigation record."""
        inv_id = investigation_data["id"]
        scope = investigation_data.get("investigation_scope", {})
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.investigations (
                tenant_id, id, anomaly_id, metric_name, status, workflow_id,
                investigation_scope, cost_budget_usd, time_budget_seconds,
                tool_call_budget, spent_usd, spent_tokens, spent_tool_calls,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $14
            )
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                inv_id,
                investigation_data["anomaly_id"],
                investigation_data["metric_name"],
                investigation_data.get("status", "INITIALIZING"),
                investigation_data["workflow_id"],
                json.dumps(scope),
                Decimal(str(investigation_data.get("cost_budget_usd", "2.00"))),
                int(investigation_data.get("time_budget_seconds", 300)),
                int(investigation_data.get("tool_call_budget", 20)),
                Decimal("0.00"),
                0,
                0,
                now,
            )
        return inv_id

    async def get_by_id(self, context: TenantContext, investigation_id: str) -> dict[str, Any] | None:
        """Retrieve investigation by ID within tenant boundary."""
        query = """
            SELECT
                id, tenant_id, anomaly_id, metric_name, status, workflow_id,
                investigation_scope, cost_budget_usd, time_budget_seconds,
                tool_call_budget, spent_usd, spent_tokens, spent_tool_calls,
                created_at, updated_at, completed_at
            FROM revpilot.investigations
            WHERE id = $1;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            row = await conn.fetchrow(query, investigation_id)
            if not row:
                return None
            res = dict(row)
            res["cost_budget_usd"] = float(res["cost_budget_usd"])
            res["spent_usd"] = float(res["spent_usd"])
            res["investigation_scope"] = json.loads(res["investigation_scope"]) if isinstance(res["investigation_scope"], str) else res["investigation_scope"]
            return res

    async def list_investigations(
        self, context: TenantContext, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List investigations with optional status filter."""
        clauses = ["1=1"]
        params: list[Any] = []
        if status:
            params.append(status.upper())
            clauses.append(f"status = ${len(params)}")

        params.append(limit)
        limit_idx = len(params)
        params.append(offset)
        offset_idx = len(params)

        where_sql = " AND ".join(clauses)
        query = f"""
            SELECT id, tenant_id, anomaly_id, metric_name, status, workflow_id,
                   cost_budget_usd, spent_usd, created_at, completed_at
            FROM revpilot.investigations
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ${limit_idx} OFFSET ${offset_idx};
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            rows = await conn.fetch(query, *params)
            results = []
            for r in rows:
                item = dict(r)
                item["cost_budget_usd"] = float(item["cost_budget_usd"])
                item["spent_usd"] = float(item["spent_usd"])
                results.append(item)
            return results

    async def update_status(
        self, context: TenantContext, investigation_id: str, new_status: str
    ) -> dict[str, Any]:
        """Update status of an active investigation."""
        now = UtcDateTime.now().as_datetime()
        completed = now if new_status in ("COMPLETED", "FAILED", "CANCELLED") else None

        query = """
            UPDATE revpilot.investigations
            SET status = $1, updated_at = $2, completed_at = COALESCE($3, completed_at)
            WHERE id = $4
            RETURNING id, status, updated_at;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            row = await conn.fetchrow(query, new_status.upper(), now, completed, investigation_id)
            if not row:
                raise NotFoundError(f"Investigation '{investigation_id}' not found.")
            return dict(row)
