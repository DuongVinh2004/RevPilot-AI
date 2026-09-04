"""
RevPilot AI — In-Memory Tenancy Repository
Adapter implementing TenantQueryPort and TenantCommandPort for testing and local execution.
"""

from __future__ import annotations
import threading

from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import NotFoundError
from revpilot.modules.tenancy.domain.models import Tenant, Organization, TenantStatus
from revpilot.modules.tenancy.ports.repository import TenantQueryPort, TenantCommandPort


class InMemoryTenantRepository(TenantQueryPort, TenantCommandPort):
    """
    Thread-safe in-memory store for tenants and organizations.
    """

    def __init__(self) -> None:
        self._tenants: dict[TenantId, Tenant] = {}
        self._organizations: dict[OrganizationId, Organization] = {}
        self._lock = threading.RLock()

    def get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        with self._lock:
            return self._tenants.get(tenant_id)

    def get_by_organization(self, organization_id: OrganizationId) -> list[Tenant]:
        with self._lock:
            return [t for t in self._tenants.values() if t.organization_id == organization_id]

    def get_organization_by_id(self, organization_id: OrganizationId) -> Organization | None:
        with self._lock:
            return self._organizations.get(organization_id)

    def exists(self, tenant_id: TenantId) -> bool:
        with self._lock:
            return tenant_id in self._tenants

    def save_tenant(self, tenant: Tenant) -> None:
        with self._lock:
            self._tenants[tenant.id] = tenant

    def save_organization(self, organization: Organization) -> None:
        with self._lock:
            self._organizations[organization.id] = organization

    def update_status(
        self, tenant_id: TenantId, status: TenantStatus, reason: str | None = None
    ) -> Tenant:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                raise NotFoundError(
                    f"Tenant '{tenant_id}' not found",
                    details={"tenant_id": str(tenant_id)},
                )
            if status == TenantStatus.ACTIVE:
                tenant.activate()
            elif status == TenantStatus.SUSPENDED:
                tenant.suspend(reason or "Administrative suspension")
            elif status == TenantStatus.LEGAL_HOLD:
                tenant.apply_legal_hold()
            elif status == TenantStatus.DELETION_STAGED:
                tenant.stage_deletion()
            elif status == TenantStatus.DELETED:
                tenant.mark_deleted()
            elif status == TenantStatus.DEACTIVATED:
                tenant.deactivate()
            else:
                tenant.status = status
                tenant.updated_at = UtcDateTime.now()
            return tenant
