"""
RevPilot AI — PostgreSQL Approval Repository Adapter (Phase 06)
Implements persistence for ApprovalRequestRecord against PostgreSQL.
Enforces INV-ACT-003 (Zero Agent Self-Approval), INV-TEN-001, and INV-TEN-002.
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


class PostgresApprovalRepository:
    """
    PostgreSQL persistence adapter for Human Approval requests.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def create_request(self, context: TenantContext, data: dict[str, Any]) -> str:
        """Create new pending approval request."""
        approval_id = data["id"]
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.approval_requests (
                tenant_id, id, decision_id, action_type, target_entity_refs,
                payload_digest, policy_digest, estimated_cost_usd, required_approval_tier,
                status, expiry_time, correlation_id, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $13
            )
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                approval_id,
                data.get("decision_id"),
                data["action_type"],
                json.dumps(data.get("target_entity_refs", [])),
                data["payload_digest"],
                data["policy_digest"],
                Decimal(str(data.get("estimated_cost_usd", "0.00"))),
                data.get("required_approval_tier", "TIER_1"),
                data.get("status", "PENDING"),
                data["expiry_time"],
                data["correlation_id"],
                now,
            )
        return approval_id

    async def list_pending(self, context: TenantContext) -> list[dict[str, Any]]:
        """List active pending approvals awaiting signature within caller's tenant."""
        now = UtcDateTime.now().as_datetime()
        query = """
            SELECT
                id, tenant_id, decision_id, action_type, target_entity_refs,
                payload_digest, policy_digest, estimated_cost_usd, required_approval_tier,
                status, expiry_time, correlation_id, created_at
            FROM revpilot.approval_requests
            WHERE status = 'PENDING' AND expiry_time > $1
            ORDER BY created_at DESC;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            rows = await conn.fetch(query, now)
            results = []
            for r in rows:
                item = dict(r)
                item["estimated_cost_usd"] = float(item["estimated_cost_usd"])
                item["target_entity_refs"] = json.loads(item["target_entity_refs"]) if isinstance(item["target_entity_refs"], str) else item["target_entity_refs"]
                results.append(item)
            return results

    async def record_approval(
        self, context: TenantContext, approval_id: str, approver_principal_id: str
    ) -> dict[str, Any]:
        """Record human approval signature."""
        now = UtcDateTime.now().as_datetime()
        query = """
            UPDATE revpilot.approval_requests
            SET status = 'APPROVED', approver_principal_id = $1, updated_at = $2
            WHERE id = $3 AND status = 'PENDING' AND expiry_time > $2
            RETURNING id, status, approver_principal_id, updated_at;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            row = await conn.fetchrow(query, approver_principal_id, now, approval_id)
            if not row:
                raise NotFoundError(f"Pending approval '{approval_id}' not found, expired, or already resolved.")
            return dict(row)

    async def record_rejection(
        self, context: TenantContext, approval_id: str, approver_principal_id: str, reason: str
    ) -> dict[str, Any]:
        """Record human approval rejection."""
        now = UtcDateTime.now().as_datetime()
        query = """
            UPDATE revpilot.approval_requests
            SET status = 'REJECTED', approver_principal_id = $1, rejection_reason = $2, updated_at = $3
            WHERE id = $4 AND status = 'PENDING'
            RETURNING id, status, updated_at;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            row = await conn.fetchrow(query, approver_principal_id, reason, now, approval_id)
            if not row:
                raise NotFoundError(f"Pending approval '{approval_id}' not found or already resolved.")
            return dict(row)
