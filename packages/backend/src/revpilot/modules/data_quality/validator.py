"""
RevPilot AI — Data Quality Rule Evaluation Engine (Phase 01)
Adheres to docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md §3, §4 and INV-TEN-001.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict, Optional, Set, List
from datetime import datetime, timezone

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.canonical.enums import Currency
from revpilot.modules.data_quality.rules import (
    DQ_SCH_001,
    DQ_REQ_001,
    DQ_TYP_001,
    DQ_REF_001,
    DQ_TEN_001,
    DQ_ORD_001,
    DQ_CUR_001,
    ValidationResult,
)

_VALID_CURRENCIES: Set[str] = {c.value for c in Currency}
_MIN_EPOCH = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


class DataQualityValidator:
    """
    Evaluates incoming raw and normalized payloads against canonical data quality rules.
    Enforces fail-closed isolation and routes defective or cross-tenant payloads to quarantine.
    """

    def __init__(self) -> None:
        self.audit_log: List[Dict[str, Any]] = []

    def validate_record(
        self,
        record: Dict[str, Any],
        session_tenant_id: TenantId,
        parent_entities: Optional[Dict[str, Set[str]]] = None,
    ) -> ValidationResult:
        """
        Execute data quality validation pipeline on an individual payload record.
        Args:
            record: Raw or normalized dictionary payload.
            session_tenant_id: Authenticated session/connector TenantId.
            parent_entities: Optional mapping of entity collections to existing primary keys in tenant.
        Returns:
            ValidationResult (is_valid=True or is_valid=False with rule_id and error_code).
        """
        # 1. Schema Validation (DQ-SCH-001)
        if not isinstance(record, dict):
            return ValidationResult.failure(
                rule_id=DQ_SCH_001,
                error_code="SCHEMA_VALIDATION_FAILED",
                rejection_reason="Payload is not a valid dictionary structure",
            )

        # 2. Tenant Ownership Validation (DQ-TEN-001)
        record_tenant = record.get("tenant_id")
        if record_tenant is not None:
            tenant_val = record_tenant.value if isinstance(record_tenant, TenantId) else str(record_tenant)
            if tenant_val != session_tenant_id.value:
                # Log security audit event for cross-tenant injection
                self.audit_log.append({
                    "event_type": "SECURITY_TENANT_MISMATCH",
                    "session_tenant_id": session_tenant_id.value,
                    "payload_tenant_id": tenant_val,
                    "timestamp": UtcDateTime.now().isoformat(),
                    "record_id": record.get("id"),
                })
                return ValidationResult.failure(
                    rule_id=DQ_TEN_001,
                    error_code="TENANT_MISMATCH_DETECTED",
                    rejection_reason=f"Cross-tenant injection attempt: record tenant {tenant_val} != session {session_tenant_id.value}",
                )
        else:
            return ValidationResult.failure(
                rule_id=DQ_REQ_001,
                error_code="MISSING_MANDATORY_FIELD",
                rejection_reason="Missing required tenant_id field",
            )

        # 3. Mandatory Non-Null Fields (DQ-REQ-001)
        for req_field in ("id", "event_time"):
            val = record.get(req_field)
            if val is None or (isinstance(val, str) and not val.strip()):
                return ValidationResult.failure(
                    rule_id=DQ_REQ_001,
                    error_code="MISSING_MANDATORY_FIELD",
                    rejection_reason=f"Mandatory field '{req_field}' is missing, null, or empty",
                )

        # 4. Type and Numeric Range Check (DQ-TYP-001)
        monetary_fields = ("total_cents", "subtotal_cents", "tax_cents", "shipping_cents", "unit_price_cents", "amount_cents")
        for field_name in monetary_fields:
            if field_name in record and record[field_name] is not None:
                val = record[field_name]
                if not isinstance(val, int) or val < 0:
                    return ValidationResult.failure(
                        rule_id=DQ_TYP_001,
                        error_code="RANGE_CHECK_FAILED",
                        rejection_reason=f"Field '{field_name}' must be a non-negative integer (cents), got: {val!r}",
                    )

        if "quantity" in record and record["quantity"] is not None:
            qty = record["quantity"]
            if not isinstance(qty, int) or qty <= 0:
                return ValidationResult.failure(
                    rule_id=DQ_TYP_001,
                    error_code="RANGE_CHECK_FAILED",
                    rejection_reason=f"Field 'quantity' must be a positive integer, got: {qty!r}",
                )

        if "impact_capacity_reduction_pct" in record and record["impact_capacity_reduction_pct"] is not None:
            pct_val = record["impact_capacity_reduction_pct"]
            try:
                dec_val = Decimal(str(pct_val))
                if dec_val < Decimal("0.00") or dec_val > Decimal("100.00"):
                    return ValidationResult.failure(
                        rule_id=DQ_TYP_001,
                        error_code="RANGE_CHECK_FAILED",
                        rejection_reason=f"Field 'impact_capacity_reduction_pct' must be between 0.00 and 100.00, got: {pct_val!r}",
                    )
            except Exception:
                return ValidationResult.failure(
                    rule_id=DQ_TYP_001,
                    error_code="RANGE_CHECK_FAILED",
                    rejection_reason=f"Field 'impact_capacity_reduction_pct' is not a valid decimal: {pct_val!r}",
                )

        # 5. Currency Code (DQ-CUR-001)
        if "currency" in record and record["currency"] is not None:
            curr_val = record["currency"].value if isinstance(record["currency"], Currency) else str(record["currency"])
            if curr_val not in _VALID_CURRENCIES:
                return ValidationResult.failure(
                    rule_id=DQ_CUR_001,
                    error_code="UNSUPPORTED_CURRENCY",
                    rejection_reason=f"Currency '{curr_val}' is not a recognized canonical currency",
                )

        # 6. Event Ordering & Timestamp Sanity (DQ-ORD-001)
        raw_et = record.get("event_time")
        try:
            if isinstance(raw_et, UtcDateTime):
                et_dt = raw_et.value
            elif isinstance(raw_et, datetime):
                et_dt = raw_et if raw_et.tzinfo is not None else raw_et.replace(tzinfo=timezone.utc)
            else:
                et_dt = datetime.fromisoformat(str(raw_et).replace("Z", "+00:00"))

            if et_dt < _MIN_EPOCH:
                return ValidationResult.failure(
                    rule_id=DQ_ORD_001,
                    error_code="INVALID_TIMESTAMP_SEQUENCE",
                    rejection_reason=f"event_time {et_dt.isoformat()} precedes minimum epoch 2020-01-01",
                )
        except Exception as e:
            return ValidationResult.failure(
                rule_id=DQ_ORD_001,
                error_code="INVALID_TIMESTAMP_SEQUENCE",
                rejection_reason=f"Failed to parse event_time: {e}",
            )

        if "effective_from" in record and "effective_to" in record and record["effective_to"] is not None:
            try:
                ef_raw = record["effective_from"]
                et_raw = record["effective_to"]
                ef_dt = ef_raw.value if isinstance(ef_raw, UtcDateTime) else datetime.fromisoformat(str(ef_raw).replace("Z", "+00:00"))
                et_dt = et_raw.value if isinstance(et_raw, UtcDateTime) else datetime.fromisoformat(str(et_raw).replace("Z", "+00:00"))
                if et_dt < ef_dt:
                    return ValidationResult.failure(
                        rule_id=DQ_ORD_001,
                        error_code="INVALID_TIMESTAMP_SEQUENCE",
                        rejection_reason=f"effective_to {et_dt.isoformat()} precedes effective_from {ef_dt.isoformat()}",
                    )
            except Exception as e:
                return ValidationResult.failure(
                    rule_id=DQ_ORD_001,
                    error_code="INVALID_TIMESTAMP_SEQUENCE",
                    rejection_reason=f"Failed to validate effective timestamp sequence: {e}",
                )

        # 7. Referential Integrity (DQ-REF-001)
        if parent_entities is not None:
            if "customer_id" in record and record["customer_id"] is not None:
                cust_id = record["customer_id"]
                valid_customers = parent_entities.get("customers", set())
                if cust_id not in valid_customers:
                    return ValidationResult.failure(
                        rule_id=DQ_REF_001,
                        error_code="ORPHAN_FOREIGN_KEY",
                        rejection_reason=f"Referenced customer_id '{cust_id}' does not exist in tenant canonical dataset",
                    )

            if "order_id" in record and record["order_id"] is not None:
                ord_id = record["order_id"]
                valid_orders = parent_entities.get("orders", set())
                if ord_id not in valid_orders:
                    return ValidationResult.failure(
                        rule_id=DQ_REF_001,
                        error_code="ORPHAN_FOREIGN_KEY",
                        rejection_reason=f"Referenced order_id '{ord_id}' does not exist in tenant canonical dataset",
                    )

        return ValidationResult.success()


__all__ = [
    "DataQualityValidator",
]
