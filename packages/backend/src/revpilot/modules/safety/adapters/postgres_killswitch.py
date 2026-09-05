"""
RevPilot AI — PostgreSQL Kill Switch Registry Adapter (Phase 06)
Implements global, tenant, and capability kill-switch persistence.
Enforces ADR-0012, INV-ACT-001, and sub-500ms safety propagation.
"""

from __future__ import annotations

from typing import Any
import asyncpg

from revpilot.shared.temporal import UtcDateTime


class PostgresKillSwitchRepository:
    """
    PostgreSQL persistence adapter for Platform Kill Switches (platform-scoped, no RLS).
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def activate_kill_switch(
        self, scope: str, reason: str, activated_by: str, target_id: str | None = None
    ) -> str:
        """Engage a kill switch."""
        now = UtcDateTime.now().as_datetime()
        ks_id = f"ks_{scope.lower()}_{UtcDateTime.now().as_datetime().strftime('%Y%m%d%H%M%S')}"

        query = """
            INSERT INTO revpilot.kill_switches (
                id, scope, target_id, is_active, reason, activated_by, activated_at
            ) VALUES (
                $1, $2, $3, TRUE, $4, $5, $6
            )
            RETURNING id;
        """

        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                ks_id,
                scope.upper(),
                target_id,
                reason,
                activated_by,
                now,
            )
        return ks_id

    async def is_kill_switch_active(
        self, scope: str, target_id: str | None = None
    ) -> bool:
        """Check if kill switch is active for given scope."""
        async with self.pool.acquire() as conn:
            if target_id:
                row = await conn.fetchrow(
                    "SELECT 1 FROM revpilot.kill_switches WHERE is_active = TRUE AND scope = $1 AND (target_id = $2 OR target_id IS NULL) LIMIT 1",
                    scope.upper(),
                    target_id,
                )
            else:
                row = await conn.fetchrow(
                    "SELECT 1 FROM revpilot.kill_switches WHERE is_active = TRUE AND scope = $1 LIMIT 1",
                    scope.upper(),
                )
            return row is not None
