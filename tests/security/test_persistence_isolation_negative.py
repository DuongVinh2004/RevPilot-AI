"""
RevPilot AI — Persistence Isolation Negative Test Matrix (Rail 5 Exit Gate)
Exhaustive verification of fail-closed persistence isolation across boundary surfaces.
Enforces INV-TEN-001, INV-TEN-002, INV-TEN-003, INV-DATA-001, INV-DATA-002, NFR-TEN-001, ADR-0004, ADR-0005.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.errors import TenancyViolationError, ValidationError, AuthorizationError
from revpilot.shared.persistence import verify_tenant_access
from revpilot.shared.rls import (
    RLSViolationError,
    RLSSessionConfig,
    DatabaseSessionBoundary,
)
from revpilot.shared.migration import MigrationSafetyValidator
from revpilot.modules.tenancy.domain.models import (
    Tenant,
    TenantStatus,
    SubscriptionTier,
    Entitlement,
)
from revpilot.modules.tenancy.adapters.isolated_repository import IsolatedTenantRepositoryAdapter


@dataclass(frozen=True, slots=True)
class SystemTenantContext(TenantContext):
    is_system: bool = True


class MockConnectionPool:
    """Simulates database connection pool managing reusable connections."""

    def __init__(self) -> None:
        self.session_log: list[str] = []
        self.current_session_vars: dict[str, str] = {}

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.session_log.append(sql)
        if "SET LOCAL revpilot.current_tenant_id" in sql:
            if params:
                self.current_session_vars["tenant_id"] = params[0]
            elif "revpilot.current_tenant_id = ''" in sql:
                self.current_session_vars["tenant_id"] = ""
            if "revpilot.is_system = 'true'" in sql:
                self.current_session_vars["is_system"] = "true"
            elif "revpilot.is_system = 'false'" in sql:
                self.current_session_vars["is_system"] = "false"
        elif "RESET revpilot.current_tenant_id" in sql:
            self.current_session_vars.clear()


def _create_tenant_entity(tenant_id: TenantId, org_id: OrganizationId, name: str) -> Tenant:
    now = UtcDateTime.now()
    return Tenant(
        id=tenant_id,
        organization_id=org_id,
        name=name,
        status=TenantStatus.ACTIVE,
        tier=SubscriptionTier.ENTERPRISE,
        entitlement=Entitlement(tier=SubscriptionTier.ENTERPRISE),
        created_at=now,
        updated_at=now,
    )


def _make_context(tenant_id: TenantId, org_id: OrganizationId, is_active: bool = True) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id,
        organization_id=org_id,
        tier="enterprise",
        is_active=is_active,
    )


class TestNullAndMissingContextNegativeMatrix:
    """AC-R05-004-01: Null, missing, or invalid context fails closed."""

    def test_repository_get_by_id_null_context(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        with pytest.raises(TenancyViolationError) as exc_info:
            adapter.get_by_id(None, "any_id")  # type: ignore[arg-type]
        assert exc_info.value.code == "TENANCY_VIOLATION"

    def test_repository_save_null_context(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid = TenantId.generate()
        oid = OrganizationId.generate()
        tenant = _create_tenant_entity(tid, oid, "T1")
        with pytest.raises(TenancyViolationError) as exc_info:
            adapter.save(None, tenant)  # type: ignore[arg-type]
        assert exc_info.value.code == "TENANCY_VIOLATION"

    def test_repository_delete_null_context(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        with pytest.raises(TenancyViolationError) as exc_info:
            adapter.delete(None, "any_id")  # type: ignore[arg-type]
        assert exc_info.value.code == "TENANCY_VIOLATION"

    def test_repository_list_null_context(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        with pytest.raises(TenancyViolationError) as exc_info:
            adapter.list_by_tenant(None)  # type: ignore[arg-type]
        assert exc_info.value.code == "TENANCY_VIOLATION"

    def test_database_session_boundary_null_context(self) -> None:
        conn = MockConnectionPool()
        with pytest.raises(TenancyViolationError) as exc_info:
            with DatabaseSessionBoundary(conn, None):
                pass
        assert exc_info.value.code == "TENANCY_VIOLATION"
        assert len(conn.session_log) == 0


class TestCrossTenantReadNegativeMatrix:
    """AC-R05-004-02: Tenant A cannot read Tenant B record (fail-closed isolation)."""

    def test_tenant_a_cannot_read_tenant_b_record(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)
        tenant_a = _create_tenant_entity(tid_a, oid_a, "Tenant A Record")
        adapter.save(ctx_a, tenant_a)

        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        ctx_b = _make_context(tid_b, oid_b)
        tenant_b = _create_tenant_entity(tid_b, oid_b, "Tenant B Record")
        adapter.save(ctx_b, tenant_b)

        # Cross-tenant read attempts must return None
        assert adapter.get_by_id(ctx_a, str(tid_b)) is None
        assert adapter.get_by_id(ctx_b, str(tid_a)) is None

    def test_tenant_a_list_excludes_tenant_b_records(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)
        adapter.save(ctx_a, _create_tenant_entity(tid_a, oid_a, "A1"))

        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        ctx_b = _make_context(tid_b, oid_b)
        adapter.save(ctx_b, _create_tenant_entity(tid_b, oid_b, "B1"))

        list_a = adapter.list_by_tenant(ctx_a)
        assert len(list_a) == 1
        assert list_a[0].id == tid_a

        list_b = adapter.list_by_tenant(ctx_b)
        assert len(list_b) == 1
        assert list_b[0].id == tid_b


class TestCrossTenantWriteNegativeMatrix:
    """AC-R05-004-03: Tenant A cannot write or modify Tenant B record."""

    def test_tenant_a_cannot_save_tenant_b_entity(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)

        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        tenant_b = _create_tenant_entity(tid_b, oid_b, "Tenant B Foreign Entity")

        with pytest.raises(TenancyViolationError) as exc_info:
            adapter.save(ctx_a, tenant_b)
        assert exc_info.value.code == "TENANCY_VIOLATION"
        assert str(tid_b) in str(exc_info.value)

    def test_cross_tenant_update_hijack_prevention(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)
        tenant_a = _create_tenant_entity(tid_a, oid_a, "Original A")
        adapter.save(ctx_a, tenant_a)

        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        ctx_b = _make_context(tid_b, oid_b)

        # Malicious entity crafted with tenant_a ID but attempted write under ctx_b
        spoofed_entity = _create_tenant_entity(tid_a, oid_a, "Hijacked Name")
        with pytest.raises(TenancyViolationError):
            adapter.save(ctx_b, spoofed_entity)

        # Verify original record unmodified
        unmodified = adapter.get_by_id(ctx_a, str(tid_a))
        assert unmodified is not None
        assert unmodified.name == "Original A"


class TestCrossTenantDeleteNegativeMatrix:
    """AC-R05-004-04: Tenant A cannot delete Tenant B record."""

    def test_tenant_a_cannot_delete_tenant_b_record(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        ctx_b = _make_context(tid_b, oid_b)
        tenant_b = _create_tenant_entity(tid_b, oid_b, "Tenant B Protected Record")
        adapter.save(ctx_b, tenant_b)

        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)

        # Tenant A attempts to delete Tenant B's record
        adapter.delete(ctx_a, str(tid_b))

        # Tenant B's record must still be intact
        retrieved = adapter.get_by_id(ctx_b, str(tid_b))
        assert retrieved is not None
        assert retrieved.id == tid_b


class TestRLSSessionStateIsolationNegativeMatrix:
    """AC-R05-004-05: Connection reuse across transactions leaves zero residual context."""

    def test_connection_pool_sequential_tenant_isolation(self) -> None:
        conn = MockConnectionPool()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)

        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        ctx_b = _make_context(tid_b, oid_b)

        # Transaction 1: Tenant A
        with DatabaseSessionBoundary(conn, ctx_a):
            assert conn.current_session_vars.get("tenant_id") == str(tid_a)
            assert conn.current_session_vars.get("is_system") == "false"

        # On release: variables must be reset
        assert len(conn.current_session_vars) == 0

        # Transaction 2: Tenant B
        with DatabaseSessionBoundary(conn, ctx_b):
            assert conn.current_session_vars.get("tenant_id") == str(tid_b)
            assert conn.current_session_vars.get("is_system") == "false"

        # On release: variables reset
        assert len(conn.current_session_vars) == 0

    def test_connection_pool_reset_on_transaction_exception(self) -> None:
        conn = MockConnectionPool()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)

        with pytest.raises(RuntimeError):
            with DatabaseSessionBoundary(conn, ctx_a):
                assert conn.current_session_vars.get("tenant_id") == str(tid_a)
                raise RuntimeError("Simulated transaction rollback")

        # Must have been cleanly reset despite exception
        assert len(conn.current_session_vars) == 0


class TestMigrationSafetyNegativeMatrix:
    """AC-R05-004-06: Prohibited destructive DDL is strictly rejected."""

    @pytest.mark.parametrize(
        "prohibited_ddl,expected_msg",
        [
            ("ALTER TABLE accounts DROP COLUMN balance;", "Destructive column drop prohibited"),
            ("ALTER TABLE accounts drop column balance;", "Destructive column drop prohibited"),
            ("ALTER TABLE users RENAME COLUMN email TO user_email;", "Direct column rename prohibited"),
            ("ALTER TABLE users rename column email to user_email;", "Direct column rename prohibited"),
            ("DROP TABLE billing_invoices;", "Dropping table prohibited without authorization"),
            ("drop table billing_invoices;", "Dropping table prohibited without authorization"),
            (
                "ALTER TABLE metrics ADD COLUMN score FLOAT NOT NULL;",
                "Adding NOT NULL column without DEFAULT is prohibited",
            ),
            (
                "ALTER TABLE events ADD COLUMN payload JSONB NOT NULL;",
                "Adding NOT NULL column without DEFAULT is prohibited",
            ),
        ],
    )
    def test_prohibited_ddl_raises_validation_error(self, prohibited_ddl: str, expected_msg: str) -> None:
        with pytest.raises(ValidationError) as exc_info:
            MigrationSafetyValidator.validate_ddl(prohibited_ddl)
        assert expected_msg in str(exc_info.value)


class TestPrivilegedSystemContextNegativeMatrix:
    """INV-TEN-003: Platform operations must be explicit; unprivileged null tenant rejected."""

    def test_unprivileged_principal_with_null_tenant_rejected(self) -> None:
        pid = PrincipalId.generate()
        with pytest.raises(TenancyViolationError) as exc_info:
            PrincipalContext(
                principal_id=pid,
                tenant_id=None,
                is_system=False,
            )
        assert "Non-system principal requires explicit tenant_id (INV-TEN-003)" in str(exc_info.value)

    def test_privileged_system_context_explicit(self) -> None:
        pid = PrincipalId.generate()
        sys_principal = PrincipalContext(
            principal_id=pid,
            tenant_id=None,
            is_system=True,
        )
        assert sys_principal.is_system is True
        assert sys_principal.tenant_id is None
