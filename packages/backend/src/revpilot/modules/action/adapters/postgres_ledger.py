"""
RevPilot AI — PostgreSQL Action Ledger Adapter (Phase 06)
Implements idempotent ActionIntent and execution ActionLedger persistence.
Enforces INV-ACT-001, INV-ACT-002, and INV-TEN-001.
"""

from __future__ import annotations

import json
from typing import Any
import asyncpg

from revpilot.infrastructure.database import TenantDatabaseSession
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import NotFoundError, ConcurrencyError
from revpilot.shared.temporal import UtcDateTime


class PostgresActionLedger:
    """
    PostgreSQL persistence adapter for ActionIntent and ActionLedger.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def create_intent(self, context: TenantContext, intent_data: dict[str, Any]) -> str:
        """Register action intent idempotently."""
        intent_id = intent_data["id"]
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.action_intents (
                tenant_id, id, approval_id, idempotency_key, action_type,
                classification, is_dry_run, max_retries, timeout_seconds,
                payload, payload_digest, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            )
            ON CONFLICT (tenant_id, idempotency_key) DO UPDATE SET
                created_at = revpilot.action_intents.created_at
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            row = await conn.fetchrow(
                query,
                str(context.tenant_id),
                intent_id,
                intent_data["approval_id"],
                intent_data["idempotency_key"],
                intent_data["action_type"],
                intent_data.get("classification", "REVERSIBLE"),
                bool(intent_data.get("is_dry_run", False)),
                int(intent_data.get("max_retries", 3)),
                int(intent_data.get("timeout_seconds", 30)),
                json.dumps(intent_data.get("payload", {})),
                intent_data["payload_digest"],
                now,
            )
            return row["id"]

    async def record_attempt(
        self, context: TenantContext, ledger_entry: dict[str, Any]
    ) -> str:
        """Record an execution dispatch attempt in action ledger."""
        ledger_id = ledger_entry["id"]
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.action_ledger (
                tenant_id, id, intent_id, attempt_number, provider_name,
                provider_tx_id, execution_status, http_status_code,
                request_digest, response_digest, started_at, completed_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            )
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                ledger_id,
                ledger_entry["intent_id"],
                int(ledger_entry.get("attempt_number", 1)),
                ledger_entry["provider_name"],
                ledger_entry.get("provider_tx_id"),
                ledger_entry.get("execution_status", "SUCCESS"),
                ledger_entry.get("http_status_code", 200),
                ledger_entry["request_digest"],
                ledger_entry.get("response_digest"),
                ledger_entry.get("started_at", now),
                ledger_entry.get("completed_at", now),
            )
        return ledger_id
