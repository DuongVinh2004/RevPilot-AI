"""
RevPilot AI — Unit Tests for Approval Request Expiration Lifecycle
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3.1
Conforms to AC-008: Approval requests past 24h TTL automatically expire
and fail closed against approval attempts.
"""

from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_approval_module():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.approval"):
            sys.modules.pop(mod, None)


@pytest.fixture
def approval_module():
    import revpilot.modules.approval as mod
    return mod


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_logistics_corp")


@pytest.mark.asyncio
async def test_approval_request_past_ttl_cannot_be_approved(approval_module, sample_tenant):
    """
    When attempting to approve a request past its expiry time,
    grant_approval marks it EXPIRED and raises ERR_APPROVAL_EXPIRED.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="LOGISTICS_EXPEDITE",
        target_customer_id="cust_001",
        target_entity_refs=["ship_001"],
        action_payload={"priority": "HIGH"},
        estimated_cost_usd=Decimal("50.00"),
        ttl_hours=24,
    )

    # Simulate clock advancing 25 hours into the future
    future_time = UtcDateTime.from_datetime(rec.created_at.value + timedelta(hours=25))

    with pytest.raises(approval_module.ApprovalError) as exc_info:
        await service.grant_approval(
            tenant_id=sample_tenant,
            approval_id=rec.approval_id,
            approver_principal_id="usr_ops_lead",
            approver_tier=1,
            expected_digest=rec.payload_digest,
            is_human=True,
            current_time=future_time,
        )
    assert exc_info.value.code == "ERR_APPROVAL_EXPIRED"

    # Verify status in database transitioned to EXPIRED
    stored = await repo.get(sample_tenant, rec.approval_id)
    assert stored is not None
    assert stored.status == approval_module.ApprovalStatus.EXPIRED


@pytest.mark.asyncio
async def test_expire_stale_requests_sweeper(approval_module, sample_tenant):
    """
    expire_stale_requests sweeps pending records and marks expired ones.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="LOGISTICS_EXPEDITE",
        target_customer_id="cust_001",
        target_entity_refs=["ship_001"],
        action_payload={"priority": "HIGH"},
        estimated_cost_usd=Decimal("50.00"),
        ttl_hours=24,
    )

    future_time = UtcDateTime.from_datetime(rec.created_at.value + timedelta(hours=26))
    swept = await service.expire_stale_requests(sample_tenant, future_time)
    assert swept == 1

    stored = await repo.get(sample_tenant, rec.approval_id)
    assert stored is not None
    assert stored.status == approval_module.ApprovalStatus.EXPIRED
