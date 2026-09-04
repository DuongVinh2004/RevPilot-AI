"""
RevPilot AI — Transactional Tenant Context and RLS Enforcement Contract
Enforces INV-TEN-001, INV-TEN-003, ADR-0004, and ADR-0005.
"""

from __future__ import annotations
from typing import Any, Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import DomainError, TenancyViolationError


class RLSViolationError(DomainError):
    """Exception representing Row-Level Security policy, configuration, or context failure."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="RLS_VIOLATION", message=message, details=details, retryable=False)


class RLSSessionConfig:
    """
    Value object generating parameterized SQL statements for transaction-scoped session isolation.
    """

    @staticmethod
    def get_set_tenant_sql(tenant_id: TenantId | str) -> tuple[str, tuple[str, ...]]:
        """
        Return parameterized SQL tuple to bind current session to tenant_id.
        Prevents SQL injection by returning statement and parameters tuple.
        """
        if not tenant_id:
            raise TenancyViolationError("tenant_id cannot be empty for RLS session.")
        tenant_str = str(tenant_id)
        sql = "SET LOCAL revpilot.current_tenant_id = %s; SET LOCAL revpilot.is_system = 'false';"
        return (sql, (tenant_str,))

    @staticmethod
    def get_set_system_sql() -> str:
        """
        Return SQL string for explicit platform system operations (INV-TEN-003).
        """
        return "SET LOCAL revpilot.current_tenant_id = ''; SET LOCAL revpilot.is_system = 'true';"

    @staticmethod
    def get_reset_sql() -> str:
        """
        Return SQL string to clean up and reset session variables on connection release.
        """
        return "RESET revpilot.current_tenant_id; RESET revpilot.is_system;"

    @staticmethod
    def get_verify_sql() -> str:
        """
        Return SQL string to query current session settings.
        """
        return "SELECT current_setting('revpilot.current_tenant_id', true), current_setting('revpilot.is_system', true);"


def _execute_sql(connection: Any, sql: str, params: tuple[Any, ...] | None = None) -> None:
    """Execute SQL statement on connection or cursor."""
    if hasattr(connection, "cursor"):
        cursor = connection.cursor()
        if hasattr(cursor, "__enter__") and hasattr(cursor, "__exit__"):
            with cursor as cur:
                if params is not None:
                    cur.execute(sql, params)
                else:
                    cur.execute(sql)
        else:
            if params is not None:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            if hasattr(cursor, "close"):
                cursor.close()
    elif hasattr(connection, "execute"):
        if params is not None:
            connection.execute(sql, params)
        else:
            connection.execute(sql)


class DatabaseSessionBoundary:
    """
    Context manager establishing and cleaning up transaction-scoped PostgreSQL RLS session variables.
    Fails closed if TenantContext is None or invalid (INV-TEN-001).
    """

    def __init__(self, connection: Any, context: TenantContext | None = None) -> None:
        self.connection = connection
        self.context = context

    def __enter__(self) -> Any:
        if self.context is None:
            raise TenancyViolationError("Cannot establish database session without TenantContext (INV-TEN-001).")

        if not getattr(self.context, "is_active", True):
            raise TenancyViolationError(
                f"Cannot establish database session: tenant '{self.context.tenant_id}' is inactive."
            )

        is_system = getattr(self.context, "is_system", False)
        if is_system:
            sql = RLSSessionConfig.get_set_system_sql()
            _execute_sql(self.connection, sql)
        else:
            sql, params = RLSSessionConfig.get_set_tenant_sql(self.context.tenant_id)
            _execute_sql(self.connection, sql, params)

        return self.connection

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            reset_sql = RLSSessionConfig.get_reset_sql()
            _execute_sql(self.connection, reset_sql)
        except Exception as err:
            # If reset fails, wrap in RLSViolationError if no prior exception
            if exc_type is None:
                raise RLSViolationError(f"Failed to reset RLS session settings: {err}") from err
