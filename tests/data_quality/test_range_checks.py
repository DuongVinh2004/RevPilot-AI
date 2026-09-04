"""
RevPilot AI — Range, Type, and Timestamp Sanity Tests (Phase 01)
Verifies DATA-QUALITY-LINEAGE-SPEC.md §3.3, §3.7, §3.8 (DQ-TYP-001, DQ-ORD-001, DQ-CUR-001).
"""

from __future__ import annotations
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.modules.data_quality import (
    DataQualityValidator,
    DQ_TYP_001,
    DQ_CUR_001,
    DQ_ORD_001,
)


@pytest.fixture
def validator():
    return DataQualityValidator()


@pytest.mark.parametrize("invalid_total", [-1, -500, -999999, "not_int", 50.5])
def test_negative_or_non_integer_monetary_amount_rejected(validator, invalid_total):
    """DQ-TYP-001: Monetary values must be non-negative integers (cents)."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "ord_range_01",
        "event_time": "2026-01-01T00:00:00Z",
        "total_cents": invalid_total,
        "currency": "USD",
    }
    res = validator.validate_record(payload, session_tenant_id=TenantId("tnt_alpha"))
    assert not res.is_valid
    assert res.rule_id == DQ_TYP_001
    assert res.error_code == "RANGE_CHECK_FAILED"


@pytest.mark.parametrize("invalid_qty", [0, -1, -50, "two", 1.5])
def test_non_positive_quantity_rejected(validator, invalid_qty):
    """DQ-TYP-001: Quantities must be positive integers (> 0)."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "orl_range_01",
        "event_time": "2026-01-01T00:00:00Z",
        "quantity": invalid_qty,
        "currency": "USD",
    }
    res = validator.validate_record(payload, session_tenant_id=TenantId("tnt_alpha"))
    assert not res.is_valid
    assert res.rule_id == DQ_TYP_001
    assert res.error_code == "RANGE_CHECK_FAILED"


@pytest.mark.parametrize("invalid_pct", [-1.0, -0.01, 100.01, 150.0, "not_a_num"])
def test_impact_percentage_out_of_bounds_rejected(validator, invalid_pct):
    """DQ-TYP-001: impact_capacity_reduction_pct must be between 0.00 and 100.00."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "mte_range_01",
        "event_time": "2026-01-01T00:00:00Z",
        "impact_capacity_reduction_pct": invalid_pct,
    }
    res = validator.validate_record(payload, session_tenant_id=TenantId("tnt_alpha"))
    assert not res.is_valid
    assert res.rule_id == DQ_TYP_001
    assert res.error_code == "RANGE_CHECK_FAILED"


@pytest.mark.parametrize("invalid_curr", ["XYZ", "BITCOIN", "US", "DOLLARS", ""])
def test_unsupported_currency_rejected(validator, invalid_curr):
    """DQ-CUR-001: Unknown or unmapped currency codes fail validation."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "ord_curr_01",
        "event_time": "2026-01-01T00:00:00Z",
        "total_cents": 1000,
        "currency": invalid_curr,
    }
    res = validator.validate_record(payload, session_tenant_id=TenantId("tnt_alpha"))
    assert not res.is_valid
    assert res.rule_id == DQ_CUR_001
    assert res.error_code == "UNSUPPORTED_CURRENCY"


def test_ancient_timestamp_rejected(validator):
    """DQ-ORD-001: Event times prior to 2020-01-01 are rejected."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "ord_time_01",
        "event_time": "2018-05-12T10:00:00Z",
        "total_cents": 1000,
        "currency": "USD",
    }
    res = validator.validate_record(payload, session_tenant_id=TenantId("tnt_alpha"))
    assert not res.is_valid
    assert res.rule_id == DQ_ORD_001
    assert res.error_code == "INVALID_TIMESTAMP_SEQUENCE"


def test_effective_to_preceding_effective_from_rejected(validator):
    """DQ-ORD-001: effective_to cannot precede effective_from."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "ctr_time_01",
        "event_time": "2026-01-01T00:00:00Z",
        "effective_from": "2026-01-10T00:00:00Z",
        "effective_to": "2026-01-05T00:00:00Z",  # before from!
    }
    res = validator.validate_record(payload, session_tenant_id=TenantId("tnt_alpha"))
    assert not res.is_valid
    assert res.rule_id == DQ_ORD_001
    assert res.error_code == "INVALID_TIMESTAMP_SEQUENCE"
