"""
RevPilot AI — Tests: Single-Tenant Slice Recovery & Isolation Matrix
Specification: docs/24-sre/BACKUP-RESTORE-VALIDATION-RUNBOOK.md §8
Conforms to INV-TEN-001, AC-P08-005-02.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from revpilot.modules.operations.dr import (
    DisasterRecoveryRunner,
    RestoreIsolationBreachError,
    TenantDataExtractor,
)
from revpilot.shared.identifiers import TenantId


def test_single_tenant_slice_extraction_zero_cross_tenant_leakage(tmp_path: Path):
    """
    AC-P08-005-02 & INV-TEN-001:
    Extracting a single tenant partition slice filters 100% of data for the target tenant
    and leaks 0 rows from any other tenant into the extracted slice.
    """
    extractor = TenantDataExtractor()
    tenant_a = TenantId.generate()
    tenant_b = TenantId.generate()

    mock_db = {
        "tenants": [
            {"id": str(tenant_a), "name": "Tenant Alpha", "tier": "enterprise"},
            {"id": str(tenant_b), "name": "Tenant Beta", "tier": "growth"},
        ],
        "customer_orders": [
            {"order_id": "ord_101", "tenant_id": str(tenant_a), "amount": 150.0},
            {"order_id": "ord_102", "tenant_id": str(tenant_a), "amount": 250.0},
            {"order_id": "ord_201", "tenant_id": str(tenant_b), "amount": 999.0},
            {"order_id": "ord_202", "tenant_id": str(tenant_b), "amount": 50.0},
        ],
        "audit_records": [
            {"event_id": "aud_1", "tenant_id": str(tenant_a), "action": "LOGIN"},
            {"event_id": "aud_2", "tenant_id": str(tenant_b), "action": "MUTATE"},
        ],
    }

    output_file = tmp_path / "tenant_alpha_slice.json"
    manifest = extractor.extract_single_tenant_slice(
        source_data=mock_db,
        tenant_id=tenant_a,
        output_path=output_file,
    )

    assert manifest.tenant_id == str(tenant_a)
    assert manifest.total_records == 4  # 1 tenant record + 2 orders + 1 audit
    assert manifest.table_records["tenants"] == 1
    assert manifest.table_records["customer_orders"] == 2
    assert manifest.table_records["audit_records"] == 1

    # Read extracted slice content and assert ZERO records belonging to tenant_b
    slice_data = json.loads(output_file.read_text(encoding="utf-8"))

    for table_name, rows in slice_data.items():
        for row in rows:
            if table_name == "tenants":
                assert row["id"] == str(tenant_a)
                assert row["id"] != str(tenant_b)
            else:
                assert row["tenant_id"] == str(tenant_a)
                assert row["tenant_id"] != str(tenant_b)


def test_restored_database_isolation_breach_fails_closed(tmp_path: Path):
    """
    AC-P08-005-02 & INV-TEN-001:
    A cross-tenant leakage observed in restored database immediately raises
    RestoreIsolationBreachError (500) and fails the rehearsal.
    """
    runner = DisasterRecoveryRunner()
    fake_snap = tmp_path / "snap_corrupted.tar.gz"
    fake_snap.write_text("MOCK_SNAPSHOT_CONTENT", encoding="utf-8")

    with pytest.raises(RestoreIsolationBreachError) as exc_info:
        runner.execute_cold_restore(
            snapshot_path=fake_snap,
            verify_isolation=True,
            injected_leak=True,  # Simulate cross-tenant row leakage
        )

    assert exc_info.value.code == "RESTORE_ISOLATION_BREACH"
    assert exc_info.value.status_code == 500
    assert "cross-tenant leak detected" in exc_info.value.message

    # Audit event logged
    breach_events = [e for e in runner.audit_events if e["event_type"] == "DR_ISOLATION_CORRUPTION_DETECTED"]
    assert len(breach_events) == 1
