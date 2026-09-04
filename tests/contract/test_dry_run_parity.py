"""
RevPilot AI — Contract Tests for Dry-Run Simulation Parity
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 4, §2 Stage 6
Conforms to AC-009: Dry-run simulation executes with identical validation logic,
returning simulated impact, cost, blast radius, and provider requirements.
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
async def test_dry_run_parity_contract(action_module, approval_module, sample_tenant, sample_context):
    """
    Dry-run simulation satisfies AC-009: evaluates identical parameters,
    computes blast radius and cost parity without physical dispatch.
    """
    intent_repo = action_module.InMemoryActionIntentRepository()
    ledger_repo = action_module.InMemoryActionLedgerRepository()
    service = action_module.ActionLedgerService(intent_repo, ledger_repo)

    approval_repo = approval_module.InMemoryApprovalRepository()
    approval_svc = approval_module.ApprovalService(approval_repo)

    # 1. Create approval request
    targets = ["order_sf_01", "order_sf_02", "order_sf_03"]
    payload = {"carrier": "fast_freight", "speed": "OVERNIGHT"}
    cost = Decimal("210.00")

    app_rec = await approval_svc.create_request(
        tenant_id=sample_tenant,
        decision_id=UUIDv7.generate(),
        action_type="CARRIER_EXPEDITE",
        target_customer_id="cust_001",
        target_entity_refs=targets,
        action_payload=payload,
        estimated_cost_usd=cost,
    )

    # 2. Create dry-run intent
    intent = await service.create_intent(
        ctx=sample_context,
        approval=app_rec,
        idempotency_key="idemp_dryrun_parity_001",
        classification=action_module.ActionClassification.REVERSIBLE,
        is_dry_run=True,
    )
    assert intent.is_dry_run is True
    assert intent.target_set_count == 3

    # 3. Execute dry run
    sim_result = await service.execute_dry_run(
        ctx=sample_context,
        intent=intent,
        payload=payload,
        cost_usd=cost,
        targets=targets,
    )

    # 4. Parity verification (AC-009)
    assert sim_result.is_dry_run is True
    assert sim_result.simulated_cost_usd == cost
    assert sim_result.simulated_blast_radius == 3
    assert sim_result.zero_side_effect_verified is True
    assert "estimated_churn_reduction_pct" in sim_result.simulated_impact
    assert sim_result.provider_requirements["idempotency_supported"] is True
