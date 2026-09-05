"""
RevPilot AI — PostgreSQL Connector Repository Adapter (Phase 07)
Implements persistence for SaaS Connector configurations and sync states.
Enforces INV-DATA-002, INV-SEC-001, and INV-TEN-001.
"""

from __future__ import annotations

import json
from typing import Any
import asyncpg

from revpilot.infrastructure.database import TenantDatabaseSession
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import NotFoundError
from revpilot.shared.temporal import UtcDateTime


class PostgresConnectorRepository:
    """
    PostgreSQL persistence adapter for Connector configurations.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def create_connector(self, context: TenantContext, data: dict[str, Any]) -> str:
        """Register SaaS connector configuration."""
        conn_id = data["id"]
        now = UtcDateTime.now().as_datetime()

        query = """
            INSERT INTO revpilot.connectors (
                tenant_id, id, provider, sync_mode, auth_method, secret_ref,
                status, schema_version, config, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10
            )
            RETURNING id;
        """

        async with TenantDatabaseSession(self.pool, context) as conn:
            await conn.execute(
                query,
                str(context.tenant_id),
                conn_id,
                data["provider"],
                data.get("sync_mode", "BATCH_PULL"),
                data.get("auth_method", "api_key_vault"),
                data["secret_ref"],
                data.get("status", "CONFIGURED"),
                data.get("schema_version", "1.0.0"),
                json.dumps(data.get("config", {})),
                now,
            )
        return conn_id

    async def list_connectors(self, context: TenantContext) -> list[dict[str, Any]]:
        """List active connectors for tenant."""
        query = """
            SELECT id, tenant_id, provider, sync_mode, auth_method, secret_ref,
                   status, schema_version, last_sync_at, consecutive_failures, created_at
            FROM revpilot.connectors
            ORDER BY created_at DESC;
        """
        async with TenantDatabaseSession(self.pool, context) as conn:
            rows = await conn.fetch(query)
            return [dict(r) for r in rows]
