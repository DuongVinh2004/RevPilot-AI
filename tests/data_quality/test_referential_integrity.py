"""
RevPilot AI — Referential Integrity and Foreign Key Checks (Phase 01)
Verifies DATA-QUALITY-LINEAGE-SPEC.md §3.4 (DQ-REF-001) and INV-TEN-001.
"""

from __future__ import annotations
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.modules.data_quality import (
    DataQualityValidator,
    DQ_REF_001,
)


@pytest.fixture
def validator():
    return DataQualityValidator()


@pytest.fixture
def tenant_parents():
    return {
        "customers": {"cus_alpha_0001", "cus_alpha_0002"},
        "orders": {"ord_alpha_0001", "ord_alpha_0002"},
    }


def test_orphan_customer_foreign_key_rejected(validator, tenant_parents):
    """DQ-REF-001: Non-existent customer_id fails referential integrity check."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "ord_orphan_01",
        "customer_id": "cus_alpha_9999",  # missing!
        "event_time": "2026-01-01T00:00:00Z",
        "total_cents": 1000,
        "currency": "USD",
    }
    res = validator.validate_record(
        record=payload,
        session_tenant_id=TenantId("tnt_alpha"),
        parent_entities=tenant_parents,
    )
    assert not res.is_valid
    assert res.rule_id == DQ_REF_001
    assert res.error_code == "ORPHAN_FOREIGN_KEY"


def test_orphan_order_foreign_key_rejected(validator, tenant_parents):
    """DQ-REF-001: Non-existent order_id in shipment/order_line fails referential integrity."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "shp_orphan_01",
        "order_id": "ord_alpha_9999",  # missing!
        "event_time": "2026-01-01T00:00:00Z",
    }
    res = validator.validate_record(
        record=payload,
        session_tenant_id=TenantId("tnt_alpha"),
        parent_entities=tenant_parents,
    )
    assert not res.is_valid
    assert res.rule_id == DQ_REF_001
    assert res.error_code == "ORPHAN_FOREIGN_KEY"


def test_cross_tenant_foreign_key_rejected(validator, tenant_parents):
    """INV-TEN-001 & DQ-REF-001: Foreign key referencing another tenant customer fails."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "ord_cross_fk_01",
        "customer_id": "cus_beta_0001",  # belongs to beta, not alpha!
        "event_time": "2026-01-01T00:00:00Z",
        "total_cents": 1000,
        "currency": "USD",
    }
    res = validator.validate_record(
        record=payload,
        session_tenant_id=TenantId("tnt_alpha"),
        parent_entities=tenant_parents,
    )
    assert not res.is_valid
    assert res.rule_id == DQ_REF_001
    assert res.error_code == "ORPHAN_FOREIGN_KEY"


def test_valid_parent_references_pass(validator, tenant_parents):
    """Records with valid tenant parent keys pass referential integrity."""
    payload = {
        "tenant_id": "tnt_alpha",
        "id": "ord_valid_01",
        "customer_id": "cus_alpha_0001",
        "event_time": "2026-01-01T00:00:00Z",
        "total_cents": 2500,
        "currency": "USD",
    }
    res = validator.validate_record(
        record=payload,
        session_tenant_id=TenantId("tnt_alpha"),
        parent_entities=tenant_parents,
    )
    assert res.is_valid
