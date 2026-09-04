"""
RevPilot AI — TC-P07-001: Tenant Provisioning Idempotency Test
Specification: docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md §3.1
Conforms to INV-TEN-001 and NFR-TEN-001.
"""

import pytest

from revpilot.shared.identifiers import OrganizationId, TenantId, UUIDv7
from revpilot.modules.tenancy import (
    InMemoryTenantRepository,
    TenantService,
    TenantProvisioningRequest,
    SubscriptionTier,
    TenantStatus,
)


def test_tenant_provisioning_idempotency():
    """
    TC-P07-001: Repeated provisioning calls with the same idempotency key yield
    consistent aggregate state without generating duplicate tenant records.
    """
    repo = InMemoryTenantRepository()
    svc = TenantService(query_port=repo, command_port=repo)

    org = svc.create_organization("Acme Corp Global")
    idempotency_key = f"idemp_prov_{UUIDv7.generate()}"
    designated_tid = TenantId.generate()

    req1 = TenantProvisioningRequest(
        request_id=UUIDv7.generate(),
        organization_id=org.id,
        name="Acme North America",
        admin_email="admin@acme.com",
        tier=SubscriptionTier.ENTERPRISE,
        tenant_id=designated_tid,
        idempotency_key=idempotency_key,
    )

    # First provisioning invocation
    tenant1 = svc.provision_tenant_idempotent(req1)
    assert tenant1.id == designated_tid
    assert tenant1.status == TenantStatus.ACTIVATING
    assert tenant1.tier == SubscriptionTier.ENTERPRISE

    # Second invocation with same idempotency key but new request ID
    req2 = TenantProvisioningRequest(
        request_id=UUIDv7.generate(),
        organization_id=org.id,
        name="Acme North America Re-run",
        admin_email="admin@acme.com",
        tier=SubscriptionTier.ENTERPRISE,
        tenant_id=TenantId.generate(),  # different tenant_id should be ignored
        idempotency_key=idempotency_key,
    )

    tenant2 = svc.provision_tenant_idempotent(req2)

    # Invariant: Returned instance is identical, no duplicate tenant created in storage
    assert tenant2.id == tenant1.id
    assert tenant2.name == "Acme North America"  # Original name preserved
    all_org_tenants = repo.get_by_organization(org.id)
    assert len(all_org_tenants) == 1
    assert all_org_tenants[0].id == designated_tid
