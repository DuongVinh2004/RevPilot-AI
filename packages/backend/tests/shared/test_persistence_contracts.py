"""
Unit and contract tests for shared persistence protocols and aggregate ownership registry.
Validates AC-R05-001-01 through AC-R05-001-05.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import TenancyViolationError, ValidationError, AuthorizationError
from revpilot.shared.persistence import (
    TenantScopedEntity,
    TenantScopedRepositoryPort,
    AggregateOwnershipRegistry,
    verify_tenant_access,
)


@dataclass
class DummyTenantEntity:
    tenant_id: TenantId
    id: str
    name: str = "test-entity"


@dataclass(frozen=True, slots=True)
class SystemTenantContext(TenantContext):
    is_system: bool = True


class DummyTenantRepository:
    """Mock implementation of TenantScopedRepositoryPort."""

    def __init__(self) -> None:
        self.items: dict[str, DummyTenantEntity] = {}

    def get_by_id(self, context: TenantContext, id: str) -> DummyTenantEntity | None:
        verify_tenant_access(context)
        entity = self.items.get(id)
        if entity is None:
            return None
        verify_tenant_access(context, entity)
        return entity

    def save(self, context: TenantContext, entity: DummyTenantEntity) -> None:
        verify_tenant_access(context, entity)
        self.items[entity.id] = entity

    def delete(self, context: TenantContext, id: str) -> None:
        verify_tenant_access(context)
        if id in self.items:
            verify_tenant_access(context, self.items[id])
            del self.items[id]

    def list_by_tenant(
        self, context: TenantContext, limit: int = 100, offset: int = 0
    ) -> Sequence[DummyTenantEntity]:
        verify_tenant_access(context)
        tenant_items = [e for e in self.items.values() if e.tenant_id == context.tenant_id]
        return tenant_items[offset : offset + limit]


def _make_context(tenant_id: str = "tnt_alpha", is_active: bool = True) -> TenantContext:
    return TenantContext(
        tenant_id=TenantId(tenant_id),
        organization_id=OrganizationId("org_test"),
        tier="growth",
        is_active=is_active,
    )


class TestTenantScopedEntityProtocol:
    def test_entity_protocol_conformance(self) -> None:
        tid = TenantId.generate()
        entity = DummyTenantEntity(tenant_id=tid, id="ent_001")
        assert isinstance(entity, TenantScopedEntity)

    def test_non_conforming_entity_lacks_tenant_id(self) -> None:
        @dataclass
        class IncompleteEntity:
            id: str

        inc = IncompleteEntity(id="123")
        assert not isinstance(inc, TenantScopedEntity)


class TestTenantScopedRepositoryPort:
    def test_repository_port_conformance(self) -> None:
        repo = DummyTenantRepository()
        assert isinstance(repo, TenantScopedRepositoryPort)

    def test_repository_operations_with_valid_context(self) -> None:
        repo = DummyTenantRepository()
        ctx = _make_context()
        entity = DummyTenantEntity(tenant_id=ctx.tenant_id, id="item_1")

        repo.save(ctx, entity)
        retrieved = repo.get_by_id(ctx, "item_1")
        assert retrieved == entity

        listing = repo.list_by_tenant(ctx)
        assert len(listing) == 1
        assert listing[0] == entity

        repo.delete(ctx, "item_1")
        assert repo.get_by_id(ctx, "item_1") is None

    def test_repository_rejects_none_context(self) -> None:
        repo = DummyTenantRepository()
        entity = DummyTenantEntity(tenant_id=TenantId("tnt_alpha"), id="item_1")
        with pytest.raises(TenancyViolationError):
            repo.save(None, entity)  # type: ignore[arg-type]
        with pytest.raises(TenancyViolationError):
            repo.get_by_id(None, "item_1")  # type: ignore[arg-type]
        with pytest.raises(TenancyViolationError):
            repo.delete(None, "item_1")  # type: ignore[arg-type]
        with pytest.raises(TenancyViolationError):
            repo.list_by_tenant(None)  # type: ignore[arg-type]

    def test_repository_rejects_inactive_context(self) -> None:
        # TenantContext constructor itself raises TenancyViolationError if is_active=False
        with pytest.raises(TenancyViolationError):
            _make_context(is_active=False)

    def test_repository_rejects_mismatched_tenant_entity(self) -> None:
        repo = DummyTenantRepository()
        ctx_a = _make_context("tnt_alpha")
        entity_b = DummyTenantEntity(tenant_id=TenantId("tnt_beta"), id="item_b")

        with pytest.raises(TenancyViolationError) as exc_info:
            repo.save(ctx_a, entity_b)
        assert "Entity tenant 'tnt_beta' does not match context tenant 'tnt_alpha'" in str(exc_info.value)

    def test_system_context_allows_cross_tenant_save(self) -> None:
        repo = DummyTenantRepository()
        ctx = SystemTenantContext(
            tenant_id=TenantId("tnt_system"),
            organization_id=OrganizationId("org_sys"),
            is_active=True,
            is_system=True,
        )

        entity_b = DummyTenantEntity(tenant_id=TenantId("tnt_beta"), id="item_b")
        repo.save(ctx, entity_b)
        assert repo.items["item_b"] == entity_b


class TestAggregateOwnershipRegistry:
    def test_registration_and_get_owner(self) -> None:
        registry = AggregateOwnershipRegistry()
        registry.register("Tenant", "tenancy")
        registry.register("Principal", "identity")

        assert registry.get_owner("Tenant") == "tenancy"
        assert registry.get_owner("tenant") == "tenancy"
        assert registry.get_owner("Principal") == "identity"

    def test_duplicate_registration_same_module_allowed(self) -> None:
        registry = AggregateOwnershipRegistry()
        registry.register("Anomaly", "detection")
        registry.register("Anomaly", "detection")
        assert registry.get_owner("Anomaly") == "detection"

    def test_duplicate_registration_different_module_raises(self) -> None:
        registry = AggregateOwnershipRegistry()
        registry.register("Investigation", "intelligence")
        with pytest.raises(ValidationError) as exc_info:
            registry.register("Investigation", "governance")
        assert "Aggregate already owned by different module" in str(exc_info.value)

    def test_unregistered_aggregate_raises_validation_error(self) -> None:
        registry = AggregateOwnershipRegistry()
        with pytest.raises(ValidationError) as exc_info:
            registry.get_owner("UnknownAggregate")
        assert "unowned or not registered" in str(exc_info.value)

    def test_assert_owner_success(self) -> None:
        registry = AggregateOwnershipRegistry()
        registry.register("Metric", "metrics")
        registry.assert_owner("Metric", "metrics")
        registry.assert_owner("metric", "METRICS")

    def test_assert_owner_mismatch_raises_authorization_error(self) -> None:
        registry = AggregateOwnershipRegistry()
        registry.register("Metric", "metrics")
        with pytest.raises(AuthorizationError) as exc_info:
            registry.assert_owner("Metric", "billing")
        assert "Module 'billing' is not authorized to modify aggregate 'Metric'" in str(exc_info.value)

    def test_clear_resets_registry(self) -> None:
        registry = AggregateOwnershipRegistry()
        registry.register("Order", "billing")
        assert registry.get_owner("Order") == "billing"
        registry.clear()
        with pytest.raises(ValidationError):
            registry.get_owner("Order")
