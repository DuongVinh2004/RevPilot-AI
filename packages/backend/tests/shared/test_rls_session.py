"""
Unit tests for RLSSessionConfig and DatabaseSessionBoundary.
Validates AC-R05-002-01 through AC-R05-002-06.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import DomainError, TenancyViolationError
from revpilot.shared.rls import (
    RLSViolationError,
    RLSSessionConfig,
    DatabaseSessionBoundary,
)


@dataclass(frozen=True, slots=True)
class SystemTenantContext(TenantContext):
    is_system: bool = True


class MockCursor:
    def __init__(self, connection: MockConnection) -> None:
        self.connection = connection

    def __enter__(self) -> MockCursor:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.connection.executed_queries.append((sql, params))


class MockConnection:
    def __init__(self) -> None:
        self.executed_queries: list[tuple[str, tuple[Any, ...] | None]] = []

    def cursor(self) -> MockCursor:
        return MockCursor(self)


def _make_context(tenant_id: str = "tnt_acme") -> TenantContext:
    return TenantContext(
        tenant_id=TenantId(tenant_id),
        organization_id=OrganizationId("org_acme"),
        tier="enterprise",
        is_active=True,
    )


class TestRLSSessionConfig:
    def test_get_set_tenant_sql_parameterized(self) -> None:
        tid = TenantId("tnt_prod_1")
        sql, params = RLSSessionConfig.get_set_tenant_sql(tid)
        assert "%s" in sql
        assert "revpilot.current_tenant_id" in sql
        assert "revpilot.is_system = 'false'" in sql
        assert params == ("tnt_prod_1",)

    def test_get_set_system_sql(self) -> None:
        sql = RLSSessionConfig.get_set_system_sql()
        assert "revpilot.current_tenant_id = ''" in sql
        assert "revpilot.is_system = 'true'" in sql

    def test_get_reset_sql(self) -> None:
        sql = RLSSessionConfig.get_reset_sql()
        assert "RESET revpilot.current_tenant_id;" in sql
        assert "RESET revpilot.is_system;" in sql

    def test_get_verify_sql(self) -> None:
        sql = RLSSessionConfig.get_verify_sql()
        assert "current_setting('revpilot.current_tenant_id', true)" in sql
        assert "current_setting('revpilot.is_system', true)" in sql


class TestDatabaseSessionBoundary:
    def test_enter_with_valid_tenant_context(self) -> None:
        conn = MockConnection()
        ctx = _make_context("tnt_alpha")

        with DatabaseSessionBoundary(conn, ctx) as session_conn:
            assert session_conn is conn
            assert len(conn.executed_queries) == 1
            sql, params = conn.executed_queries[0]
            assert "revpilot.current_tenant_id = %s" in sql
            assert params == ("tnt_alpha",)

        # On exit, RESET was executed
        assert len(conn.executed_queries) == 2
        reset_sql, reset_params = conn.executed_queries[1]
        assert "RESET revpilot.current_tenant_id;" in reset_sql
        assert reset_params is None

    def test_enter_with_system_context(self) -> None:
        conn = MockConnection()
        ctx = SystemTenantContext(
            tenant_id=TenantId("tnt_sys"),
            organization_id=OrganizationId("org_sys"),
            is_active=True,
            is_system=True,
        )

        with DatabaseSessionBoundary(conn, ctx):
            assert len(conn.executed_queries) == 1
            sql, params = conn.executed_queries[0]
            assert "revpilot.is_system = 'true'" in sql
            assert params is None

        assert len(conn.executed_queries) == 2
        assert "RESET revpilot.current_tenant_id;" in conn.executed_queries[1][0]

    def test_enter_with_none_context_raises_tenancy_violation(self) -> None:
        conn = MockConnection()
        with pytest.raises(TenancyViolationError) as exc_info:
            with DatabaseSessionBoundary(conn, None):
                pass
        assert "Cannot establish database session without TenantContext" in str(exc_info.value)
        assert len(conn.executed_queries) == 0

    def test_exit_always_executes_reset_on_exception(self) -> None:
        conn = MockConnection()
        ctx = _make_context("tnt_err")

        with pytest.raises(ValueError, match="internal error"):
            with DatabaseSessionBoundary(conn, ctx):
                raise ValueError("internal error")

        # Must have executed SET then RESET
        assert len(conn.executed_queries) == 2
        assert "revpilot.current_tenant_id = %s" in conn.executed_queries[0][0]
        assert "RESET revpilot.current_tenant_id;" in conn.executed_queries[1][0]


class TestRLSViolationError:
    def test_error_attributes_and_hierarchy(self) -> None:
        err = RLSViolationError("RLS policy violated", details={"table": "events"})
        assert isinstance(err, DomainError)
        assert isinstance(err, Exception)
        assert err.code == "RLS_VIOLATION"
        assert err.message == "RLS policy violated"
        assert err.details == {"table": "events"}
        assert err.retryable is False
