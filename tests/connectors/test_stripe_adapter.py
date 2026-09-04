"""
RevPilot AI — Tests: Stripe Billing Connector Adapter
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §4
Conforms to DEC-001, DEC-006 (2-tier deduplication), and INV-DATA-002.
"""

from __future__ import annotations

import json
import sys
import time
import pytest

from revpilot.modules.canonical.enums import CurrencyCode, GatewayProvider, PaymentStatus, TransactionType
from revpilot.modules.connectors.adapters.stripe import StripeConnectorAdapter
from revpilot.modules.connectors.domain import (
    ConnectorInstanceRecord,
    ConnectorStatus,
    SyncMode,
)
from revpilot.modules.connectors.ingestion.webhook import (
    InvalidWebhookSignatureError,
    generate_webhook_signature,
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
        provider_name="stripe",
        provider_version="v2024-06-20",
        capability_type="billing_sync",
        auth_method="api_key",
        secret_ref=SecretReference(value="vault://secret/stripe_01"),
        granted_scopes=["charges:read", "invoices:read"],
        data_classification="CONFIDENTIAL",
        sync_mode=SyncMode.WEBHOOK_PUSH,
        status=ConnectorStatus.ACTIVE,
        rate_limit_per_minute=2000,
        retry_class="exponential_jitter",
        created_at=now,
        updated_at=now,
    )


def test_stripe_webhook_verification_and_deduplication():
    """Verify Stripe webhook signature check, mapping, and DEC-006 deduplication."""
    tenant_id = TenantId.generate()
    record = _build_test_record(tenant_id)
    webhook_secret = "whsec_stripe_test_secret_123"
    adapter = StripeConnectorAdapter(record, webhook_secret=webhook_secret)

    payload_dict = {
        "id": "evt_test_charge_succeeded_001",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "ch_test_999",
                "amount": 25000,
                "currency": "usd",
                "customer": "cus_corp_01",
                "invoice": "inv_oct_2026",
            }
        },
    }
    raw_body = json.dumps(payload_dict).encode("utf-8")
    ts_str = str(int(time.time()))
    sig = generate_webhook_signature(raw_body, webhook_secret, ts_str)

    # 1. First arrival: processed and mapped
    receipt, payment = adapter.process_webhook_event(
        execution_tenant_id=tenant_id,
        raw_body=raw_body,
        signature_header=f"v1={sig}",
        timestamp_header=ts_str,
    )

    assert not receipt.is_duplicate
    assert payment is not None
    assert payment.id == "pay_ch_test_999"
    assert payment.order_id == "inv_oct_2026"
    assert payment.gateway_provider == GatewayProvider.STRIPE
    assert payment.transaction_type == TransactionType.CAPTURE
    assert payment.payment_status == PaymentStatus.SUCCEEDED
    assert payment.amount_cents == 25000
    assert payment.currency == CurrencyCode.USD

    # 2. Replay arrival (DEC-006): deduplicated fail-safe
    replay_receipt, replay_payment = adapter.process_webhook_event(
        execution_tenant_id=tenant_id,
        raw_body=raw_body,
        signature_header=f"v1={sig}",
        timestamp_header=ts_str,
    )

    assert replay_receipt.is_duplicate
    assert replay_payment is None


def test_stripe_webhook_invalid_signature_rejected():
    """Verify forged webhook payloads are rejected with InvalidWebhookSignatureError."""
    tenant_id = TenantId.generate()
    record = _build_test_record(tenant_id)
    adapter = StripeConnectorAdapter(record, webhook_secret="whsec_real_secret")

    raw_body = b'{"id": "evt_forged", "type": "charge.refunded"}'
    ts_str = str(int(time.time()))
    bad_sig = "a" * 64

    with pytest.raises(InvalidWebhookSignatureError):
        adapter.process_webhook_event(
            execution_tenant_id=tenant_id,
            raw_body=raw_body,
            signature_header=f"v1={bad_sig}",
            timestamp_header=ts_str,
        )


def test_stripe_tenant_isolation_boundary():
    """INV-TEN-001: Webhook from foreign tenant is rejected fail-closed."""
    tenant_a = TenantId.generate()
    tenant_b = TenantId.generate()

    record = _build_test_record(tenant_a)
    adapter = StripeConnectorAdapter(record)

    with pytest.raises(TenancyViolationError) as exc_info:
        adapter.process_webhook_event(
            execution_tenant_id=tenant_b,
            raw_body=b"{}",
            signature_header="v1=none",
            timestamp_header="0",
        )

    assert "Cross-tenant sync violation" in str(exc_info.value)
