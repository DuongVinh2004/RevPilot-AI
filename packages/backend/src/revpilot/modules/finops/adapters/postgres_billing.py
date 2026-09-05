"""
RevPilot AI — PostgreSQL Billing and Usage Repository Adapter
Implements persistence for UsageRecords, Invoices, and Credit Ledgers.
Enforces INV-COST-001 and INV-TEN-001.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
import asyncpg

from revpilot.infrastructure.database import TenantDatabaseSession
from revpilot.shared.context import TenantContext
from revpilot.shared.temporal import UtcDateTime


class PostgresBillingRepository:
    """
    PostgreSQL persistence adapter for Billing and FinOps records.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def record_usage(
        self, context: TenantContext, resource_type: str, quantity: int, unit: str = "TOKENS"
    ) -> str:
        """Record resource usage consumption."""
        now = UtcDateTime.now().as_datetime()
        record_id = f"usg_{UtcDateTime.now().as_datetime().strftime('%Y%m%d%H%M%S')}_{str(context.tenant_id)[:8]}"

        query = """
            INSERT INTO revpilot.usage_records (
                tenant_id, id, resource_type, quantity, unit, recorded_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6
            )
            RETURNING id;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                record_id,
                resource_type,
                quantity,
                unit,
                now,
            )
        return record_id
