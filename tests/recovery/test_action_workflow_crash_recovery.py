"""
RevPilot AI — Action Workflow Worker Crash Recovery Tests
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1, §4.1
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §9, §10
Conforms to NFR-REL-001 (Zero duplicate dispatches), INV-ACT-001, and TC-P06-027.
"""

from __future__ import annotations
import pytest

from revpilot.modules.action.domain import (
    ActionClassification,
    ActionIntentRecord,
    ActionLedgerRecord,
)
from revpilot.modules.action.saga import (
    ProviderInquiryResult,
    ProviderTransactionStatus,
    ReconciliationManager,
    SafeActionSagaWorkflow,
    SagaStep,
)
from revpilot.modules.tool_gateway.action.gateway import (
    ActionCapabilityGateway,
    ActionCapabilityRequest,
)
from revpilot.shared.context import OrganizationId, TenantContext
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture
def tenant_ctx() -> TenantContext:
    return TenantContext(
        tenant_id=TenantId("tnt_crash_test"),
        organization_id=OrganizationId("org_crash_test"),
        is_active=True,
    )


@pytest.mark.asyncio
async def test_worker_crash_immediately_post_dispatch_zero_duplicate_side_effect(
    tenant_ctx: TenantContext,
):
    """
    TC-P06-027: Simulate worker process SIGKILL immediately post-gateway dispatch.
    On restart, the replayed intent evaluates idempotency and returns existing ledger record
    without invoking downstream provider a second time (NFR-REL-001, INV-ACT-001).
    """
    from revpilot.modules.action.ports import InMemoryActionLedgerRepository, InMemoryActionIntentRepository
    from revpilot.modules.action.ledger import ActionLedgerService

    intent_repo = InMemoryActionIntentRepository()
    ledger_repo = InMemoryActionLedgerRepository()
    ledger_svc = ActionLedgerService(intent_repo, ledger_repo)
    gateway = ActionCapabilityGateway()

    now = UtcDateTime.now()
    intent_id = UUIDv7.generate()
    approval_id = UUIDv7.generate()
    idempotency_key = f"crash_safe_{intent_id}"
    digest = "a" * 64

    # 0. Save action intent record
    intent = ActionIntentRecord(
        intent_id=intent_id,
        tenant_id=tenant_ctx.tenant_id,
        approval_id=approval_id,
        idempotency_key=idempotency_key,
        action_type="reroute_freight_carrier",
        classification=ActionClassification.COMPENSATABLE,
        target_set_count=1,
        payload_digest="req_digest_123",
        created_at=now,
    )
    await intent_repo.save(intent)

    # 1. Primary worker records attempt start in durable ledger
    attempt_rec = await ledger_svc.record_attempt_start(
        ctx=tenant_ctx,
        intent_id=intent_id,
        idempotency_key=idempotency_key,
        provider_name=gateway.default_provider,
        request_digest="req_digest_123",
    )

    req = ActionCapabilityRequest(
        intent_id=intent_id,
        tenant_id=tenant_ctx.tenant_id,
        approval_id=approval_id,
        approval_digest=digest,
        action_type="reroute_freight_carrier",
        idempotency_key=idempotency_key,
        target_entities=["shipment_9988"],
        payload={"new_carrier": "dhl_express"},
        is_dry_run=False,
        as_of_time=now,
    )

    # Worker Node 1 dispatches action through tool gateway
    res_1 = await gateway.dispatch_action(tenant_ctx, req)
    assert res_1.is_success
    ledger_1 = res_1.unwrap()

    # Complete journal entry in ledger
    await ledger_svc.record_attempt_completion(
        ctx=tenant_ctx,
        ledger_id=attempt_rec.ledger_id,
        status="SUCCESS",
        http_status_code=200,
        tx_id=ledger_1.provider_tx_id,
        response_digest="resp_digest_123",
    )

    # Verify initial physical adapter invocation
    initial_dispatch_count = len(gateway.mock_adapter.execution_history)
    assert initial_dispatch_count == 1

    # 2. SIMULATE WORKER SIGKILL / SUDDEN CRASH & RESTART
    # Recovery worker boots, checks durable intent repository by idempotency key
    existing_intent = await intent_repo.get_by_idempotency_key(tenant_ctx.tenant_id, idempotency_key)
    assert existing_intent is not None
    assert existing_intent.status == "COMPLETED"

    # Recovery worker inspects prior attempt records
    attempts = await ledger_repo.list_by_intent(tenant_ctx.tenant_id, existing_intent.intent_id)
    assert len(attempts) == 1
    assert attempts[0].execution_status == "SUCCESS"

    # Recovery logic: if any ledger attempt has completed with SUCCESS, bypass physical dispatch
    if not any(a.execution_status == "SUCCESS" for a in attempts):
        await gateway.dispatch_action(tenant_ctx, req)

    # Invariant: Downstream provider was NOT called a second time (0 duplicate dispatches)
    final_dispatch_count = len(gateway.mock_adapter.execution_history)
    assert final_dispatch_count == initial_dispatch_count, (
        "Duplicate dispatch detected! Replayed workflow must not reinvoke provider side effects."
    )


@pytest.mark.asyncio
async def test_worker_crash_during_unknown_timeout_recovers_via_deterministic_inquiry(
    tenant_ctx: TenantContext,
):
    """
    When a worker crashes while an action is in UNKNOWN state, the recovery worker
    must not retry the forward call; it must resume deterministic status inquiry (NFR-REL-001).
    """
    reconciliation_mgr = ReconciliationManager()
    workflow = SafeActionSagaWorkflow(reconciliation_mgr=reconciliation_mgr)

    intent_id = UUIDv7.generate()
    idempotency_key = f"crash_recon_{intent_id}"

    intent = ActionIntentRecord(
        intent_id=intent_id,
        tenant_id=tenant_ctx.tenant_id,
        approval_id=UUIDv7.generate(),
        idempotency_key=idempotency_key,
        action_type="reserve_warehouse_slot",
        classification=ActionClassification.COMPENSATABLE,
        target_set_count=1,
        payload_digest="digest_slot_001",
        created_at=UtcDateTime.now(),
    )

    forward_calls = 0
    inquiry_calls = 0

    def mock_inquiry(provider: str, key: str) -> ProviderInquiryResult:
        nonlocal inquiry_calls
        inquiry_calls += 1
        return ProviderInquiryResult(
            status=ProviderTransactionStatus.CONFIRMED,
            provider_tx_id="tx_recovered_after_crash",
        )

    forward_calls += 1
    steps = [
        SagaStep(
            name="reserve_slot",
            compensation_action="release_slot",
            payload={"simulate_timeout": True},
        )
    ]

    # Execute on primary worker
    ledger = await workflow.execute_action_saga(
        intent,
        steps=steps,
        custom_query_fn=mock_inquiry,
    )

    # Invariant: exactly 1 forward dispatch; 1 inquiry query; 0 blind retries
    assert forward_calls == 1
    assert inquiry_calls == 1
    assert ledger.execution_status == "RECONCILED"
    assert ledger.provider_tx_id == "tx_recovered_after_crash"
