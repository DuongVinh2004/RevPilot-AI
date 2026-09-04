"""
RevPilot AI — Unit Tests for Approval Request Creation and Sealing
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1, §3.1
Conforms to INV-ACT-002, AC-008, and ADR-0003.
"""

from __future__ import annotations
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
async def test_approval_request_creation_and_digest_sealing(approval_module, sample_tenant):
    """
    Approval request is created with status PENDING, SHA-256 payload digest,
    policy digest, 24-hour expiry TTL, and appropriate required approval tier.
    """
    repo = approval_module.InMemoryApprovalRepository()
    service = approval_module.ApprovalService(repo)

    decision_id = UUIDv7.generate()
    action_type = "FREIGHT_CARRIER_EXPEDITE"
    targets = ["order_mw_1001", "order_mw_1002"]
    payload = {
        "carrier": "regional_express",
        "service_level": "NEXT_DAY_AIR",
        "insurance_waived": True,
    }
    cost = Decimal("150.00")

    rec = await service.create_request(
        tenant_id=sample_tenant,
        decision_id=decision_id,
        action_type=action_type,
        target_customer_id="cust_enterprise_01",
        target_entity_refs=targets,
        action_payload=payload,
        estimated_cost_usd=cost,
        risk_tier="LOW",
        decision_digest="sha256_mock_decision",
        policy_rules="retention_policy_v1.0",
        ttl_hours=24,
    )

    # 1. State Invariants
    assert rec.status == approval_module.ApprovalStatus.PENDING
    assert rec.tenant_id == sample_tenant
    assert rec.decision_id == decision_id
    assert rec.action_type == action_type
    assert rec.target_entity_refs == targets
    assert rec.estimated_cost_usd == cost
    assert rec.reserved_budget_usd == cost
    assert rec.required_approval_tier == 1  # LOW risk, <= 250 -> Tier 1

    # 2. Cryptographic Digest Sealing (INV-ACT-002, AC-008)
    assert len(rec.payload_digest) == 64
    assert len(rec.policy_digest) == 64
    expected_digest = approval_module.ApprovalDigestHasher.compute_payload_digest(
        action_type=action_type,
        target_entities=targets,
        payload=payload,
        cost_usd=cost,
    )
    assert rec.payload_digest == expected_digest

    # 3. 24-hour TTL Expiry Time
    ttl_seconds = rec.expiry_time.value.timestamp() - rec.created_at.value.timestamp()
    assert 86390 <= ttl_seconds <= 86410  # ~24 hours

    # 4. Persistence verification
    stored = await repo.get(sample_tenant, rec.approval_id)
    assert stored is not None
    assert stored.approval_id == rec.approval_id
