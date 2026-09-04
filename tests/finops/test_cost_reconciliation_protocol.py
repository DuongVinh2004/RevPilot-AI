"""
RevPilot AI — TC-P07-024: Provider Cost Reconciliation Protocol Test
Specification: docs/21-finops/FINOPS-SPEC.md §4
Conforms to NFR-COST-002.
"""

from decimal import Decimal
import sys
import pytest

from revpilot.shared.identifiers import TenantId, PrincipalId


@pytest.fixture(autouse=True)
def _isolate_finops_module():
    """Ensure finops module is clean in test environment."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.finops"):
            sys.modules.pop(mod, None)


def test_provider_cost_reconciliation_variance_matching():
    """
    TC-P07-024:
    - Items with variance <= 2% transition from ESTIMATED to RECONCILED.
    - Items with variance > 2% transition to DISCREPANCY and flag FinOps gap alert.
    """
    from revpilot.modules.finops import (
        MeteringService,
        MeteringUnit,
        ProviderReconciliationService,
        ReconciliationStatus,
        ReconciliationGapError,
    )

    metering = MeteringService()
    reconciliation = ProviderReconciliationService(metering_service=metering)

    tenant_id = TenantId.generate()
    principal_id = PrincipalId.generate()

    # 1. Setup Usage Records
    # Record 1: estimated $10.00
    u1 = metering.record_usage(
        tenant_id=tenant_id,
        principal_id=principal_id,
        dimension=MeteringUnit.TOKENS,
        quantity=Decimal("100000"),
        estimated_cost=Decimal("10.00"),
        idempotency_key="req_anthropic_call_001",
    )
    # Record 2: estimated $20.00
    u2 = metering.record_usage(
        tenant_id=tenant_id,
        principal_id=principal_id,
        dimension=MeteringUnit.TOKENS,
        quantity=Decimal("200000"),
        estimated_cost=Decimal("20.00"),
        idempotency_key="req_anthropic_call_002",
    )

    # 2. Cycle 1: Provider invoice with variance <= 2%
    # Item 1: actual $10.15 (1.5% variance <= 2%)
    # Item 2: actual $19.80 (1.0% variance <= 2%)
    invoice_within_tolerance = [
        {"idempotency_key": "req_anthropic_call_001", "actual_usd": Decimal("10.15")},
        {"idempotency_key": "req_anthropic_call_002", "actual_usd": Decimal("19.80")},
    ]

    report = reconciliation.reconcile_monthly_cycle(
        tenant_id=tenant_id,
        provider_invoice_records=invoice_within_tolerance,
        cycle_id="cycle_september_2026",
    )

    assert report.status == "RECONCILED"
    assert report.matched_records_count == 2
    assert report.discrepancy_count == 0
    assert report.variance_pct <= 0.02

    rec1 = metering.get_usage_record(u1)
    rec2 = metering.get_usage_record(u2)
    assert rec1.reconciliation_status == ReconciliationStatus.RECONCILED
    assert rec2.reconciliation_status == ReconciliationStatus.RECONCILED

    # 3. Cycle 2: Discrepant Invoice (> 2% variance)
    # Record 3: estimated $50.00, actual $65.00 (30% variance)
    u3 = metering.record_usage(
        tenant_id=tenant_id,
        principal_id=principal_id,
        dimension=MeteringUnit.CALLS,
        quantity=Decimal("500"),
        estimated_cost=Decimal("50.00"),
        idempotency_key="req_tool_gateway_call_003",
    )

    invoice_discrepant = [
        {"idempotency_key": "req_tool_gateway_call_003", "actual_usd": Decimal("65.00")},
    ]

    report_discrepant = reconciliation.reconcile_monthly_cycle(
        tenant_id=tenant_id,
        provider_invoice_records=invoice_discrepant,
        cycle_id="cycle_flagged_gap",
    )
    assert report_discrepant.status == "DISCREPANCY"
    assert report_discrepant.discrepancy_count == 1

    rec3 = metering.get_usage_record(u3)
    assert rec3.reconciliation_status == ReconciliationStatus.DISCREPANCY

    # Strict mode raises 422 RECONCILIATION_GAP
    with pytest.raises(ReconciliationGapError) as exc_info:
        reconciliation.reconcile_monthly_cycle(
            tenant_id=tenant_id,
            provider_invoice_records=invoice_discrepant,
            cycle_id="cycle_flagged_gap",
            strict_fail=True,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "RECONCILIATION_GAP"
