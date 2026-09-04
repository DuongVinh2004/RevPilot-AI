"""
RevPilot AI — Irreversible Action Compensation Guard Tests
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §4.2
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §10
Conforms to ADR-0002 and TC-P06-022.
"""

from __future__ import annotations
import pytest

from revpilot.modules.action.domain import (
    ActionClassification,
    ActionIntentRecord,
)
from revpilot.modules.action.saga import (
    CompensationStatus,
    IrreversibleActionError,
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
async def test_irreversible_action_direct_compensation_rejected():
    """
    Direct attempt to compensate an IRREVERSIBLE action must raise IrreversibleActionError
    and record FAILED_MANUAL_REQUIRED (TC-P06-022).
    """
    workflow = SafeActionSagaWorkflow()
    tenant = TenantId("tnt_logistics_corp")
    intent_id = UUIDv7.generate()

    completed_steps = [
        ("dispatch_freight_truck", {"driver_id": "drv_123"}),
        ("print_waybill_label", {"awb": "awb_999"}),
    ]

    with pytest.raises(IrreversibleActionError) as exc_info:
        await workflow.compensate_steps(
            completed_steps=completed_steps,
            tenant_id=tenant,
            intent_id=intent_id,
            classification=ActionClassification.IRREVERSIBLE,
        )

    err = exc_info.value
    assert err.code == "ERR_IRREVERSIBLE_ACTION"
    assert "manual intervention required" in err.message.lower()

    # Verify audit record flags manual intervention required
    recs = SAGA_REGISTRY.compensation_records
    assert len(recs) == 1
    assert recs[0].status == CompensationStatus.FAILED_MANUAL_REQUIRED
    assert recs[0].compensation_action == "FLAG_OPERATOR_MANUAL_TICKET"


@pytest.mark.asyncio
async def test_compound_workflow_with_irreversible_action_flags_manual_ticket_on_failure():
    """
    When a compound workflow marked IRREVERSIBLE experiences a downstream failure,
    it must not execute automated compensation; it flags manual intervention in the ledger.
    """
    workflow = SafeActionSagaWorkflow()
    tenant = TenantId("tnt_heavy_freight")
    intent = ActionIntentRecord(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant,
        approval_id=UUIDv7.generate(),
        idempotency_key="idemp_freight_irrev",
        action_type="dispatch_heavy_machinery",
        classification=ActionClassification.IRREVERSIBLE,
        target_set_count=1,
        payload_digest="digest_freight_001",
        created_at=UtcDateTime.now(),
    )

    steps = [
        SagaStep(name="crane_lift_machinery", compensation_action="undo_lift", payload={}),
        SagaStep(name="dispatch_truck_highway", compensation_action="turn_around_truck", payload={"simulate_failure": True}),
    ]

    ledger = await workflow.execute_action_saga(intent, steps=steps)

    # Must NOT be marked COMPENSATED
    assert ledger.execution_status == "PROVIDER_ERROR"
    assert ledger.error_code == "ERR_IRREVERSIBLE_MANUAL_REQUIRED"

    # Automated reverse compensation must NOT have run for crane_lift
    recs = SAGA_REGISTRY.compensation_records
    assert len(recs) == 1
    assert recs[0].status == CompensationStatus.FAILED_MANUAL_REQUIRED
    assert recs[0].compensation_action == "FLAG_OPERATOR_MANUAL_TICKET"
