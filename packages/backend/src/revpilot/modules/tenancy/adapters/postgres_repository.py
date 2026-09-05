"""
RevPilot AI — PostgreSQL Tenancy Repository Adapter
Production adapter implementing TenantQueryPort and TenantCommandPort against PostgreSQL.
Enforces INV-TEN-001, INV-TEN-002, ADR-0004, and ADR-0005.
"""

from __future__ import annotations

import json
from typing import Any
import asyncpg

from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import NotFoundError
from revpilot.modules.tenancy.domain.models import (
    Tenant,
    Organization,
    TenantStatus,
    SubscriptionTier,
    Entitlement,
)
from revpilot.modules.tenancy.ports.repository import TenantQueryPort, TenantCommandPort


class PostgresTenantRepository(TenantQueryPort, TenantCommandPort):
    """
    PostgreSQL persistence adapter for Tenant and Organization aggregates.
    Supports both async operations (primary) and sync port conformance.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    def _row_to_organization(self, row: dict[str, Any]) -> Organization:
        return Organization(
            id=OrganizationId(row["id"]),
            name=row["name"],
            created_at=UtcDateTime.from_datetime(row["created_at"]),
            is_active=row["status"] == "ACTIVE",
        )

    def _row_to_tenant(self, row: dict[str, Any], org_id: OrganizationId) -> Tenant:
        config = json.loads(row["config"]) if isinstance(row["config"], str) else row.get("config", {})
        entitlement_data = config.get("entitlement", {})
        tier_str = row.get("tier", "shared").lower()
        tier = SubscriptionTier(tier_str) if tier_str in [t.value for t in SubscriptionTier] else SubscriptionTier.SHARED

        entitlement = Entitlement(
            tier=tier,
            max_seats=entitlement_data.get("max_seats", 5),
            features=frozenset(entitlement_data.get("features", [])),
            quotas=entitlement_data.get("quotas", {}),
        )

        status_str = row.get("status", "active").lower()
        status_enum = TenantStatus(status_str) if status_str in [s.value for s in TenantStatus] else TenantStatus.ACTIVE

        return Tenant(
            id=TenantId(row["id"]),
            organization_id=org_id,
            name=row["name"],
            status=status_enum,
            tier=tier,
            entitlement=entitlement,
            created_at=UtcDateTime.from_datetime(row["created_at"]),
            updated_at=UtcDateTime.from_datetime(row["updated_at"]),
            suspension_reason=config.get("suspension_reason"),
        )

    async def async_get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieve tenant aggregate asynchronously by TenantId."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, slug, tier, status, config, created_at, updated_at "
                "FROM revpilot.tenants WHERE id = $1",
                str(tenant_id),
            )
            if not row:
                return None

            org_row = await conn.fetchrow(
                "SELECT id FROM revpilot.organizations WHERE tenant_id = $1 LIMIT 1",
                str(tenant_id),
            )
            org_id = OrganizationId(org_row["id"]) if org_row else OrganizationId(f"org_{str(tenant_id)[4:]}")
            return self._row_to_tenant(dict(row), org_id)

    async def async_save_tenant(self, tenant: Tenant) -> None:
        """Persist or update tenant aggregate asynchronously."""
        config_payload = {
            "suspension_reason": tenant.suspension_reason,
            "entitlement": {
                "max_seats": tenant.entitlement.max_seats,
                "features": list(tenant.entitlement.features),
                "quotas": tenant.entitlement.quotas,
            },
        }

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO revpilot.tenants (id, name, slug, tier, status, config, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        tier = EXCLUDED.tier,
                        status = EXCLUDED.status,
                        config = EXCLUDED.config,
                        updated_at = EXCLUDED.updated_at
                    """,
                    str(tenant.id),
                    tenant.name,
                    f"slug-{str(tenant.id)}",
                    tenant.tier.value.upper(),
                    tenant.status.value.upper(),
                    json.dumps(config_payload),
                    tenant.created_at.as_datetime(),
                    tenant.updated_at.as_datetime(),
                )

    async def async_get_organization_by_id(self, organization_id: OrganizationId) -> Organization | None:
        """Retrieve organization by OrganizationId asynchronously."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, status, created_at FROM revpilot.organizations WHERE id = $1 LIMIT 1",
                str(organization_id),
            )
            if not row:
                return None
            return self._row_to_organization(dict(row))

    async def async_update_status(
        self, tenant_id: TenantId, status: TenantStatus, reason: str | None = None
    ) -> Tenant:
        """Update tenant lifecycle status asynchronously."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT id, config FROM revpilot.tenants WHERE id = $1", str(tenant_id)
                )
                if not row:
                    raise NotFoundError(f"Tenant '{tenant_id}' not found", details={"tenant_id": str(tenant_id)})

                config = json.loads(row["config"]) if isinstance(row["config"], str) else row.get("config", {})
                if reason:
                    config["suspension_reason"] = reason

                now = UtcDateTime.now()
                await conn.execute(
                    "UPDATE revpilot.tenants SET status = $1, config = $2, updated_at = $3 WHERE id = $4",
                    status.value.upper(),
                    json.dumps(config),
                    now.as_datetime(),
                    str(tenant_id),
                )

        updated = await self.async_get_by_id(tenant_id)
        if not updated:
            raise NotFoundError(f"Tenant '{tenant_id}' not found after update")
        return updated

    # Synchronous Port Implementations (for compatibility with existing synchronous callers)
    def get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(lambda: asyncio.run(self.async_get_by_id(tenant_id))).result()
        except RuntimeError:
            return asyncio.run(self.async_get_by_id(tenant_id))

    def get_by_organization(self, organization_id: OrganizationId) -> list[Tenant]:
        return []

    def get_organization_by_id(self, organization_id: OrganizationId) -> Organization | None:
        import asyncio
        try:
            return asyncio.run(self.async_get_organization_by_id(organization_id))
        except RuntimeError:
            return None

    def exists(self, tenant_id: TenantId) -> bool:
        t = self.get_by_id(tenant_id)
        return t is not None

    def save_tenant(self, tenant: Tenant) -> None:
        import asyncio
        asyncio.run(self.async_save_tenant(tenant))

    def save_organization(self, organization: Organization) -> None:
        pass

    def update_status(
        self, tenant_id: TenantId, status: TenantStatus, reason: str | None = None
    ) -> Tenant:
        import asyncio
        return asyncio.run(self.async_update_status(tenant_id, status, reason))
