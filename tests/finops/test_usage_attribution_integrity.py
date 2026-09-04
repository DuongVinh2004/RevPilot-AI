"""
RevPilot AI — TC-P07-023: Multi-Dimensional Usage Attribution Integrity Test
Specification: docs/21-finops/FINOPS-SPEC.md §1.1, §3
Conforms to AC-P07-007-02, FR-CTL-002, and NFR-COST-001.
"""

from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, PrincipalId, UUIDv7


@pytest.fixture(autouse=True)
def _isolate_finops_module():
    """Ensure finops module is clean in test environment."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.finops"):
            sys.modules.pop(mod, None)


def test_multi_dimensional_usage_attribution_integrity():
    """
    TC-P07-023 / AC-P07-007-02:
    - 100% of usage is strictly attributed across tenant, principal, and investigation hierarchy.
    - Idempotency key duplication raises 409 DUPLICATE_USAGE.
    - Cryptographic record hash ensures ledger integrity.
    """
    from revpilot.modules.finops import (
        MeteringService,
        MeteringUnit,
        DuplicateUsageError,
        ReconciliationStatus,
    )

    metering = MeteringService()

    tenant_id = TenantId.generate()
    principal_id = PrincipalId.generate()
    investigation_id = UUIDv7.generate()
    idempotency_key = "idemp_stripe_llm_inference_7744"

    # 1. Record Valid Usage
    usage_id = metering.record_usage(
        tenant_id=tenant_id,
        principal_id=principal_id,
        dimension=MeteringUnit.TOKENS,
        quantity=Decimal("1500"),
        estimated_cost=Decimal("0.045"),
        idempotency_key=idempotency_key,
        investigation_id=investigation_id,
        workflow_id="wf_churn_investigation_001",
        agent_name="hypothesis_generator",
        model_or_tool_name="claude-3-5-sonnet",
    )

    rec = metering.get_usage_record(usage_id)
    assert rec.tenant_id == tenant_id
    assert rec.principal_id == principal_id
    assert rec.investigation_id == investigation_id
    assert rec.dimension == MeteringUnit.TOKENS
    assert rec.quantity == Decimal("1500")
    assert rec.estimated_provider_cost_usd == Decimal("0.045")
    assert rec.reconciliation_status == ReconciliationStatus.ESTIMATED
    assert len(rec.record_hash) == 64  # SHA-256 hash digest

    # 2. Reject Duplicate Idempotency Key (409 DUPLICATE_USAGE)
    with pytest.raises(DuplicateUsageError) as exc_info:
        metering.record_usage(
            tenant_id=tenant_id,
            principal_id=principal_id,
            dimension=MeteringUnit.TOKENS,
            quantity=Decimal("1500"),
            estimated_cost=Decimal("0.045"),
            idempotency_key=idempotency_key,
            investigation_id=investigation_id,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "DUPLICATE_USAGE"

    # 3. Query Attribution Filter
    results = metering.list_usage_records(tenant_id=tenant_id, investigation_id=investigation_id)
    assert len(results) == 1
    assert results[0].usage_id == usage_id
