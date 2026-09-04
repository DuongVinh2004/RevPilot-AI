"""
Unit tests for IsolatedTenantRepositoryAdapter.
Validates AC-R05-003-04, AC-R05-003-05, and tenant persistence isolation contracts.
"""

from __future__ import annotations
from dataclasses import dataclass
import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import TenancyViolationError
from revpilot.shared.persistence import TenantScopedRepositoryPort
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


def _create_tenant(tenant_id: TenantId, org_id: OrganizationId, name: str) -> Tenant:
    now = UtcDateTime.now()
    return Tenant(
        id=tenant_id,
        organization_id=org_id,
        name=name,
        status=TenantStatus.ACTIVE,
        tier=SubscriptionTier.SHARED,
        entitlement=Entitlement(tier=SubscriptionTier.SHARED),
        created_at=now,
        updated_at=now,
    )


def _make_context(tenant_id: TenantId, org_id: OrganizationId) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id,
        organization_id=org_id,
        tier="growth",
        is_active=True,
    )


class TestIsolatedTenantRepositoryAdapter:
    def test_implements_tenant_scoped_repository_port(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        assert isinstance(adapter, TenantScopedRepositoryPort)

    def test_save_and_retrieve_within_same_tenant(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid = TenantId.generate()
        oid = OrganizationId.generate()
        ctx = _make_context(tid, oid)
        tenant = _create_tenant(tid, oid, "Acme Corp")

        adapter.save(ctx, tenant)
        retrieved = adapter.get_by_id(ctx, str(tid))
        assert retrieved is not None
        assert retrieved.id == tid
        assert retrieved.name == "Acme Corp"

    def test_cross_tenant_read_returns_none(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)
        tenant_a = _create_tenant(tid_a, oid_a, "Tenant A")
        adapter.save(ctx_a, tenant_a)

        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        ctx_b = _make_context(tid_b, oid_b)

        # Tenant B queries Tenant A's record ID -> returns None
        retrieved = adapter.get_by_id(ctx_b, str(tid_a))
        assert retrieved is None

    def test_cross_tenant_write_raises_tenancy_violation(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)

        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        tenant_b = _create_tenant(tid_b, oid_b, "Tenant B")

        # Tenant A attempts to save Tenant B's entity
        with pytest.raises(TenancyViolationError) as exc_info:
            adapter.save(ctx_a, tenant_b)
        assert "Entity tenant" in str(exc_info.value)

    def test_cross_tenant_delete_isolation(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)
        tenant_a = _create_tenant(tid_a, oid_a, "Tenant A")
        adapter.save(ctx_a, tenant_a)

        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        ctx_b = _make_context(tid_b, oid_b)

        # Tenant B attempts to delete Tenant A's record
        adapter.delete(ctx_b, str(tid_a))

        # Record A must still exist in Tenant A's partition
        retrieved = adapter.get_by_id(ctx_a, str(tid_a))
        assert retrieved is not None
        assert retrieved.id == tid_a

    def test_list_by_tenant_scoped_strictly(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)
        tenant_a = _create_tenant(tid_a, oid_a, "Tenant A")
        adapter.save(ctx_a, tenant_a)

        tid_b = TenantId.generate()
        oid_b = OrganizationId.generate()
        ctx_b = _make_context(tid_b, oid_b)
        tenant_b = _create_tenant(tid_b, oid_b, "Tenant B")
        adapter.save(ctx_b, tenant_b)

        list_a = adapter.list_by_tenant(ctx_a)
        assert len(list_a) == 1
        assert list_a[0].id == tid_a

        list_b = adapter.list_by_tenant(ctx_b)
        assert len(list_b) == 1
        assert list_b[0].id == tid_b

    def test_rejects_null_context(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid = TenantId.generate()
        oid = OrganizationId.generate()
        tenant = _create_tenant(tid, oid, "Test")

        with pytest.raises(TenancyViolationError):
            adapter.get_by_id(None, str(tid))  # type: ignore[arg-type]
        with pytest.raises(TenancyViolationError):
            adapter.save(None, tenant)  # type: ignore[arg-type]
        with pytest.raises(TenancyViolationError):
            adapter.delete(None, str(tid))  # type: ignore[arg-type]
        with pytest.raises(TenancyViolationError):
            adapter.list_by_tenant(None)  # type: ignore[arg-type]

    def test_system_context_cross_partition_access(self) -> None:
        adapter = IsolatedTenantRepositoryAdapter()
        tid_a = TenantId.generate()
        oid_a = OrganizationId.generate()
        ctx_a = _make_context(tid_a, oid_a)
        tenant_a = _create_tenant(tid_a, oid_a, "Tenant A")
        adapter.save(ctx_a, tenant_a)

        sys_ctx = SystemTenantContext(
            tenant_id=TenantId("tnt_system"),
            organization_id=OrganizationId("org_sys"),
            is_active=True,
            is_system=True,
        )

        retrieved = adapter.get_by_id(sys_ctx, str(tid_a))
        assert retrieved is not None
        assert retrieved.id == tid_a

        all_items = adapter.list_by_tenant(sys_ctx)
        assert len(all_items) == 1
        assert all_items[0].id == tid_a
