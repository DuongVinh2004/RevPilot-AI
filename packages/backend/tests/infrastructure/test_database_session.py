"""
Unit tests for TenantDatabaseSession and async database pool helpers.
Enforces INV-TEN-001, INV-TEN-002, INV-TEN-003.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from revpilot.infrastructure.database import (
    TenantDatabaseSession,
    RLSViolationError,
    normalize_asyncpg_url,
)
from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.errors import TenancyViolationError
from revpilot.shared.identifiers import TenantId, OrganizationId, PrincipalId


class MockAsyncConnection:
    """Mock asyncpg connection recording executed queries."""

    def __init__(self):
        self.executed = []
        self._tx = AsyncMock()

    async def execute(self, query: str, *args):
        self.executed.append((query, args))
        return "EXECUTE_OK"

    def transaction(self):
        return self._tx


class MockAsyncPool:
    """Mock asyncpg pool."""

    def __init__(self, conn):
        self.conn = conn
        self.acquired = 0
        self.released = 0

    async def acquire(self):
        self.acquired += 1
        return self.conn

    async def release(self, conn):
        self.released += 1


@pytest.fixture
def sample_tenant_context():
    return TenantContext(
        tenant_id=TenantId("tnt_01h8abcde12345678901234567"),
        organization_id=OrganizationId("org_01h8abcde12345678901234567"),
        tier="enterprise",
        is_active=True,
    )


@pytest.fixture
def sample_system_context():
    return PrincipalContext(
        principal_id=PrincipalId("usr_system_root_001"),
        tenant_id=None,
        roles=frozenset(["SYSTEM_ADMIN"]),
        is_system=True,
    )


def test_normalize_asyncpg_url():
    assert normalize_asyncpg_url("postgresql+asyncpg://user:pw@host/db") == "postgresql://user:pw@host/db"
    assert normalize_asyncpg_url("postgres://user:pw@host/db") == "postgresql://user:pw@host/db"
    assert normalize_asyncpg_url("postgresql://user:pw@host/db") == "postgresql://user:pw@host/db"


@pytest.mark.asyncio
async def test_tenant_database_session_sets_tenant_rls(sample_tenant_context):
    conn = MockAsyncConnection()
    pool = MockAsyncPool(conn)

    async with TenantDatabaseSession(pool, sample_tenant_context) as active_conn:
        assert active_conn is conn
        # Check transaction started
        conn._tx.start.assert_awaited_once()

        # Check RLS statements executed
        queries = [q for q, _ in conn.executed]
        assert "SET LOCAL revpilot.is_system = 'false';" in queries
        assert any("revpilot.current_tenant_id" in q for q in queries)
        # Check tenant ID parameter passed correctly
        set_tenant_call = [call for call in conn.executed if "revpilot.current_tenant_id" in call[0]][0]
        assert set_tenant_call[1] == (str(sample_tenant_context.tenant_id),)

    # Check commit and pool release
    conn._tx.commit.assert_awaited_once()
    assert pool.released == 1


@pytest.mark.asyncio
async def test_tenant_database_session_sets_system_override(sample_system_context):
    conn = MockAsyncConnection()
    pool = MockAsyncPool(conn)

    async with TenantDatabaseSession(pool, sample_system_context) as active_conn:
        assert active_conn is conn
        queries = [q for q, _ in conn.executed]
        assert "SET LOCAL revpilot.is_system = 'true';" in queries
        assert "SET LOCAL revpilot.current_tenant_id = '';" in queries

    conn._tx.commit.assert_awaited_once()
    assert pool.released == 1


@pytest.mark.asyncio
async def test_tenant_database_session_none_context_fails_closed():
    conn = MockAsyncConnection()
    pool = MockAsyncPool(conn)

    with pytest.raises(TenancyViolationError) as exc_info:
        async with TenantDatabaseSession(pool, None):
            pass

    assert "INV-TEN-001" in str(exc_info.value.message)
    assert pool.acquired == 0


@pytest.mark.asyncio
async def test_tenant_database_session_rolls_back_on_error(sample_tenant_context):
    conn = MockAsyncConnection()
    pool = MockAsyncPool(conn)

    with pytest.raises(ValueError, match="Simulated database write error"):
        async with TenantDatabaseSession(pool, sample_tenant_context):
            raise ValueError("Simulated database write error")

    conn._tx.rollback.assert_awaited_once()
    conn._tx.commit.assert_not_awaited()
    assert pool.released == 1
