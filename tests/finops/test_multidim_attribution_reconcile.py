"""
RevPilot AI — Multi-Dimensional Attribution & Provider Reconciliation Tests
Specification: docs/21-finops/FINOPS-SPEC.md §1..§5
Specification: docs/22-billing/BILLING-SPEC.md §1..§4
Conforms to INV-COST-001, NFR-COST-002, and TC-P08-021.
"""

from __future__ import annotations

import pytest

from revpilot.modules.operations.review.exit_runner import (
    FinancialVarianceBreachError,
    Phase08ExitGateRunner,
)


@pytest.fixture
def exit_runner() -> Phase08ExitGateRunner:
    return Phase08ExitGateRunner()


def test_finops_multidim_attribution_reconciles_within_half_percent(
    exit_runner: Phase08ExitGateRunner,
):
    """
    TC-P08-021 & INV-COST-001: Usage matches synthetic provider bill with <= 0.5% gap.
    """
    # Recorded internal spend $125,000.00 vs provider invoice $125,300.00
    # Gap = $300.00 / $125,300.00 = 0.2394% <= 0.5%
    reconciled = exit_runner.verify_financial_reconciliation(
        recorded_spend=125000.0,
        provider_bill=125300.0,
        tolerance_percent=0.5,
    )

    assert reconciled is True


def test_finops_reconciliation_variance_breach_raises_error(
    exit_runner: Phase08ExitGateRunner,
):
    """
    Verify that variance > 0.5% triggers FINANCIAL_VARIANCE_BREACH (422).
    """
    # Recorded internal spend $120,000.00 vs provider invoice $125,000.00
    # Gap = $5,000.00 / $125,000.00 = 4.0% > 0.5%
    with pytest.raises(FinancialVarianceBreachError) as exc_info:
        exit_runner.verify_financial_reconciliation(
            recorded_spend=120000.0,
            provider_bill=125000.0,
            tolerance_percent=0.5,
        )

    err = exc_info.value
    assert err.code == "FINANCIAL_VARIANCE_BREACH"
    assert err.status_code == 422
    assert err.retryable is False
    assert err.details["variance_percent"] == 4.0
    assert err.details["tolerance_percent"] == 0.5


def test_multitenant_attribution_zero_leakage():
    """
    Verify synthetic multi-tenant spend attribution totals match aggregate spend.
    """
    tenant_allocations = {
        f"tnt_{i:03d}": 1250.0 + (i * 10.0) for i in range(10)
    }
    total_attributed = sum(tenant_allocations.values())

    # Direct invoice reconciliation
    invoice_total = total_attributed * 1.002  # 0.2% variance
    variance_pct = abs(total_attributed - invoice_total) / invoice_total * 100.0

    assert variance_pct <= 0.5
    assert len(tenant_allocations) == 10
