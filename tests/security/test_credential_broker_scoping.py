"""
RevPilot AI — Security Tests for Ephemeral Credential Broker Scoping & TTL
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7.2, ADR-0009
Conforms to INV-SEC-001: Ephemeral token TTL capped at 15 minutes, strict tenant/provider/action scoping.
"""

from __future__ import annotations
from datetime import timedelta
import sys
import pytest

from revpilot.modules.tool_gateway.action.credential_broker import (
    CredentialBroker,
    GatewayError,
)
from revpilot.modules.tool_gateway.action.gateway import (
    ActionCapabilityGateway,
    ActionCapabilityRequest,
)
from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.results import Failure


@pytest.fixture(autouse=True)
def _isolate_gateway_modules():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.tool_gateway"):
            sys.modules.pop(mod, None)


@pytest.fixture
def broker() -> CredentialBroker:
    return CredentialBroker()


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha_logistics")


@pytest.fixture
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta_retail")


@pytest.mark.asyncio
async def test_credential_ttl_capped_at_15_minutes(broker: CredentialBroker, tenant_alpha: TenantId):
    """
    ADR-0009: Ephemeral tokens must not exceed 15-minute (900 seconds) lifetime.
    """
    # Requesting valid <= 15 minutes succeeds
    cred = await broker.issue_ephemeral_token(
        tenant_id=tenant_alpha,
        provider="mock_logistics_v1",
        action_type="CARRIER_EXPEDITE",
        ttl_seconds=900,
    )
    now = UtcDateTime.now()
    assert cred.token_id.startswith("tok_eph_")
    assert cred.expires_at > now
    assert (cred.expires_at.value - now.value).total_seconds() <= 905

    # Requesting > 15 minutes (901s) raises ERR_INVALID_TOKEN_TTL immediately
    with pytest.raises(GatewayError) as exc_info:
        await broker.issue_ephemeral_token(
            tenant_id=tenant_alpha,
            provider="mock_logistics_v1",
            action_type="CARRIER_EXPEDITE",
            ttl_seconds=901,
        )
    assert exc_info.value.code == "ERR_INVALID_TOKEN_TTL"


@pytest.mark.asyncio
async def test_credential_cross_tenant_scope_rejection(
    broker: CredentialBroker,
    tenant_alpha: TenantId,
    tenant_beta: TenantId,
):
    """
    Tokens issued for tenant Alpha must fail closed if presented for tenant Beta.
    """
    cred = await broker.issue_ephemeral_token(
        tenant_id=tenant_alpha,
        provider="mock_carrier_v1",
        action_type="CARRIER_EXPEDITE",
        ttl_seconds=300,
    )

    # Validating against tenant_beta must fail
    res = broker.validate_token(
        credential=cred,
        tenant_id=tenant_beta,
        provider="mock_carrier_v1",
        action_type="CARRIER_EXPEDITE",
    )
    assert isinstance(res, Failure)
    assert res.error.code == "ERR_CREDENTIAL_SCOPE_MISMATCH"
    assert "tenant" in res.error.message.lower()


@pytest.mark.asyncio
async def test_credential_provider_scope_rejection(broker: CredentialBroker, tenant_alpha: TenantId):
    """
    Tokens issued for provider A cannot be used for provider B.
    """
    cred = await broker.issue_ephemeral_token(
        tenant_id=tenant_alpha,
        provider="mock_carrier_v1",
        action_type="CARRIER_EXPEDITE",
        ttl_seconds=300,
    )

    res = broker.validate_token(
        credential=cred,
        tenant_id=tenant_alpha,
        provider="mock_crm_v1",
        action_type="CARRIER_EXPEDITE",
    )
    assert isinstance(res, Failure)
    assert res.error.code == "ERR_CREDENTIAL_SCOPE_MISMATCH"
    assert "provider" in res.error.message.lower()


@pytest.mark.asyncio
async def test_credential_action_scope_rejection(broker: CredentialBroker, tenant_alpha: TenantId):
    """
    Tokens issued for action type A cannot be used for action type B.
    """
    cred = await broker.issue_ephemeral_token(
        tenant_id=tenant_alpha,
        provider="mock_carrier_v1",
        action_type="CARRIER_EXPEDITE",
        ttl_seconds=300,
    )

    res = broker.validate_token(
        credential=cred,
        tenant_id=tenant_alpha,
        provider="mock_carrier_v1",
        action_type="BILLING_REFUND",
    )
    assert isinstance(res, Failure)
    assert res.error.code == "ERR_CREDENTIAL_SCOPE_MISMATCH"
    assert "action" in res.error.message.lower()


@pytest.mark.asyncio
async def test_credential_expired_token_rejection(broker: CredentialBroker, tenant_alpha: TenantId):
    """
    Tokens with expiry in the past must fail closed with ERR_CREDENTIAL_EXPIRED.
    """
    now = UtcDateTime.now()
    cred = await broker.issue_ephemeral_token(
        tenant_id=tenant_alpha,
        provider="mock_carrier_v1",
        action_type="CARRIER_EXPEDITE",
        ttl_seconds=60,
    )

    # Validate with as_of_time 65 seconds in the future
    future_time = UtcDateTime(now.value + timedelta(seconds=65))
    res = broker.validate_token(
        credential=cred,
        tenant_id=tenant_alpha,
        provider="mock_carrier_v1",
        action_type="CARRIER_EXPEDITE",
        as_of_time=future_time,
    )
    assert isinstance(res, Failure)
    assert res.error.code == "ERR_CREDENTIAL_EXPIRED"


@pytest.mark.asyncio
async def test_gateway_dispatch_enforces_tenant_context_match(
    tenant_alpha: TenantId,
    tenant_beta: TenantId,
):
    """
    Gateway rejects requests where TenantContext does not match request.tenant_id.
    """
    gateway = ActionCapabilityGateway()
    ctx = TenantContext(
        tenant_id=tenant_alpha,
        organization_id=OrganizationId("org_sample"),
    )

    req = ActionCapabilityRequest(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant_beta,  # Mismatched!
        approval_id=UUIDv7.generate(),
        approval_digest="a" * 64,
        action_type="CARRIER_EXPEDITE",
        idempotency_key="idemp_test_mismatch",
        target_entities=["shipment_01"],
        payload={"notes": "test"},
        as_of_time=UtcDateTime.now(),
    )

    res = await gateway.dispatch_action(ctx=ctx, req=req)
    assert isinstance(res, Failure)
    assert res.error.code == "ERR_TENANT_MISMATCH"
