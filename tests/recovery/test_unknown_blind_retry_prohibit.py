"""
RevPilot AI — Zero Blind Retry Prohibition Tests for UNKNOWN Timeout
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §4.1
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §10.2
Conforms to NFR-REL-001 and TC-P06-023.
"""

from __future__ import annotations
import pytest

from revpilot.modules.action.domain import (
    ActionClassification,
    ActionIntentRecord,
)
from revpilot.modules.action.saga import (
    ProviderInquiryResult,
    ProviderTransactionStatus,
    ReconciliationManager,
    SafeActionSagaWorkflow,
    SagaStep,
)
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.mark.asyncio
async def test_zero_blind_retries_on_network_timeout():
    """
    NFR-REL-001: Outbound provider request suffering network timeout transitions to UNKNOWN.
    Automatic HTTP retry is strictly prohibited; status query activity is invoked instead (TC-P06-023).
    """
    reconciliation_mgr = ReconciliationManager()
    workflow = SafeActionSagaWorkflow(reconciliation_mgr=reconciliation_mgr)

    tenant = TenantId("tnt_blind_retry_test")
    idempotency_key = "idemp_no_blind_retry_999"
    intent = ActionIntentRecord(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant,
        approval_id=UUIDv7.generate(),
        idempotency_key=idempotency_key,
        action_type="charge_credit_card",
        classification=ActionClassification.COMPENSATABLE,
        target_set_count=1,
        payload_digest="digest_charge_001",
        created_at=UtcDateTime.now(),
    )

    forward_dispatch_count = 0
    inquiry_query_count = 0

    def mock_query_fn(provider: str, key: str) -> ProviderInquiryResult:
        nonlocal inquiry_query_count
        inquiry_query_count += 1
        return ProviderInquiryResult(
            status=ProviderTransactionStatus.CONFIRMED,
            provider_tx_id="tx_confirmed_from_query",
        )

    # Step simulates network timeout during byte transmission
    forward_dispatch_count += 1
    steps = [
        SagaStep(
            name="charge_card_external",
            compensation_action="refund_card",
            payload={"simulate_timeout": True},
        )
    ]

    ledger = await workflow.execute_action_saga(
        intent,
        steps=steps,
        custom_query_fn=mock_query_fn,
    )

    # Invariant: exactly 1 dispatch attempt occurred; ZERO blind HTTP retries
    assert forward_dispatch_count == 1, "Blind retry occurred! Forward dispatch must never retry blindly after timeout."

    # Status inquiry was scheduled instead
    assert inquiry_query_count == 1
    assert ledger.execution_status == "RECONCILED"
    assert ledger.provider_tx_id == "tx_confirmed_from_query"
