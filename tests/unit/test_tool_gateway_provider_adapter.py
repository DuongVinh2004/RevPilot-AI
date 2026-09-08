"""
RevPilot AI — Tool Gateway Provider Adapter Port & Gate 2 Verification Unit Tests
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §4, §7.1
Conforms to INV-ACT-001, INV-ACT-002, AC-008, AC-009, ADR-0009.
"""

from __future__ import annotations
from typing import Any
import pytest

from revpilot.modules.approval.digest import (
    ApprovalArtifact,
    compute_approval_digest,
)
from revpilot.modules.tool_gateway.action.credential_broker import (
    EphemeralCredential,
    GatewayError,
)
from revpilot.modules.tool_gateway.action.gateway import (
    ActionCapabilityGateway,
    ActionCapabilityRequest,
)
from revpilot.modules.tool_gateway.action.mock_adapter import MockProviderAdapter
from revpilot.modules.tool_gateway.ports.provider_adapter import (
    ProviderAdapterPort,
    ProviderResponse,
)
from revpilot.shared.context import OrganizationId, TenantContext
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.results import Failure, Result, Success
from revpilot.shared.temporal import UtcDateTime


class DummyExternalProviderAdapter:
    """Production external provider adapter implementing ProviderAdapterPort."""

    def __init__(self, tx_id: str = "tx_ext_12345", status_code: int = 200) -> None:
        self.tx_id = tx_id
        self.status_code = status_code
        self.calls: list[dict[str, Any]] = []

    def execute(
        self,
        intent_id: str,
        action_type: str,
        target_entities: list[str],
        payload: dict[str, Any],
        credential: EphemeralCredential,
    ) -> Result[ProviderResponse, GatewayError]:
        self.calls.append({
            "intent_id": intent_id,
            "action_type": action_type,
            "target_entities": target_entities,
            "token_id": credential.token_id,
        })
        return Success(
            ProviderResponse(
                http_status_code=self.status_code,
                provider_tx_id=self.tx_id,
                response_payload={"status": "DELIVERED", "external_ref": self.tx_id},
                duration_ms=42,
            )
        )


def _build_test_context() -> tuple[TenantContext, TenantId]:
    tenant_id = TenantId("tnt_adapter_test")
    ctx = TenantContext(
        tenant_id=tenant_id,
        organization_id=OrganizationId("org_adapter_test"),
        is_active=True,
    )
    return ctx, tenant_id


def _build_sample_artifact(tenant_id: str) -> ApprovalArtifact:
    return ApprovalArtifact(
        tenant_id=tenant_id,
        action_type="reroute_carrier",
        target_entities=["order_001"],
        payload={"carrier": "dhl", "priority": "overnight"},
        policy_version="1.0.0",
        required_tier="TIER_1",
        expires_at="2026-12-31T23:59:59Z",
        created_by="usr_lead_analyst",
    )


@pytest.mark.asyncio
async def test_01_gateway_accepts_provider_adapter_port():
    """Verify ActionCapabilityGateway constructor accepts valid ProviderAdapterPort."""
    adapter = DummyExternalProviderAdapter()
    assert isinstance(adapter, ProviderAdapterPort)

    gateway = ActionCapabilityGateway(provider_adapter=adapter, environment="test")
    assert gateway.provider_adapter is adapter
    assert isinstance(gateway.provider_adapter, ProviderAdapterPort)

    # Rejection of invalid adapter not satisfying protocol
    class InvalidAdapter:
        pass

    with pytest.raises(GatewayError) as exc_info:
        ActionCapabilityGateway(provider_adapter=InvalidAdapter(), environment="test")  # type: ignore
    assert exc_info.value.code == "ERR_INVALID_PROVIDER_ADAPTER"


@pytest.mark.asyncio
async def test_02_mock_provider_adapter_forbidden_in_production(monkeypatch):
    """Verify MockProviderAdapter in production environment raises ERR_MOCK_PROVIDER_FORBIDDEN."""
    # 1. Explicit environment="production" with no adapter (defaults to mock)
    with pytest.raises(GatewayError) as exc1:
        ActionCapabilityGateway(environment="production")
    assert exc1.value.code == "ERR_MOCK_PROVIDER_FORBIDDEN"

    # 2. Explicit environment="production" with MockProviderAdapter instance
    with pytest.raises(GatewayError) as exc2:
        ActionCapabilityGateway(
            provider_adapter=MockProviderAdapter(),
            environment="production",
        )
    assert exc2.value.code == "ERR_MOCK_PROVIDER_FORBIDDEN"

    # 3. Via ENVIRONMENT env var
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(GatewayError) as exc3:
        ActionCapabilityGateway()
    assert exc3.value.code == "ERR_MOCK_PROVIDER_FORBIDDEN"

    # 4. Invocation check: if mock adapter somehow present and environment is production
    gateway_test = ActionCapabilityGateway(environment="test")
    gateway_test.environment = "production"
    ctx, tenant_id = _build_test_context()
    req = ActionCapabilityRequest(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        approval_id=UUIDv7.generate(),
        approval_digest="0" * 64,
        action_type="reroute_carrier",
        idempotency_key="idemp_prod_block",
        target_entities=["order_001"],
        payload={"carrier": "test"},
        as_of_time=UtcDateTime.now(),
    )
    res = await gateway_test.dispatch_action(ctx, req)
    assert isinstance(res, Failure)
    assert res.error.code == "ERR_MOCK_PROVIDER_FORBIDDEN"


@pytest.mark.asyncio
async def test_03_real_provider_adapter_succeeds_in_production():
    """Verify real ProviderAdapterPort implementation succeeds in production environment."""
    adapter = DummyExternalProviderAdapter(tx_id="tx_live_prod_999")
    gateway = ActionCapabilityGateway(provider_adapter=adapter, environment="production")
    ctx, tenant_id = _build_test_context()

    req = ActionCapabilityRequest(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        approval_id=UUIDv7.generate(),
        approval_digest="0" * 64,
        action_type="reroute_carrier",
        idempotency_key="idemp_prod_real",
        target_entities=["order_001"],
        payload={"carrier": "dhl"},
        as_of_time=UtcDateTime.now(),
    )
    res = await gateway.dispatch_action(ctx, req)
    assert res.is_success
    record = res.unwrap()
    assert record.execution_status == "SUCCESS"
    assert record.provider_tx_id == "tx_live_prod_999"
    assert len(adapter.calls) == 1


@pytest.mark.asyncio
async def test_04_mock_provider_adapter_operates_in_test_environment():
    """Verify MockProviderAdapter operates normally when ENVIRONMENT=test."""
    gateway = ActionCapabilityGateway(environment="test")
    assert isinstance(gateway.provider_adapter, MockProviderAdapter)

    ctx, tenant_id = _build_test_context()
    req = ActionCapabilityRequest(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        approval_id=UUIDv7.generate(),
        approval_digest="1" * 64,
        action_type="reroute_carrier",
        idempotency_key="idemp_test_mock",
        target_entities=["order_001"],
        payload={"carrier": "mock"},
        as_of_time=UtcDateTime.now(),
    )
    res = await gateway.dispatch_action(ctx, req)
    assert res.is_success
    record = res.unwrap()
    assert record.execution_status == "SUCCESS"
    assert record.provider_name == "mock_logistics_v1"


@pytest.mark.asyncio
async def test_05_gate_2_rejects_invalid_approval_digest():
    """Verify Gate 2 rejects invalid approval digest via verify_approval_digest."""
    gateway = ActionCapabilityGateway(environment="test")
    ctx, tenant_id = _build_test_context()
    artifact = _build_sample_artifact(str(tenant_id))

    # Mismatched/tampered digest
    tampered_digest = "f" * 64
    req = ActionCapabilityRequest(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        approval_id=UUIDv7.generate(),
        approval_digest=tampered_digest,
        action_type="reroute_carrier",
        idempotency_key="idemp_tampered_digest",
        target_entities=["order_001"],
        payload={"carrier": "dhl", "priority": "overnight"},
        as_of_time=UtcDateTime.now(),
        approval_artifact=artifact,
    )
    res = await gateway.dispatch_action(ctx, req)
    assert isinstance(res, Failure)
    assert res.error.code == "ERR_APPROVAL_DIGEST_MISMATCH"

    # Also test invalid length (< 64)
    with pytest.raises(Exception):
        ActionCapabilityRequest(
            intent_id=UUIDv7.generate(),
            tenant_id=tenant_id,
            approval_id=UUIDv7.generate(),
            approval_digest="too_short",
            action_type="reroute_carrier",
            idempotency_key="idemp_short",
            as_of_time=UtcDateTime.now(),
        )


@pytest.mark.asyncio
async def test_06_gate_2_accepts_valid_approval_digest():
    """Verify Gate 2 accepts valid approval digest via verify_approval_digest."""
    gateway = ActionCapabilityGateway(environment="test")
    ctx, tenant_id = _build_test_context()
    artifact = _build_sample_artifact(str(tenant_id))
    canonical_digest = compute_approval_digest(artifact)

    req = ActionCapabilityRequest(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant_id,
        approval_id=UUIDv7.generate(),
        approval_digest=canonical_digest,
        action_type="reroute_carrier",
        idempotency_key="idemp_valid_digest",
        target_entities=["order_001"],
        payload={"carrier": "dhl", "priority": "overnight"},
        as_of_time=UtcDateTime.now(),
        approval_artifact=artifact,
    )
    res = await gateway.dispatch_action(ctx, req)
    assert res.is_success
    record = res.unwrap()
    assert record.execution_status == "SUCCESS"
