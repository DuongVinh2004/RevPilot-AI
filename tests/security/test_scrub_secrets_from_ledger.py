"""
RevPilot AI — Security Tests for Scrubbing Secrets from Ledger & Audit Traces
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §5, §7.2
Conforms to INV-AUD-002, INV-SEC-001: 100% of tokens, authorization headers, and keys scrubbed from ledger.
"""

from __future__ import annotations
import sys
import pytest

from revpilot.modules.tool_gateway.action.gateway import (
    ActionCapabilityGateway,
    ActionCapabilityRequest,
    scrub_secrets,
)
from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.results import Success


@pytest.fixture(autouse=True)
def _isolate_gateway_modules():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.tool_gateway"):
            sys.modules.pop(mod, None)


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_clean")


@pytest.fixture
def sample_context(sample_tenant: TenantId) -> TenantContext:
    return TenantContext(
        tenant_id=sample_tenant,
        organization_id=OrganizationId("org_clean"),
    )


def test_scrub_secrets_recursive_dict_and_headers():
    """
    Ensure all sensitive keys and header patterns are replaced by [REDACTED].
    """
    raw_payload = {
        "action": "UPDATE_ORDER",
        "api_key": "AKIA_TEST_SECRET_KEY_999",
        "nested": {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "client_secret": "cs_live_0987654321",
            "user_token": "tok_usr_abc123",
            "normal_data": "order_xyz",
        },
        "credentials_list": [
            {"token_secret": "secret_abc"},
            {"public_info": 123},
        ],
    }

    scrubbed = scrub_secrets(raw_payload)

    assert scrubbed["api_key"] == "[REDACTED]"
    assert scrubbed["nested"]["Authorization"] == "Bearer [REDACTED]"
    assert scrubbed["nested"]["client_secret"] == "[REDACTED]"
    assert scrubbed["nested"]["user_token"] == "[REDACTED]"
    assert scrubbed["nested"]["normal_data"] == "order_xyz"
    assert scrubbed["credentials_list"][0]["token_secret"] == "[REDACTED]"
    assert scrubbed["credentials_list"][1]["public_info"] == 123


def test_scrub_secrets_known_tokens():
    """
    Ensure dynamically known ephemeral secrets appearing inside string values are scrubbed.
    """
    known_tokens = {"eph_secret_value_xyz789"}
    payload = {
        "message": "Dispatching with header token eph_secret_value_xyz789 to external carrier",
    }
    scrubbed = scrub_secrets(payload, known_secrets=known_tokens)
    assert "eph_secret_value_xyz789" not in scrubbed["message"]
    assert "[REDACTED]" in scrubbed["message"]


@pytest.mark.asyncio
async def test_ledger_record_contains_zero_secrets(
    sample_tenant: TenantId,
    sample_context: TenantContext,
):
    """
    INV-AUD-002: Ensure that an end-to-end dispatch leaves 0 raw secrets in the ActionLedgerRecord.
    """
    raw_secret_key = "MY_HIGH_SECURITY_API_KEY_999"
    bearer_token = "Bearer live_access_token_super_secret"

    gateway = ActionCapabilityGateway()
    req = ActionCapabilityRequest(
        intent_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        approval_id=UUIDv7.generate(),
        approval_digest="e" * 64,
        action_type="CARRIER_EXPEDITE",
        idempotency_key="idemp_scrub_test_01",
        target_entities=["shipment_midwest_1"],
        payload={
            "carrier": "express_freight",
            "api_key": raw_secret_key,
            "headers": {"Authorization": bearer_token},
            "order_id": "ORD-9988",
        },
        as_of_time=UtcDateTime.now(),
    )

    res = await gateway.dispatch_action(ctx=sample_context, req=req)
    assert isinstance(res, Success)

    record = res.value
    serialized_record = str(record.model_dump())

    # Verify neither the raw api key nor raw bearer token appear in the ledger record
    assert raw_secret_key not in serialized_record
    assert "live_access_token_super_secret" not in serialized_record
    assert record.execution_status == "SUCCESS"
    assert record.http_status_code == 200
    assert record.request_digest is not None
    assert record.response_digest is not None


@pytest.mark.asyncio
async def test_dry_run_scrubs_secrets_safely(
    sample_tenant: TenantId,
    sample_context: TenantContext,
):
    """
    Dry-run simulation must also scrub all secrets prior to computing digests.
    """
    raw_secret = "SECRET_PASSWORD_123"
    gateway = ActionCapabilityGateway()
    req = ActionCapabilityRequest(
        intent_id=UUIDv7.generate(),
        tenant_id=sample_tenant,
        approval_id=UUIDv7.generate(),
        approval_digest="f" * 64,
        action_type="CARRIER_EXPEDITE",
        idempotency_key="idemp_dryrun_scrub",
        target_entities=["shipment_01"],
        payload={"password": raw_secret, "action": "test"},
        is_dry_run=True,
        as_of_time=UtcDateTime.now(),
    )

    res = await gateway.dispatch_action(ctx=sample_context, req=req)
    assert isinstance(res, Success)

    record = res.value
    serialized = str(record.model_dump())
    assert raw_secret not in serialized
    assert record.http_status_code == 200
