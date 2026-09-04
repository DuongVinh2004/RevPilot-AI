"""
RevPilot AI — Tenant-Scoped Persistence Ports and Aggregate Ownership Contracts
Enforces INV-TEN-001, INV-TEN-002, INV-DATA-002, and ADR-0004.
"""

from __future__ import annotations
from typing import Any, Protocol, Sequence, TypeVar, runtime_checkable

from revpilot.shared.identifiers import TenantId
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import TenancyViolationError, ValidationError, AuthorizationError


@runtime_checkable
class TenantScopedEntity(Protocol):
    """
    Protocol requiring an explicit TenantId and unique entity string identifier (INV-TEN-001).
    """
    tenant_id: TenantId
    id: str


T = TypeVar("T", bound=TenantScopedEntity)


def verify_tenant_access(context: TenantContext, entity: TenantScopedEntity | None = None) -> None:
    """
    Verify that the tenant context is valid, active, and matches the entity tenant (INV-TEN-001, INV-TEN-002).
    Fails closed if context is None or inactive, or if tenant IDs mismatch for non-system actors.
    """
    if context is None:
        raise TenancyViolationError(
            "TenantContext is required for persistence operations (INV-TEN-001).",
            details={"error": "context_none"},
        )
    if not isinstance(context, TenantContext):
        raise TenancyViolationError(
            f"Expected TenantContext instance, got {type(context).__name__}.",
            details={"error": "invalid_context_type"},
        )
    if not context.is_active:
        raise TenancyViolationError(
            f"Tenant context '{context.tenant_id}' is inactive.",
            details={"tenant_id": str(context.tenant_id), "is_active": False},
        )

    if entity is not None:
        is_system = getattr(context, "is_system", False)
        entity_tenant = getattr(entity, "tenant_id", None)
        if entity_tenant is None and hasattr(entity, "id") and isinstance(entity.id, TenantId):
            entity_tenant = entity.id

        if not is_system and entity_tenant != context.tenant_id:
            raise TenancyViolationError(
                f"Entity tenant '{entity_tenant}' does not match context tenant '{context.tenant_id}' (INV-TEN-001).",
                details={
                    "entity_tenant": str(entity_tenant),
                    "context_tenant": str(context.tenant_id),
                },
            )


@runtime_checkable
class TenantScopedRepositoryPort(Protocol[T]):
    """
    Generic repository port protocol enforcing tenant isolation on all persistence operations.
    """

    def get_by_id(self, context: TenantContext, id: str) -> T | None:
        """
        Retrieve entity by id within context's tenant scope.
        Must reject null or inactive context with TenancyViolationError.
        """
        ...

    def save(self, context: TenantContext, entity: T) -> None:
        """
        Persist or update entity within context's tenant scope.
        Must verify context.tenant_id == entity.tenant_id (unless context.is_system).
        Raises TenancyViolationError on mismatch or invalid context.
        """
        ...

    def delete(self, context: TenantContext, id: str) -> None:
        """
        Delete entity by id within context's tenant scope.
        Must reject null or inactive context with TenancyViolationError.
        """
        ...

    def list_by_tenant(
        self, context: TenantContext, limit: int = 100, offset: int = 0
    ) -> Sequence[T]:
        """
        List entities belonging strictly to context's tenant.
        Must reject null or inactive context with TenancyViolationError.
        """
        ...


class AggregateOwnershipRegistry:
    """
    Registry enforcing single-module write ownership for aggregates (INV-DATA-002).
    Every aggregate must be exclusively owned by exactly one module.
    """

    def __init__(self) -> None:
        self._owners: dict[str, str] = {}

    def register(self, aggregate_type: str, owning_module: str) -> None:
        """
        Register write ownership of an aggregate type to a specific module.
        Raises ValidationError if aggregate is already registered to a different module.
        """
        if not aggregate_type or not isinstance(aggregate_type, str):
            raise ValidationError("aggregate_type must be a non-empty string.")
        if not owning_module or not isinstance(owning_module, str):
            raise ValidationError("owning_module must be a non-empty string.")

        aggregate_key = aggregate_type.strip().lower()
        module_key = owning_module.strip().lower()

        existing = self._owners.get(aggregate_key)
        if existing is not None and existing != module_key:
            raise ValidationError(
                f"Aggregate already owned by different module: '{aggregate_key}' is owned by '{existing}', "
                f"cannot register to '{module_key}'.",
                details={"aggregate": aggregate_key, "existing_owner": existing, "requested_owner": module_key},
            )

        self._owners[aggregate_key] = module_key

    def get_owner(self, aggregate_type: str) -> str:
        """
        Return owning module name for the specified aggregate type.
        Raises ValidationError if aggregate is unowned / unregistered.
        """
        if not aggregate_type or not isinstance(aggregate_type, str):
            raise ValidationError("aggregate_type must be a non-empty string.")

        aggregate_key = aggregate_type.strip().lower()
        owner = self._owners.get(aggregate_key)
        if owner is None:
            raise ValidationError(
                f"Aggregate '{aggregate_type}' is unowned or not registered.",
                details={"aggregate": aggregate_key},
            )
        return owner

    def assert_owner(self, aggregate_type: str, calling_module: str) -> None:
        """
        Verify that calling_module owns aggregate_type.
        Raises AuthorizationError if calling_module is not the registered owner.
        """
        if not calling_module or not isinstance(calling_module, str):
            raise AuthorizationError("calling_module must be a non-empty string.")

        owner = self.get_owner(aggregate_type)
        calling_key = calling_module.strip().lower()
        if owner != calling_key:
            raise AuthorizationError(
                f"Module '{calling_module}' is not authorized to modify aggregate '{aggregate_type}'. "
                f"Exclusive owner is '{owner}' (INV-DATA-002).",
                details={"aggregate": aggregate_type, "owner": owner, "caller": calling_module},
            )

    def clear(self) -> None:
        """Clear all registered ownership mappings (primarily for test resets)."""
        self._owners.clear()


# Ensure Tenant aggregate satisfies TenantScopedEntity protocol if imported
try:
    from revpilot.modules.tenancy.domain.models import Tenant
    if not hasattr(Tenant, "tenant_id"):
        Tenant.tenant_id = property(lambda self: self.id)  # type: ignore[attr-defined]
except ImportError:
    pass
