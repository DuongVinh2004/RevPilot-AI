"""
RevPilot AI — Action Completed Outbox Event Contract Tests
Specification: docs/26-api/EVENT-CONTRACTS.md §8
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3
Conforms to INV-AUD-001, INV-AUD-002, and TC-P06-025.
"""

from __future__ import annotations
from decimal import Decimal
import json
import pytest

from revpilot.modules.action.domain import ActionLedgerRecord
from revpilot.modules.action.outcome.domain import ActionEventEnvelope
from revpilot.modules.action.outcome.service import ActionOutcomeService
from revpilot.shared.context import TenantContext
from revpilot.shared.identifiers import OrganizationId, TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture
def tenant_ctx() -> TenantContext:
    return TenantContext(
        tenant_id=TenantId("tnt_event_contract"),
        organization_id=OrganizationId("org_event_contract"),
        is_active=True,
    )


@pytest.mark.asyncio
async def test_action_completed_event_envelope_conformance(tenant_ctx: TenantContext):
    """
    Verify published action.completed.v1 event adheres to canonical schema in EVENT-CONTRACTS.md §8.1 (TC-P06-025).
    """
    service = ActionOutcomeService()
    now = UtcDateTime.now()

    intent_id = UUIDv7.generate()
    approval_id = UUIDv7.generate()
    ledger_id = UUIDv7.generate()

    ledger = ActionLedgerRecord(
        ledger_id=ledger_id,
        tenant_id=tenant_ctx.tenant_id,
        intent_id=intent_id,
        attempt_number=1,
        idempotency_key="act_reship_01h8abcde77777",
        provider_name="mock_carrier_logistics_v1",
        request_digest="digest_request_123",
        response_digest="digest_response_123",
        http_status_code=200,
        provider_tx_id="prov_tx_998822",
        execution_status="SUCCESS",
        started_at=now,
        completed_at=now,
    )

    envelope = await service.publish_completion_event(
        ctx=tenant_ctx,
        ledger=ledger,
        approval_id=approval_id,
        actual_cost_usd=Decimal("45.00"),
    )

    # 1. Structural fields
    assert envelope.event_type == "action.completed.v1"
    assert envelope.producer == "revpilot.modules.tool_gateway"
    assert envelope.aggregate_id == str(ledger_id)
    assert envelope.aggregate_version >= 1
    assert envelope.tenant_id == str(tenant_ctx.tenant_id)
    assert envelope.causation_id == str(intent_id)
    assert envelope.idempotency_key == "act_reship_01h8abcde77777"

    # 2. Payload fields
    payload = envelope.payload
    assert payload["intent_id"] == str(intent_id)
    assert payload["approval_id"] == str(approval_id)
    assert payload["provider_name"] == "mock_carrier_logistics_v1"
    assert payload["provider_tx_id"] == "prov_tx_998822"
    assert payload["execution_status"] == "SUCCESS"
    assert payload["http_status_code"] == 200
    assert payload["actual_cost_usd"] == 45.00


@pytest.mark.asyncio
async def test_action_event_zero_secrets_leakage(tenant_ctx: TenantContext):
    """
    Verify event payload and serialized JSON contain zero credentials or tokens (INV-AUD-002, INV-SEC-001).
    """
    service = ActionOutcomeService()
    now = UtcDateTime.now()

    ledger = ActionLedgerRecord(
        ledger_id=UUIDv7.generate(),
        tenant_id=tenant_ctx.tenant_id,
        intent_id=UUIDv7.generate(),
        attempt_number=1,
        idempotency_key="act_key_safe",
        provider_name="secure_payment_gateway",
        request_digest="sha256_clean",
        http_status_code=200,
        provider_tx_id="tx_clean_12345",
        execution_status="SUCCESS",
        started_at=now,
    )

    envelope = await service.publish_completion_event(
        ctx=tenant_ctx,
        ledger=ledger,
        actual_cost_usd=Decimal("12.50"),
    )

    # Serialize to JSON string
    serialized = envelope.model_dump_json()
    lower_serialized = serialized.lower()

    forbidden_tokens = ["bearer ", "secret_key", "client_secret", "access_token", "private_key"]
    for token in forbidden_tokens:
        assert token not in lower_serialized, f"Forbidden credential substring '{token}' leaked into event payload!"


def test_action_event_envelope_pydantic_validation():
    """
    Verify envelope schema strictly validates input types and rejects missing mandatory keys.
    """
    now = UtcDateTime.now()
    valid_data = {
        "event_id": "evt_test_123",
        "event_type": "action.completed.v1",
        "occurred_at": now,
        "producer": "revpilot.modules.tool_gateway",
        "aggregate_id": "led_123",
        "aggregate_version": 1,
        "tenant_id": "tnt_test",
        "correlation_id": "cor_123",
        "causation_id": "cau_123",
        "idempotency_key": "idemp_123",
        "payload": {"status": "SUCCESS"},
    }

    env = ActionEventEnvelope(**valid_data)
    assert env.event_id == "evt_test_123"

    # Missing mandatory aggregate_id raises ValidationError
    invalid_data = valid_data.copy()
    invalid_data.pop("aggregate_id")
    with pytest.raises(Exception):
        ActionEventEnvelope(**invalid_data)
