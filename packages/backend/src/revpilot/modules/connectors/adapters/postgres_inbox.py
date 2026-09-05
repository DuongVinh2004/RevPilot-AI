"""
RevPilot AI — PostgreSQL Inbound Webhook Inbox Adapter (Phase 07)
Implements transactional anti-replay webhook staging and quarantine.
Enforces INV-DATA-002, INV-REL-001, and anti-replay contracts.
"""

from __future__ import annotations

import json
from typing import Any
import asyncpg

from revpilot.infrastructure.database import TenantDatabaseSession
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import ConcurrencyError
from revpilot.shared.temporal import UtcDateTime


class PostgresConnectorInbox:
    """
    Transactional inbox for incoming SaaS webhooks with anti-replay guarantees.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def ingest_webhook_event(
        self,
        context: TenantContext,
        connector_id: str,
        external_event_id: str,
        payload: dict[str, Any],
        payload_digest: str,
    ) -> tuple[str, bool]:
        """
        Store webhook event in transactional inbox.
        Returns (inbox_event_id, is_duplicate).
        """
        now = UtcDateTime.now().as_datetime()
        inbox_id = f"inbox_{UtcDateTime.now().as_datetime().strftime('%Y%m%d%H%M%S')}_{external_event_id[:16]}"

        query = """
            INSERT INTO revpilot.connector_inbox (
                tenant_id, id, connector_id, external_event_id,
                payload, payload_digest, received_at, status
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, 'RECEIVED'
            )
            ON CONFLICT (tenant_id, connector_id, external_event_id) DO NOTHING
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            row = await conn.fetchrow(
                query,
                str(context.tenant_id),
                inbox_id,
                connector_id,
                external_event_id,
                json.dumps(payload),
                payload_digest,
                now,
            )
            if row:
                return row["id"], False
            return "duplicate_event_acknowledged", True
