"""
RevPilot AI — Tests: Zendesk Support Connector Adapter
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §3
Conforms to DEC-001, INV-DATA-002, and INV-TEN-001..002.
"""

from __future__ import annotations

import sys
import pytest

from revpilot.modules.canonical.enums import TicketPriority, TicketStatus, TicketTopic
from revpilot.modules.connectors.adapters.zendesk import ZendeskConnectorAdapter
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
        provider_name="zendesk",
        provider_version="v2",
        capability_type="support_sync",
        auth_method="oauth2_client_credentials",
        secret_ref=SecretReference(value="vault://secret/zd_01"),
        granted_scopes=["tickets:read", "users:read"],
        data_classification="RESTRICTED_PII",
        sync_mode=SyncMode.BATCH_PULL,
        status=ConnectorStatus.ACTIVE,
        rate_limit_per_minute=700,
        retry_class="standard_backoff",
        created_at=now,
        updated_at=now,
    )


def test_zendesk_ticket_to_canonical_mapping():
    """Verify raw Zendesk ticket maps to canonical SupportTicket entity."""
    tenant_id = TenantId.generate()
    record = _build_test_record(tenant_id)
    adapter = ZendeskConnectorAdapter(record, subdomain="acme-help")

    raw_ticket = {
        "id": 98765,
        "subject": "Enterprise SLA escalation - Latency spike",
        "description": "API latency exceeded 500ms for EMEA cluster",
        "priority": "high",
        "status": "open",
        "requester_id": "cust_zendesk_99",
    }

    ticket = adapter.map_raw_ticket_to_canonical(raw_ticket, tenant_id)

    assert ticket.id == "98765"
    assert ticket.customer_id == "cust_zendesk_99"
    assert ticket.ticket_number == "ZEN-98765"
    assert ticket.priority == TicketPriority.P2_HIGH
    assert ticket.status == TicketStatus.OPEN
    assert ticket.topic == TicketTopic.GENERAL_SUPPORT
    assert ticket.subject == "Enterprise SLA escalation - Latency spike"
    assert "latency exceeded 500ms" in ticket.transcript_text
    assert ticket.tenant_id == tenant_id


def test_zendesk_urgent_and_closed_mapping():
    """Verify urgent priority and solved status mapping."""
    tenant_id = TenantId.generate()
    record = _build_test_record(tenant_id)
    adapter = ZendeskConnectorAdapter(record)

    raw_ticket = {
        "id": 12345,
        "subject": "Critical outage",
        "description": "Production down",
        "priority": "urgent",
        "status": "solved",
        "requester_id": "cust_zendesk_01",
    }

    ticket = adapter.map_raw_ticket_to_canonical(raw_ticket, tenant_id)

    assert ticket.priority == TicketPriority.P1_URGENT
    assert ticket.status == TicketStatus.CLOSED


def test_zendesk_tenant_isolation_boundary():
    """INV-TEN-001: Sync request from mismatched tenant is rejected fail-closed."""
    tenant_a = TenantId.generate()
    tenant_b = TenantId.generate()

    record = _build_test_record(tenant_a)
    adapter = ZendeskConnectorAdapter(record)

    with pytest.raises(TenancyViolationError) as exc_info:
        adapter.sync_incremental(execution_tenant_id=tenant_b, cursor=None)

    assert "Cross-tenant sync violation" in str(exc_info.value)
