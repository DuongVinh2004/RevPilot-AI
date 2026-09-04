"""
RevPilot AI — Saga Backward Compensation Workflow Tests
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §4.2
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §10
Conforms to ADR-0002, INV-ACT-001, and TC-P06-021.
"""

from __future__ import annotations
import pytest

from revpilot.modules.action.domain import (
    ActionClassification,
    ActionIntentRecord,
)
from revpilot.modules.action.saga import (
    CompensationStatus,
    SAGA_REGISTRY,
    SafeActionSagaWorkflow,
    SagaStep,
)
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def clean_registry():
    SAGA_REGISTRY.clear()
    yield
    SAGA_REGISTRY.clear()


@pytest.mark.asyncio
async def test_all_steps_succeed_no_compensation_invoked():
    """When all compound steps complete cleanly, zero compensation records are created."""
    workflow = SafeActionSagaWorkflow()
    tenant = TenantId("tnt_compound_01")
    intent = ActionIntentRecord(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant,
        approval_id=UUIDv7.generate(),
        idempotency_key="idemp_compound_success",
        action_type="fulfill_expedited_order",
        classification=ActionClassification.COMPENSATABLE,
        target_set_count=1,
        payload_digest="digest_all_pass",
        created_at=UtcDateTime.now(),
    )

    steps = [
        SagaStep(name="reserve_inventory", compensation_action="release_inventory", payload={"sku": "item_1"}),
        SagaStep(name="charge_surcharge", compensation_action="refund_surcharge", payload={"amount_usd": 15.0}),
        SagaStep(name="book_courier", compensation_action="cancel_courier", payload={"courier": "dhl"}),
    ]

    ledger = await workflow.execute_action_saga(intent, steps=steps)
    assert ledger.execution_status == "SUCCESS"
    assert len(SAGA_REGISTRY.compensation_records) == 0
    assert len(workflow.compensation_history) == 0


@pytest.mark.asyncio
async def test_step_failure_triggers_compensation_in_strict_reverse_order():
    """
    When step K fails, steps K-1 down to 1 must be compensated in strict reverse order (TC-P06-021).
    Step 1: reserve_inventory
    Step 2: charge_surcharge
    Step 3: book_courier (FAILS)
    Expected compensation sequence: Step 2 (refund_surcharge), then Step 1 (release_inventory).
    """
    workflow = SafeActionSagaWorkflow()
    tenant = TenantId("tnt_compound_02")
    intent = ActionIntentRecord(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant,
        approval_id=UUIDv7.generate(),
        idempotency_key="idemp_compound_rollback",
        action_type="fulfill_expedited_order",
        classification=ActionClassification.COMPENSATABLE,
        target_set_count=1,
        payload_digest="digest_fail_at_step_3",
        created_at=UtcDateTime.now(),
    )

    steps = [
        SagaStep(name="reserve_inventory", compensation_action="release_inventory", payload={"sku": "item_abc"}),
        SagaStep(name="charge_surcharge", compensation_action="refund_surcharge", payload={"amount_usd": 25.0}),
        SagaStep(name="book_courier", compensation_action="cancel_courier", payload={"simulate_failure": True}),
    ]

    ledger = await workflow.execute_action_saga(intent, steps=steps)
    assert ledger.execution_status == "COMPENSATED"
    assert ledger.error_code == "ERR_STEP_FAILED_COMPENSATED"

    # Verify compensation records
    recs = SAGA_REGISTRY.compensation_records
    assert len(recs) == 2

    # Step 2 compensated first (Reverse Order Invariant)
    assert recs[0].step_name == "charge_surcharge"
    assert recs[0].compensation_action == "refund_surcharge"
    assert recs[0].status == CompensationStatus.COMPLETED

    # Step 1 compensated second
    assert recs[1].step_name == "reserve_inventory"
    assert recs[1].compensation_action == "release_inventory"
    assert recs[1].status == CompensationStatus.COMPLETED


@pytest.mark.asyncio
async def test_compensation_activity_failure_escalates_to_failed_manual_required():
    """
    If a compensation activity fails, status transitions to FAILED_MANUAL_REQUIRED
    and pages on-call operations immediately.
    """
    workflow = SafeActionSagaWorkflow()
    tenant = TenantId("tnt_compound_03")
    intent = ActionIntentRecord(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant,
        approval_id=UUIDv7.generate(),
        idempotency_key="idemp_comp_failure",
        action_type="fulfill_order",
        classification=ActionClassification.COMPENSATABLE,
        target_set_count=1,
        payload_digest="digest_comp_fail",
        created_at=UtcDateTime.now(),
    )

    # Step 2 compensation will simulate an internal failure
    steps = [
        SagaStep(name="step_1_db_lock", compensation_action="release_lock", payload={}),
        SagaStep(
            name="step_2_api_call",
            compensation_action="undo_api_call",
            payload={"simulate_compensation_failure": True},
        ),
        SagaStep(name="step_3_terminal", compensation_action="undo_terminal", payload={"simulate_failure": True}),
    ]

    await workflow.execute_action_saga(intent, steps=steps)

    recs = SAGA_REGISTRY.compensation_records
    # Step 2 compensation failed, so it halted before Step 1
    assert len(recs) == 1
    assert recs[0].step_name == "step_2_api_call"
    assert recs[0].status == CompensationStatus.FAILED_MANUAL_REQUIRED

    # Verify on-call paging occurred
    assert len(SAGA_REGISTRY.paged_incidents) == 1
    assert SAGA_REGISTRY.paged_incidents[0]["step_name"] == "step_2_api_call"
