"""
RevPilot AI — PostgreSQL Append-Only Audit Log Adapter
Implements tamper-evident audit event recording with cryptographic hash chain.
Enforces INV-AUD-001 (Zero Audit Drop, Immutability) and INV-TEN-001.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
import asyncpg

from revpilot.infrastructure.database import TenantDatabaseSession
from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.errors import DomainError
from revpilot.shared.temporal import UtcDateTime


class PostgresAuditLog:
    """
    Append-only audit log adapter enforcing cryptographic hash chain integrity.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def append_event(
        self,
        tenant_id: str,
        actor_id: str,
        event_type: str,
        resource: str,
        action: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
        actor_type: str = "USER",
        outcome: str = "SUCCESS",
        causation_id: str | None = None,
        delegation_id: str | None = None,
    ) -> str:
        """Append an immutable audit event to the tamper-evident hash chain."""
        now = UtcDateTime.now().as_datetime()
        event_id = f"aud_{UtcDateTime.now().as_datetime().strftime('%Y%m%d%H%M%S')}_{hashlib.sha256(str(correlation_id).encode()).hexdigest()[:12]}"

        async with self.pool.acquire() as conn:
            # 1. Fetch previous event hash for tenant
            prev_row = await conn.fetchrow(
                "SELECT event_hash FROM revpilot.audit_events WHERE tenant_id = $1 ORDER BY occurred_at DESC, id DESC LIMIT 1",
                tenant_id,
            )
            prev_hash = prev_row["event_hash"] if prev_row else "genesis_block_00000000000000000000000000000000"

            # 2. Compute current event SHA-256 hash
            details_json = json.dumps(details or {}, sort_keys=True)
            hash_material = f"{event_id}:{tenant_id}:{actor_id}:{event_type}:{resource}:{action}:{outcome}:{correlation_id}:{prev_hash}:{details_json}"
            event_hash = hashlib.sha256(hash_material.encode()).hexdigest()

            # 3. Append-only INSERT
            query = """
                INSERT INTO revpilot.audit_events (
                    id, tenant_id, occurred_at, event_type, actor_id, actor_type,
                    delegation_id, resource, action, outcome, correlation_id,
                    causation_id, details, previous_event_hash, event_hash
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                )
                RETURNING id;
            """
            await conn.execute(
                query,
                event_id,
                tenant_id,
                now,
                event_type,
                actor_id,
                actor_type,
                delegation_id,
                resource,
                action,
                outcome,
                correlation_id,
                causation_id,
                details_json,
                prev_hash,
                event_hash,
            )
            return event_id
