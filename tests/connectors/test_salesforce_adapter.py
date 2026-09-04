"""
RevPilot AI — Tests: Salesforce CRM Connector Adapter
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §3
Conforms to DEC-001, INV-DATA-002, and INV-TEN-001.
"""

from __future__ import annotations

import sys
import pytest

from revpilot.modules.canonical.enums import AccountTier, CustomerSegment
from revpilot.modules.connectors.adapters.salesforce import SalesforceConnectorAdapter
from revpilot.modules.connectors.domain import (
    ConnectorInstanceRecord,
    ConnectorStatus,
    SyncMode,
)
from revpilot.modules.security.secrets.broker import SecretReference
from revpilot.shared.errors import TenancyViolationError
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_connectors_module():
    """Ensure connectors module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.connectors"):
            sys.modules.pop(mod, None)


def _build_test_record(tenant_id: TenantId) -> ConnectorInstanceRecord:
    now = UtcDateTime.now()
    return ConnectorInstanceRecord(
        connector_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        provider_name="salesforce",
        provider_version="v60.0",
        capability_type="crm_sync",
        auth_method="oauth2_client_credentials",
        secret_ref=SecretReference(value="vault://secret/sf_01"),
        granted_scopes=["api", "refresh_token"],
        data_classification="CONFIDENTIAL",
        sync_mode=SyncMode.BATCH_PULL,
        status=ConnectorStatus.ACTIVE,
        rate_limit_per_minute=1000,
        retry_class="standard_backoff",
        created_at=now,
        updated_at=now,
    )


def test_salesforce_account_to_customer_mapping():
    """Verify raw Salesforce Account maps correctly to canonical Customer entity."""
    tenant_id = TenantId.generate()
    record = _build_test_record(tenant_id)
    adapter = SalesforceConnectorAdapter(record)

    raw_account = {
        "Id": "001xx000003DGb2AAG",
        "Name": "Enterprise Alpha Corp",
        "AnnualRevenue": 2_500_000,
    }

    customer = adapter.map_raw_account_to_customer(raw_account, tenant_id)

    assert customer.id == "001xx000003DGb2AAG"
    assert customer.name == "Enterprise Alpha Corp"
    assert customer.account_tier == AccountTier.TIER_1_PLATINUM
    assert customer.segment == CustomerSegment.ENTERPRISE
    assert customer.tenant_id == tenant_id


def test_salesforce_contract_mapping():
    """Verify raw Salesforce Contract maps to canonical Contract entity."""
    tenant_id = TenantId.generate()
    record = _build_test_record(tenant_id)
    adapter = SalesforceConnectorAdapter(record)

    raw_contract = {
        "Id": "800xx0000001",
        "AccountId": "001xx000003DGb2AAG",
        "ContractNumber": "CTR-2026-001",
        "ContractValue": 120_000.0,
    }

    contract = adapter.map_raw_contract(raw_contract, tenant_id)

    assert contract.id == "800xx0000001"
    assert contract.customer_id == "001xx000003DGb2AAG"
    assert "CTR-2026-001" in contract.title
    assert len(contract.document_digest) == 64


def test_salesforce_tenant_isolation_boundary():
    """INV-TEN-001: Sync request from mismatched tenant is rejected fail-closed."""
    tenant_a = TenantId.generate()
    tenant_b = TenantId.generate()

    record = _build_test_record(tenant_a)
    adapter = SalesforceConnectorAdapter(record)

    with pytest.raises(TenancyViolationError) as exc_info:
        adapter.sync_incremental(execution_tenant_id=tenant_b, cursor=None)

    assert "Cross-tenant sync violation" in str(exc_info.value)
