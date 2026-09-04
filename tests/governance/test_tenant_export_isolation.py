"""
RevPilot AI — TC-P07-007: Tenant Export Isolation Test
Specification: docs/18-data-governance/DATA-GOVERNANCE.md §3
Conforms to NFR-TEN-001, INV-PRV-001, INV-SEC-001, and INV-ACT-003.
"""

import hashlib
import json
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.errors import AuthorizationError
from revpilot.modules.tenancy import TenantExportService


def test_tenant_export_isolation_zero_cross_tenant_leakage():
    """
    TC-P07-007: Export package queries strictly within the caller's verified TenantId.
    Inclusion of cross-tenant data equals zero (0.0).
    PII is masked, API keys are redacted, and archive includes verified SHA-256 manifest.
    """
    export_svc = TenantExportService()

    tenant_a = TenantId.generate()
    tenant_b = TenantId.generate()

    # Populate mixed multi-tenant datastore
    customers = [
        {"tenant_id": str(tenant_a), "customer_id": "cust_1", "email": "alice@customer.com", "api_key": "secret_live_123"},
        {"tenant_id": str(tenant_a), "customer_id": "cust_2", "email": "bob@acme.org", "token": "tok_live_456"},
        {"tenant_id": str(tenant_b), "customer_id": "cust_3", "email": "charlie@othercorp.com", "api_key": "secret_other"},
    ]
    tickets = [
        {"tenant_id": str(tenant_a), "ticket_id": "tick_101", "summary": "Delayed cargo"},
        {"tenant_id": str(tenant_b), "ticket_id": "tick_202", "summary": "Billing inquiry"},
    ]

    export_svc.populate_collection("customers", customers)
    export_svc.populate_collection("tickets", tickets)

    # 1. Agent caller is strictly blocked (INV-ACT-003)
    with pytest.raises(AuthorizationError) as exc_info:
        export_svc.export_tenant_data(tenant_a, caller_permissions={"tenant:export"}, is_agent=True)
    assert "agents are strictly prohibited" in exc_info.value.message.lower()

    # 2. Caller without permission is blocked
    with pytest.raises(AuthorizationError):
        export_svc.export_tenant_data(tenant_a, caller_permissions={"tenant:read"})

    # 3. Authorized Human Admin Export Execution
    bundle = export_svc.export_tenant_data(tenant_a, caller_permissions={"tenant:export"})

    assert bundle.tenant_id == tenant_a
    assert bundle.status == "SEALED"
    assert bundle.record_count == 3  # 2 customers + 1 ticket for tenant_a

    # Verify ZERO leakage of Tenant B
    for col_name, recs in bundle.data_payload.items():
        for r in recs:
            assert r["tenant_id"] == str(tenant_a)
            assert str(tenant_b) not in json.dumps(r)

    # Verify PII masking and secret redaction
    exported_custs = bundle.data_payload["customers"]
    alice_rec = next(c for c in exported_custs if c["customer_id"] == "cust_1")
    assert alice_rec["api_key"] == "[REDACTED_SECRET]"
    assert alice_rec["email"] == "a***e@customer.com"

    # Verify Manifest Cryptographic Integrity
    manifest = json.loads(bundle.manifest_json)
    assert manifest["tenant_id"] == str(tenant_a)
    assert manifest["total_records"] == 3
    calculated_hash = hashlib.sha256(bundle.manifest_json.encode("utf-8")).hexdigest()
    assert calculated_hash == bundle.manifest_sha256
