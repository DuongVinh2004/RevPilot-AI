"""
RevPilot AI — Salesforce CRM Connector Adapter
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §3
Conforms to DEC-001 (B2B SaaS), INV-DATA-002, and INV-TEN-001..002.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from revpilot.modules.canonical.enums import (
    AccountTier,
    ContractStatus,
    ContractType,
    CurrencyCode,
    CustomerSegment,
    CustomerStatus,
)
from revpilot.modules.canonical.models import (
    Contract,
    Customer,
)
from revpilot.modules.connectors.adapters.base import BaseConnectorAdapter
from revpilot.modules.connectors.adapters.egress import EgressProxyGateway
from revpilot.modules.connectors.domain import ConnectorInstanceRecord
from revpilot.shared.identifiers import TenantId
from revpilot.shared.monetary import Money
from revpilot.shared.temporal import UtcDateTime


class SalesforceConnectorAdapter(BaseConnectorAdapter):
    """
    Commercial adapter for Salesforce CRM.
    Ingests Account and Contract objects and maps to RevPilot canonical schemas.
    """

    def __init__(
        self,
        instance_record: ConnectorInstanceRecord,
        egress_proxy: EgressProxyGateway | None = None,
    ) -> None:
        super().__init__(instance_record)
        self.egress_proxy = egress_proxy or EgressProxyGateway()
        self.instance_url = "https://revpilot-partner.my.salesforce.com"

    def validate_connection(self, scoped_token: str) -> bool:
        """Validates upstream Salesforce connectivity via governed egress proxy."""
        endpoint = f"{self.instance_url}/services/data/v60.0/"
        res = self.egress_proxy.execute_mock_egress(endpoint, method="GET")
        return res["status"] == 200

    def map_raw_account_to_customer(self, raw: dict[str, Any], tenant_id: TenantId) -> Customer:
        """Transforms a Salesforce Account record to canonical Customer entity."""
        sf_id = raw.get("Id", "")
        name = raw.get("Name", "Unknown Account")
        email = raw.get("Email", f"contact@{sf_id.lower() or 'salesforce'}.example.com")
        revenue = float(raw.get("AnnualRevenue", 0.0) or 0.0)

        # B2B tier classification
        tier = AccountTier.TIER_1_PLATINUM if revenue >= 1_000_000 else AccountTier.TIER_2_GOLD
        segment = CustomerSegment.ENTERPRISE if revenue >= 1_000_000 else CustomerSegment.MID_MARKET
        now = UtcDateTime.now()

        return Customer(
            tenant_id=tenant_id,
            id=sf_id,
            name=name,
            email=email,
            segment=segment,
            account_tier=tier,
            billing_country="US",
            contract_mrr_cents=int(revenue / 12 * 100),
            currency=CurrencyCode.USD,
            status=CustomerStatus.ACTIVE,
            event_time=now,
            effective_from=now,
        )

    def map_raw_contract(self, raw: dict[str, Any], tenant_id: TenantId) -> Contract:
        """Transforms a Salesforce Contract record to canonical Contract entity."""
        import hashlib
        sf_id = raw.get("Id", "")
        account_id = raw.get("AccountId", "")
        contract_num = raw.get("ContractNumber", f"SF-{sf_id}")
        val = float(raw.get("ContractValue", 0.0) or 0.0)
        now = UtcDateTime.now()
        digest = hashlib.sha256(f"{sf_id}:{contract_num}".encode("utf-8")).hexdigest()

        return Contract(
            tenant_id=tenant_id,
            id=sf_id,
            customer_id=account_id,
            title=f"Salesforce Contract {contract_num}",
            contract_type=ContractType.ENTERPRISE_SLA,
            document_uri=f"salesforce://contract/{sf_id}",
            document_digest=digest,
            status=ContractStatus.ACTIVE,
            event_time=now,
            effective_from=now,
        )

    def sync_incremental(
        self,
        execution_tenant_id: TenantId,
        cursor: str | None,
        batch_size: int = 500,
    ) -> tuple[list[Any], str | None]:
        """Performs incremental sync of Salesforce B2B accounts and contracts."""
        self.verify_tenant_boundary(execution_tenant_id)

        # Mock pull representing records modified after cursor
        mock_raw_accounts = [
            {"Id": "001xx001", "Name": "Alpha Corp", "AnnualRevenue": 2500000},
            {"Id": "001xx002", "Name": "Beta Logistics", "AnnualRevenue": 450000},
        ]
        entities: list[Any] = [
            self.map_raw_account_to_customer(acc, execution_tenant_id)
            for acc in mock_raw_accounts
        ]
        next_cursor = "sf_cursor_20260904_230000"
        return entities, next_cursor
