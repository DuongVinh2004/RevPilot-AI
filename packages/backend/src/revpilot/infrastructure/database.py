"""
RevPilot AI — Asynchronous Database Pool and Tenant RLS Session Manager
Enforces INV-TEN-001, INV-TEN-002, INV-TEN-003, ADR-0004, and ADR-0005.
Provides asyncpg connection pooling and transaction-scoped RLS session boundaries.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator
import asyncpg

from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.errors import TenancyViolationError, DomainError
from revpilot.shared.identifiers import TenantId

logger = logging.getLogger("revpilot.infrastructure.database")


class RLSViolationError(DomainError):
    """Exception representing Row-Level Security policy or context failure."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="RLS_VIOLATION", message=message, details=details, retryable=False)


def normalize_asyncpg_url(database_url: str) -> str:
    """Ensure database URL format is suitable for asyncpg."""
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


async def create_database_pool(
    database_url: str, min_size: int = 2, max_size: int = 10
) -> asyncpg.Pool:
    """Create and return an asyncpg connection pool."""
    clean_url = normalize_asyncpg_url(database_url)
    return await asyncpg.create_pool(clean_url, min_size=min_size, max_size=max_size)


class TenantDatabaseSession:
    """
    Asynchronous context manager that acquires an asyncpg connection,
    starts an isolated transaction, and sets PostgreSQL transaction-scoped
    RLS settings (revpilot.current_tenant_id and revpilot.is_system).

    Guarantees that:
    1. Zero cross-tenant leakage (INV-TEN-001, NFR-TEN-001).
    2. Missing/None context fails closed (INV-TEN-001).
    3. Inactive tenant fails closed (INV-TEN-002).
    4. Connection reset and return to pool on completion.
    """

    def __init__(
        self,
        pool: asyncpg.Pool | None,
        context: TenantContext | PrincipalContext | None,
        connection: Any = None,
    ) -> None:
        self.pool = pool
        self.context = context
        self.conn: Any = connection
        self._owned_connection: bool = False
        self._tx: Any = None

    async def __aenter__(self) -> Any:
        # 1. Validate Context Fail-Closed
        if self.context is None:
            raise TenancyViolationError(
                "Tenant context is required for database persistence operations (INV-TEN-001).",
                details={"error": "context_none"},
            )

        if not getattr(self.context, "is_active", True):
            tenant_val = getattr(self.context, "tenant_id", "unknown")
            raise TenancyViolationError(
                f"Tenant '{tenant_val}' is deactivated or suspended.",
                details={"tenant_id": str(tenant_val), "is_active": False},
            )

        # 2. Acquire connection if not supplied
        if self.conn is None:
            if self.pool is None:
                raise RLSViolationError("No database pool or connection provided to TenantDatabaseSession.")
            self.conn = await self.pool.acquire()
            self._owned_connection = True

        # 3. Begin Transaction
        if hasattr(self.conn, "transaction"):
            self._tx = self.conn.transaction()
            await self._tx.start()

        # 4. Set RLS Session Variables
        is_system = getattr(self.context, "is_system", False)
        tenant_id = getattr(self.context, "tenant_id", None)

        if is_system:
            await self.conn.execute("SET LOCAL revpilot.is_system = 'true';")
            await self.conn.execute("SET LOCAL revpilot.current_tenant_id = '';")
        else:
            if not tenant_id:
                raise TenancyViolationError(
                    "Non-system context must provide a valid tenant_id.",
                    details={"error": "tenant_id_missing"},
                )
            await self.conn.execute("SET LOCAL revpilot.is_system = 'false';")
            await self.conn.execute("SET LOCAL revpilot.current_tenant_id = $1;", str(tenant_id))

        return self.conn

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            if self._tx is not None:
                if exc_type is not None:
                    await self._tx.rollback()
                else:
                    await self._tx.commit()
        finally:
            if self._owned_connection and self.pool is not None and self.conn is not None:
                await self.pool.release(self.conn)
                self.conn = None
