"""
RevPilot AI — PostgreSQL Atomic Budget Ledger with OCC (Phase 05)
Implements daily monetary budget reservation and atomic ledger commits.
Enforces INV-COST-001, INV-TEN-001, and Concurrency Controls.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from datetime import date
import asyncpg

from revpilot.infrastructure.database import TenantDatabaseSession
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import ConcurrencyError, DomainError
from revpilot.shared.temporal import UtcDateTime


class PostgresBudgetLedger:
    """
    Atomic budget ledger using PostgreSQL Row-Level Locking and Optimistic Concurrency Control.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def reserve_budget(
        self, context: TenantContext, ledger_date: date, amount_usd: Decimal
    ) -> bool:
        """
        Atomically check headroom and reserve budget.
        Raises ConcurrencyError on OCC conflict or DomainError if budget exceeded.
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            # 1. Select for update or insert daily ledger row
            row = await conn.fetchrow(
                """
                SELECT id, daily_budget_usd, spent_usd, reserved_usd, version
                FROM revpilot.budget_ledger
                WHERE ledger_date = $1
                FOR UPDATE;
                """,
                ledger_date,
            )

            if not row:
                # Initialize daily budget of $5000.00 default
                await conn.execute(
                    """
                    INSERT INTO revpilot.budget_ledger (
                        tenant_id, id, ledger_date, daily_budget_usd, spent_usd, reserved_usd, version
                    ) VALUES (
                        $1, 'bl_' || $1 || '_' || $2::text, $2, 5000.00, 0.00, $3, 1
                    ) ON CONFLICT (tenant_id, ledger_date) DO NOTHING;
                    """,
                    str(context.tenant_id),
                    ledger_date,
                    amount_usd,
                )
                return True

            daily_budget = row["daily_budget_usd"]
            spent = row["spent_usd"]
            reserved = row["reserved_usd"]
            current_version = row["version"]

            available = daily_budget - (spent + reserved)
            if available < amount_usd:
                raise DomainError(
                    code="ERR_BUDGET_EXCEEDED",
                    message=f"Requested {amount_usd} USD exceeds available budget headroom {available} USD",
                    details={"available": float(available), "requested": float(amount_usd)},
                    retryable=False,
                )

            # Atomic update with version check
            res = await conn.execute(
                """
                UPDATE revpilot.budget_ledger
                SET reserved_usd = reserved_usd + $1,
                    version = version + 1,
                    updated_at = $2
                WHERE id = $3 AND version = $4;
                """,
                amount_usd,
                UtcDateTime.now().as_datetime(),
                row["id"],
                current_version,
            )

            if res == "UPDATE 0":
                raise ConcurrencyError("Budget ledger updated concurrently. Retry transaction.")

            return True
