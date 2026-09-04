"""
RevPilot AI — Tenancy Repository Ports
Abstract persistence contracts for tenant and organization querying and mutation.
Conforms to ADR-0001, MODULE-BOUNDARIES.md, and DEPENDENCY-RULES.md.
"""

from __future__ import annotations
from typing import Protocol, runtime_checkable

from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.modules.tenancy.domain.models import Tenant, Organization, TenantStatus


@runtime_checkable
class TenantQueryPort(Protocol):
    """Read-only query interface for tenant and organization aggregates."""

    def get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieve tenant aggregate by unique TenantId, or None if not found."""
        ...

    def get_by_organization(self, organization_id: OrganizationId) -> list[Tenant]:
        """Retrieve all tenants associated with an OrganizationId."""
        ...

    def get_organization_by_id(self, organization_id: OrganizationId) -> Organization | None:
        """Retrieve organization aggregate by unique OrganizationId, or None if not found."""
        ...

    def exists(self, tenant_id: TenantId) -> bool:
        """Check whether a tenant exists by unique TenantId."""
        ...


@runtime_checkable
class TenantCommandPort(Protocol):
    """Command/mutation interface for tenant and organization lifecycle."""

    def save_tenant(self, tenant: Tenant) -> None:
        """Persist or update tenant aggregate."""
        ...

    def save_organization(self, organization: Organization) -> None:
        """Persist or update organization entity."""
        ...

    def update_status(
        self, tenant_id: TenantId, status: TenantStatus, reason: str | None = None
    ) -> Tenant:
        """Update status and lifecycle state of a tenant."""
        ...
