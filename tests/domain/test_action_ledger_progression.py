"""
RevPilot AI — Domain Tests for Action Ledger State Machine Progression
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.3, §4
Conforms to NFR-REL-001, AC-008: Ledger records attempt numbers, request/response digests,
and manages transitions through STARTED -> SUCCESS / PROVIDER_ERROR / TIMEOUT_UNKNOWN.
"""

from __future__ import annotations
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7, OrganizationId
from revpilot.shared.context import TenantContext


@pytest.fixture(autouse=True)
def _isolate_action_module():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.action") or mod.startswith("revpilot.modules.approval"):
            sys.modules.pop(mod, None)


@pytest.fixture
def action_module():
    import revpilot.modules.action as mod
    return mod


@pytest.fixture
def approval_module():
    import revpilot.modules.approval as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_corp")


@pytest.fixture
def sample_context(sample_tenant) -> TenantContext:
    return TenantContext(
        tenant_id=sample_tenant,
        organization_id=OrganizationId("org_sample"),
    )


@pytest.mark.asyncio
async def test_action_ledger_attempt_progression(
    action_module, approval_module, sample_tenant, sample_context
):
    """
    Action ledger records sequential attempt numbers, SHA-256 digests,
    and updates parent intent state to COMPLETED on SUCCESS.
    """
    intent_repo = action_module.InMemoryActionIntentRepository()
    ledger_repo = action_module.InMemoryActionLedgerRepository()
    service = action_module.ActionLedgerService(intent_repo, ledger_repo)

    approval_repo = approval_module.InMemoryApprovalRepository()
    approval_svc = approval_module.ApprovalService(approval_repo)

    app_rec = await approval_svc.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_DISPATCH",
        target_customer_id="cust_001",
        target_entity_refs=["ship_01"],
        action_payload={"priority": "HIGH"},
        estimated_cost_usd=Decimal("50.00"),
    )
    approved_rec = await approval_svc.grant_approval(
        tenant_id=sample_tenant,
        approval_id=app_rec.approval_id,
        approver_principal_id="usr_manager",
        approver_tier=1,
        expected_digest=app_rec.payload_digest,
        is_human=True,
    )

    intent = await service.create_intent(
        ctx=sample_context,
        approval=approved_rec,
        idempotency_key="idemp_dispatch_progression_01",
        classification=action_module.ActionClassification.REVERSIBLE,
    )
    assert intent.status == "INITIALIZED"

    # 1. Record attempt 1 start
    attempt1 = await service.record_attempt_start(
        ctx=sample_context,
        intent_id=intent.intent_id,
        idempotency_key="idemp_attempt_1",
        provider_name="mock_logistics_api",
        request_digest="sha256_req_digest_1",
    )
    assert attempt1.attempt_number == 1
    assert attempt1.execution_status == "STARTED"

    # Intent moves to DISPATCHED
    reloaded_intent = await intent_repo.get(sample_tenant, intent.intent_id)
    assert reloaded_intent.status == "DISPATCHED"

    # 2. Complete attempt 1 with success
    completed_attempt1 = await service.record_attempt_completion(
        ctx=sample_context,
        ledger_id=attempt1.ledger_id,
        status="SUCCESS",
        response_digest="sha256_resp_digest_1",
        http_status_code=200,
        tx_id="tx_provider_999",
    )
    assert completed_attempt1.execution_status == "SUCCESS"
    assert completed_attempt1.http_status_code == 200
    assert completed_attempt1.provider_tx_id == "tx_provider_999"

    # Intent moves to COMPLETED
    final_intent = await intent_repo.get(sample_tenant, intent.intent_id)
    assert final_intent.status == "COMPLETED"


@pytest.mark.asyncio
async def test_action_ledger_timeout_unknown_progression(
    action_module, approval_module, sample_tenant, sample_context
):
    """
    When an attempt suffers TIMEOUT_UNKNOWN, intent transitions to RECONCILING
    to block blind automated retries (NFR-REL-001).
    """
    intent_repo = action_module.InMemoryActionIntentRepository()
    ledger_repo = action_module.InMemoryActionLedgerRepository()
    service = action_module.ActionLedgerService(intent_repo, ledger_repo)

    approval_repo = approval_module.InMemoryApprovalRepository()
    approval_svc = approval_module.ApprovalService(approval_repo)

    app_rec = await approval_svc.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_DISPATCH",
        target_customer_id="cust_001",
        target_entity_refs=["ship_01"],
        action_payload={"priority": "HIGH"},
        estimated_cost_usd=Decimal("50.00"),
    )
    approved_rec = await approval_svc.grant_approval(
        tenant_id=sample_tenant,
        approval_id=app_rec.approval_id,
        approver_principal_id="usr_manager",
        approver_tier=1,
        expected_digest=app_rec.payload_digest,
        is_human=True,
    )

    intent = await service.create_intent(
        ctx=sample_context,
        approval=approved_rec,
        idempotency_key="idemp_timeout_progression_02",
        classification=action_module.ActionClassification.REVERSIBLE,
    )

    attempt = await service.record_attempt_start(
        ctx=sample_context,
        intent_id=intent.intent_id,
        idempotency_key="idemp_attempt_timeout",
        provider_name="mock_logistics_api",
        request_digest="sha256_req_digest",
    )

    # Provider timed out
    await service.record_attempt_completion(
        ctx=sample_context,
        ledger_id=attempt.ledger_id,
        status="TIMEOUT_UNKNOWN",
        http_status_code=504,
        error_code="ERR_GATEWAY_TIMEOUT",
    )

    # Intent enters RECONCILING status (NFR-REL-001)
    reconciling_intent = await intent_repo.get(sample_tenant, intent.intent_id)
    assert reconciling_intent.status == "RECONCILING"
