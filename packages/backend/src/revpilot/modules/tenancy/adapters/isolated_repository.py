"""
RevPilot AI — Isolated Tenant Repository Adapter
Reference multi-tenant repository adapter enforcing partition isolation and RLS-like context verification.
Conforms to ADR-0004, ADR-0005, and DATABASE-SCHEMA.md §8.
"""

from __future__ import annotations
from typing import Sequence

from revpilot.shared.identifiers import TenantId
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import TenancyViolationError
from revpilot.shared.persistence import TenantScopedRepositoryPort, verify_tenant_access
from revpilot.modules.tenancy.domain.models import Tenant


class IsolatedTenantRepositoryAdapter(TenantScopedRepositoryPort[Tenant]):
    """
    Concrete repository adapter simulating PostgreSQL RLS multi-tenant partitioned storage.
    Enforces that queries executed without valid context or with mismatched context fail closed.
    """

    def __init__(self) -> None:
        # Partitioned storage: tenant_id -> {entity_id: Tenant}
        self._partitions: dict[str, dict[str, Tenant]] = {}

    def get_by_id(self, context: TenantContext, id: str) -> Tenant | None:
        """
        Retrieve tenant aggregate by unique string ID within caller's tenant scope.
        Fails closed on null or inactive context.
        """
        verify_tenant_access(context)

        is_system = getattr(context, "is_system", False)
        if is_system:
            for partition in self._partitions.values():
                if id in partition:
                    return partition[id]
            return None

        partition = self._partitions.get(str(context.tenant_id), {})
        return partition.get(id)

    def save(self, context: TenantContext, entity: Tenant) -> None:
        """
        Persist or update tenant aggregate within caller's tenant scope.
        Fails closed on context mismatch or inactive context.
        """
        verify_tenant_access(context, entity)

        entity_tenant_str = str(getattr(entity, "tenant_id", entity.id))
        partition = self._partitions.setdefault(entity_tenant_str, {})
        partition[str(entity.id)] = entity

    def delete(self, context: TenantContext, id: str) -> None:
        """
        Delete tenant aggregate by ID within caller's tenant scope.
        Fails closed on null or inactive context.
        """
        verify_tenant_access(context)

        is_system = getattr(context, "is_system", False)
        if is_system:
            for partition in self._partitions.values():
                partition.pop(id, None)
            return

        partition = self._partitions.get(str(context.tenant_id), {})
        partition.pop(id, None)

    def list_by_tenant(
        self, context: TenantContext, limit: int = 100, offset: int = 0
    ) -> Sequence[Tenant]:
        """
        List all tenant aggregates strictly belonging to caller's tenant scope.
        """
        verify_tenant_access(context)

        is_system = getattr(context, "is_system", False)
        if is_system:
            all_items = [t for part in self._partitions.values() for t in part.values()]
            return all_items[offset : offset + limit]

        partition = self._partitions.get(str(context.tenant_id), {})
        items = list(partition.values())
        return items[offset : offset + limit]
