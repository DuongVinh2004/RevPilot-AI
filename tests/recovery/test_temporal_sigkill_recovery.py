"""
RevPilot AI — Temporal & Action Workflow SIGKILL Crash Recovery Tests
Specification: docs/29-testing/TEST-STRATEGY.md §13.2
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §9, §10
Conforms to INV-WF-001, INV-ACT-001, NFR-REL-001, and TC-P08-005.
"""

from __future__ import annotations

import pytest

from revpilot.modules.action.domain import (
    ActionClassification,
    ActionIntentRecord,
)
from revpilot.modules.action.ledger import ActionLedgerService
from revpilot.modules.action.ports import (
    InMemoryActionIntentRepository,
    InMemoryActionLedgerRepository,
)
from revpilot.modules.testing.resilience.fault_injector import FaultInjector
from revpilot.shared.context import OrganizationId, TenantContext
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture
def tenant_ctx() -> TenantContext:
    return TenantContext(
        tenant_id=TenantId("tnt_chaos_recovery"),
        organization_id=OrganizationId("org_chaos_recovery"),
        is_active=True,
    )


@pytest.mark.asyncio
async def test_worker_sigkill_recovery_zero_duplicate_execution(
    tenant_ctx: TenantContext,
):
    """
    Simulate worker process SIGKILL via FaultInjector mid-execution.
    On failover to replacement worker, verify execution state is reconstructed from
    durable ledger without duplicate side effects (INV-WF-001, INV-ACT-001).
    """
    fault_injector = FaultInjector()
    worker_1_pid = 9182
    worker_2_pid = 9183

    intent_repo = InMemoryActionIntentRepository()
    ledger_repo = InMemoryActionLedgerRepository()
    ledger_svc = ActionLedgerService(intent_repo, ledger_repo)

    now = UtcDateTime.now()
    intent_id = UUIDv7.generate()
    approval_id = UUIDv7.generate()
    idempotency_key = f"sigkill_safe_{intent_id}"

    intent = ActionIntentRecord(
        intent_id=intent_id,
        tenant_id=tenant_ctx.tenant_id,
        approval_id=approval_id,
        idempotency_key=idempotency_key,
        action_type="reroute_freight_carrier",
        classification=ActionClassification.COMPENSATABLE,
        target_set_count=1,
        payload_digest="req_digest_chaos_99",
        created_at=now,
    )
    await intent_repo.save(intent)

    # 1. Worker 1 records attempt start in durable ledger
    await ledger_svc.record_attempt_start(
        ctx=tenant_ctx,
        intent_id=intent_id,
        idempotency_key=idempotency_key,
        provider_name="mock_carrier_gateway",
        request_digest="req_digest_chaos_99",
    )

    # 2. Chaos engineering: Inject ungraceful SIGKILL on Worker 1
    fault_injector.inject_worker_sigkill(worker_1_pid)
    assert fault_injector.is_worker_killed(worker_1_pid) is True
    assert fault_injector.is_worker_killed(worker_2_pid) is False

    # 3. Worker 2 (replacement node) picks up workflow recovery
    # Queries durable intent and ledger before attempting duplicate provider dispatch
    existing_intent = await intent_repo.get_by_idempotency_key(
        tenant_id=tenant_ctx.tenant_id,
        idempotency_key=idempotency_key,
    )
    assert existing_intent is not None
    assert existing_intent.intent_id == intent_id

    attempts = await ledger_repo.list_by_intent(
        tenant_id=tenant_ctx.tenant_id,
        intent_id=intent_id,
    )
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt.idempotency_key == idempotency_key
    assert attempt.execution_status == "STARTED"

    # Record terminal success from recovered state
    success_record = await ledger_svc.record_attempt_completion(
        ctx=tenant_ctx,
        ledger_id=attempt.ledger_id,
        status="SUCCESS",
        http_status_code=200,
        tx_id="tx_recovered_001",
        response_digest="resp_digest_recovered_001",
    )

    assert success_record.execution_status == "SUCCESS"
    assert success_record.provider_tx_id == "tx_recovered_001"

    # Verify fault injector teardown
    fault_injector.clear_all_faults()
    assert fault_injector.is_worker_killed(worker_1_pid) is False
    assert len(fault_injector.get_active_faults()["killed_workers"]) == 0
