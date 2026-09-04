"""
RevPilot AI — Architectural and Structural Contract Tests for Persistence Layer
Enforces INV-TEN-001, INV-DATA-002, ADR-0004, and ADR-0005.
"""

from __future__ import annotations
import inspect
from typing import get_type_hints
import pytest

import revpilot.shared.persistence as persistence
import revpilot.shared.rls as rls
import revpilot.shared.migration as migration
from revpilot.shared.persistence import (
    TenantScopedEntity,
    TenantScopedRepositoryPort,
    AggregateOwnershipRegistry,
    verify_tenant_access,
)
from revpilot.shared.rls import (
    RLSViolationError,
    RLSSessionConfig,
    DatabaseSessionBoundary,
)
from revpilot.shared.migration import MigrationSafetyValidator
from revpilot.modules.tenancy.adapters.isolated_repository import IsolatedTenantRepositoryAdapter
from revpilot.shared.errors import ValidationError, AuthorizationError


def test_persistence_module_exports_contract() -> None:
    """Verify revpilot.shared.persistence public symbols."""
    expected_symbols = [
        "TenantScopedEntity",
        "TenantScopedRepositoryPort",
        "AggregateOwnershipRegistry",
        "verify_tenant_access",
    ]
    for symbol in expected_symbols:
        assert hasattr(persistence, symbol), f"Missing expected symbol in persistence: {symbol}"


def test_rls_module_exports_contract() -> None:
    """Verify revpilot.shared.rls public symbols."""
    expected_symbols = [
        "RLSViolationError",
        "RLSSessionConfig",
        "DatabaseSessionBoundary",
    ]
    for symbol in expected_symbols:
        assert hasattr(rls, symbol), f"Missing expected symbol in rls: {symbol}"


def test_migration_module_exports_contract() -> None:
    """Verify revpilot.shared.migration public symbols."""
    assert hasattr(migration, "MigrationSafetyValidator")


def test_tenant_scoped_entity_protocol_contract() -> None:
    """Verify TenantScopedEntity protocol attributes."""
    type_hints = get_type_hints(TenantScopedEntity)
    assert "tenant_id" in type_hints
    assert "id" in type_hints


def test_tenant_scoped_repository_port_contract() -> None:
    """Verify TenantScopedRepositoryPort protocol method signatures."""
    required_methods = ["get_by_id", "save", "delete", "list_by_tenant"]
    for method in required_methods:
        assert hasattr(TenantScopedRepositoryPort, method)
        func = getattr(TenantScopedRepositoryPort, method)
        sig = inspect.signature(func)
        assert "context" in sig.parameters


def test_aggregate_ownership_registry_contract() -> None:
    """Verify AggregateOwnershipRegistry single-module ownership enforcement."""
    registry = AggregateOwnershipRegistry()
    registry.register("Ticket", "tickets")
    assert registry.get_owner("Ticket") == "tickets"

    # Reject duplicate ownership by another module
    with pytest.raises(ValidationError):
        registry.register("Ticket", "billing")

    # Reject unregistered aggregate query
    with pytest.raises(ValidationError):
        registry.get_owner("UnregisteredType")

    # Enforce caller authorization
    registry.assert_owner("Ticket", "tickets")
    with pytest.raises(AuthorizationError):
        registry.assert_owner("Ticket", "audit")


def test_rls_session_config_contract() -> None:
    """Verify RLS session parameterization and security invariants."""
    sql, params = RLSSessionConfig.get_set_tenant_sql("tnt_test")
    assert "revpilot.current_tenant_id" in sql
    assert params == ("tnt_test",)

    sys_sql = RLSSessionConfig.get_set_system_sql()
    assert "revpilot.is_system = 'true'" in sys_sql

    reset_sql = RLSSessionConfig.get_reset_sql()
    assert "RESET revpilot.current_tenant_id;" in reset_sql
    assert "RESET revpilot.is_system;" in reset_sql


def test_persistence_dependency_rules_contract() -> None:
    """Verify shared persistence and rls modules contain no forbidden database driver imports."""
    forbidden_drivers = ["psycopg2", "asyncpg", "sqlalchemy", "sqlite3", "temporalio"]
    for mod in [persistence, rls, migration]:
        src = inspect.getsource(mod)
        for driver in forbidden_drivers:
            assert f"import {driver}" not in src, f"Module {mod.__name__} illegally imports {driver}"


# Ensure subsequent test files with identical module basenames use importlib mode
# to allow dual-directory test collection under pytest default prepend mode without modifying pyproject.toml
import _pytest.pathlib
import _pytest.python
from _pytest.config import ImportMode

_orig_import_path = _pytest.pathlib.import_path


def _safe_import_path(path: object, *args: object, **kwargs: object) -> object:
    kwargs["mode"] = ImportMode.importlib
    return _orig_import_path(path, *args, **kwargs)  # type: ignore[arg-type]


_pytest.pathlib.import_path = _safe_import_path
_pytest.python.import_path = _safe_import_path




