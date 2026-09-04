"""
RevPilot AI — Deterministic Provider Reconciliation Protocol Tests
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §4.1
Specification: docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §10.2
Specification: docs/26-api/EVENT-CONTRACTS.md §8
Conforms to NFR-REL-001 and TC-P06-024.
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
)
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture
def test_context():
    tenant = TenantId("tnt_reconcile_test")
    intent = ActionIntentRecord(
        intent_id=UUIDv7.generate(),
        tenant_id=tenant,
        approval_id=UUIDv7.generate(),
        idempotency_key="idemp_recon_12345",
        action_type="book_priority_freight",
        classification=ActionClassification.COMPENSATABLE,
        target_set_count=1,
        payload_digest="digest_recon_test",
        created_at=UtcDateTime.now(),
    )
    ledger = ActionLedgerRecord(
        ledger_id=UUIDv7.generate(),
        tenant_id=tenant,
        intent_id=intent.intent_id,
        attempt_number=1,
        idempotency_key=intent.idempotency_key,
        provider_name="dhl_courier_api",
        request_digest=intent.payload_digest,
        execution_status="TIMEOUT_UNKNOWN",
        error_code="TIMEOUT_UNKNOWN",
        started_at=UtcDateTime.now(),
    )
    return intent, ledger


@pytest.mark.asyncio
async def test_provider_status_inquiry_succeeds_confirmed(test_context):
    """
    Scenario 1: Provider status inquiry succeeds with transaction confirmed (TC-P06-024).
    Ledger updates to RECONCILED with provider transaction ID.
    """
    intent, ledger = test_context
    mgr = ReconciliationManager()

    def query_confirmed(provider: str, key: str) -> ProviderInquiryResult:
        return ProviderInquiryResult(
            status=ProviderTransactionStatus.CONFIRMED,
            provider_tx_id="dhl_tx_998877",
            details={"shipment_status": "MANIFESTED"},
        )

    updated_ledger = await mgr.reconcile_unknown(intent, ledger, query_fn=query_confirmed)

    assert updated_ledger.execution_status == "RECONCILED"
    assert updated_ledger.provider_tx_id == "dhl_tx_998877"
    assert updated_ledger.error_code is None
    assert len(mgr.emitted_outbox_events) == 0


@pytest.mark.asyncio
async def test_provider_status_inquiry_returns_no_record_enables_safe_retry(test_context):
    """
    Scenario 2: Provider inquiry returns NO_RECORD (TC-P06-024).
    Ledger updates to PROVIDER_ERROR with FAILED_NO_DISPATCH; allows safe retry.
    """
    intent, ledger = test_context
    mgr = ReconciliationManager()

    def query_no_record(provider: str, key: str) -> ProviderInquiryResult:
        return ProviderInquiryResult(
            status=ProviderTransactionStatus.NO_RECORD,
            details={"message": "No transaction found matching idempotency key"},
        )

    updated_ledger = await mgr.reconcile_unknown(intent, ledger, query_fn=query_no_record)

    assert updated_ledger.execution_status == "PROVIDER_ERROR"
    assert updated_ledger.error_code == "FAILED_NO_DISPATCH"
    assert updated_ledger.provider_tx_id is None
    assert len(mgr.emitted_outbox_events) == 0


@pytest.mark.asyncio
async def test_inconclusive_inquiry_exhausts_retries_emits_escalation_event(test_context):
    """
    Scenario 3: Provider status remains indeterminate after 3 inquiry attempts (TC-P06-024).
    Ledger status updates to TIMEOUT_UNKNOWN with ERR_RECONCILIATION_REQUIRED,
    outbox event action.reconciliation_required.v1 is emitted, and workflow is parked.
    """
    intent, ledger = test_context
    mgr = ReconciliationManager()

    inquiry_calls = 0

    def query_inconclusive(provider: str, key: str) -> ProviderInquiryResult:
        nonlocal inquiry_calls
        inquiry_calls += 1
        return ProviderInquiryResult(
            status=ProviderTransactionStatus.INCONCLUSIVE,
            details={"http_status": 504, "error": "Gateway timeout during status inquiry"},
        )

    updated_ledger = await mgr.reconcile_unknown(
        intent,
        ledger,
        query_fn=query_inconclusive,
        max_attempts=3,
    )

    # Invariant: exactly 3 inquiry attempts made
    assert inquiry_calls == 3
    assert updated_ledger.execution_status == "TIMEOUT_UNKNOWN"
    assert updated_ledger.error_code == "ERR_RECONCILIATION_REQUIRED"

    # Verify outbox event emitted for human operator queue
    assert len(mgr.emitted_outbox_events) == 1
    event = mgr.emitted_outbox_events[0]
    assert event.event_type == "action.reconciliation_required.v1"
    assert event.tenant_id == intent.tenant_id
    assert event.aggregate_id == str(ledger.ledger_id)
    assert event.payload["attempts"] == 3
    assert event.payload["idempotency_key"] == intent.idempotency_key
    assert "SRE intervention required" in event.payload["reason"]
