"""
RevPilot AI — Tenancy Module
Public domain, ports, adapters, and service for tenant context and lifecycle management.
Conforms to MODULE-BOUNDARIES.md §tenancy.
"""

from revpilot.modules.tenancy.domain.models import (
    TenantStatus,
    SubscriptionTier,
    Entitlement,
    Organization,
    Tenant,
    TenantProvisioningRequest,
    LegalHoldRecord,
    TenantExportBundle,
    DeletionCertificate,
)
from revpilot.modules.tenancy.domain.errors import (
    TenantLifecycleError,
    TenantSuspendedError,
    TenantInactiveError,
    LegalHoldActiveError,
    PartialProvisioningError,
    IsolationVerificationFailedError,
    DeletionIncompleteError,
)
from revpilot.modules.tenancy.ports.repository import (
    TenantQueryPort,
    TenantCommandPort,
)
from revpilot.modules.tenancy.ports.policy import TenantContextPolicy
from revpilot.modules.tenancy.adapters.in_memory_repository import (
    InMemoryTenantRepository,
)
from revpilot.modules.tenancy.service import TenantService
from revpilot.modules.tenancy.export import TenantExportService
from revpilot.modules.tenancy.deletion_saga import TenantCascadeDeletionSaga

__all__ = [
    # Domain
    "TenantStatus",
    "SubscriptionTier",
    "Entitlement",
    "Organization",
    "Tenant",
    "TenantProvisioningRequest",
    "LegalHoldRecord",
    "TenantExportBundle",
    "DeletionCertificate",
    # Errors
    "TenantLifecycleError",
    "TenantSuspendedError",
    "TenantInactiveError",
    "LegalHoldActiveError",
    "PartialProvisioningError",
    "IsolationVerificationFailedError",
    "DeletionIncompleteError",
    # Ports
    "TenantQueryPort",
    "TenantCommandPort",
    "TenantContextPolicy",
    # Adapters
    "InMemoryTenantRepository",
    # Services & Sagas
    "TenantService",
    "TenantExportService",
    "TenantCascadeDeletionSaga",
]
