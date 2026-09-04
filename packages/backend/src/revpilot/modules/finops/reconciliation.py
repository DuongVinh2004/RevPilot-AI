"""
RevPilot AI — Provider Cost Reconciliation Protocol
Specification: docs/21-finops/FINOPS-SPEC.md §4
Conforms to NFR-COST-002 and TC-P07-024.
"""

from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from revpilot.shared.identifiers import TenantId
from revpilot.modules.finops.quota import QuotaError
from revpilot.modules.finops.metering import (
    MeteringService,
    ReconciliationStatus,
)


class ReconciliationGapError(QuotaError):
    def __init__(self, message: str = "Reconciliation variance exceeds 2% threshold") -> None:
        super().__init__(message=message, code="RECONCILIATION_GAP", status_code=422)


class ReconciliationReport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tenant_id: TenantId
    cycle_id: str
    total_estimated_usd: Decimal
    total_actual_usd: Decimal
    variance_pct: float
    matched_records_count: int
    discrepancy_count: int
    status: str  # "RECONCILED" or "DISCREPANCY"


class ProviderReconciliationService:
    """
    Reconciles internal estimated usage records against external provider invoices.
    Applies strict 2% variance threshold (FINOPS-SPEC.md §4).
    """

    def __init__(self, metering_service: MeteringService) -> None:
        self.metering_service = metering_service

    def reconcile_monthly_cycle(
        self,
        tenant_id: TenantId,
        provider_invoice_records: list[dict],
        cycle_id: str = "monthly_cycle_001",
        strict_fail: bool = False,
    ) -> ReconciliationReport:
        """
        Reconcile provider bill line items with internal UsageRecords.
        Items within <= 2% variance transition to RECONCILED.
        Items > 2% variance transition to DISCREPANCY.
        """
        records = self.metering_service.list_usage_records(tenant_id)
        records_by_key = {r.idempotency_key: r for r in records}

        matched_count = 0
        discrepancy_count = 0
        total_estimated = Decimal("0.00")
        total_actual = Decimal("0.00")

        for invoice_item in provider_invoice_records:
            idemp_key = invoice_item["idempotency_key"]
            actual_cost = Decimal(str(invoice_item["actual_usd"]))
            total_actual += actual_cost

            rec = records_by_key.get(idemp_key)
            if not rec:
                discrepancy_count += 1
                continue

            matched_count += 1
            est_cost = rec.estimated_provider_cost_usd
            total_estimated += est_cost

            # Evaluate Individual Variance
            if est_cost > Decimal("0.00"):
                diff = abs(actual_cost - est_cost)
                var = float(diff / est_cost)
                if var <= 0.02:  # <= 2% variance tolerance
                    rec.reconciliation_status = ReconciliationStatus.RECONCILED
                else:
                    rec.reconciliation_status = ReconciliationStatus.DISCREPANCY
                    discrepancy_count += 1
            else:
                if actual_cost == Decimal("0.00"):
                    rec.reconciliation_status = ReconciliationStatus.RECONCILED
                else:
                    rec.reconciliation_status = ReconciliationStatus.DISCREPANCY
                    discrepancy_count += 1

        # Calculate Overall Cycle Variance Percentage
        if total_estimated > Decimal("0.00"):
            cycle_variance = float(abs(total_actual - total_estimated) / total_estimated)
        else:
            cycle_variance = 0.0 if total_actual == Decimal("0.00") else 1.0

        status = "RECONCILED" if (cycle_variance <= 0.02 and discrepancy_count == 0) else "DISCREPANCY"

        if strict_fail and status == "DISCREPANCY":
            raise ReconciliationGapError(
                f"Reconciliation cycle '{cycle_id}' variance {cycle_variance*100:.2f}% exceeds 2% threshold with {discrepancy_count} discrepancy item(s)"
            )

        return ReconciliationReport(
            tenant_id=tenant_id,
            cycle_id=cycle_id,
            total_estimated_usd=total_estimated,
            total_actual_usd=total_actual,
            variance_pct=cycle_variance,
            matched_records_count=matched_count,
            discrepancy_count=discrepancy_count,
            status=status,
        )
