"""
RevPilot AI — Tests: Cold Restore Rehearsal & Continuous WAL Verification
Specification: docs/24-sre/DR-PLAN.md §1, §2, docs/24-sre/BACKUP-RESTORE-VALIDATION-RUNBOOK.md §6
Conforms to NFR-REC-001, INV-REL-001, TC-P08-019, AC-P08-005-01.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from revpilot.modules.operations.dr import (
    DisasterRecoveryRunner,
    RecoveryRehearsalResult,
    RestoreTimeoutError,
    WalBlock,
    WalGapDetectedError,
    WalVerifier,
)
from revpilot.shared.temporal import UtcDateTime


def _create_mock_wal_blocks(
    start_seq: int = 100,
    count: int = 5,
    base_time: UtcDateTime | None = None,
    interval_seconds: int = 60,
    introduce_gap_at: int | None = None,
) -> list[WalBlock]:
    t0 = base_time or UtcDateTime.now()
    blocks = []
    current_seq = start_seq
    for i in range(count):
        if introduce_gap_at is not None and i == introduce_gap_at:
            current_seq += 2  # skip a sequence number
        else:
            current_seq += 1

        b_time = UtcDateTime(t0.value + timedelta(seconds=i * interval_seconds))
        blocks.append(
            WalBlock(
                sequence_id=current_seq,
                start_lsn=f"0/0{current_seq:06X}",
                end_lsn=f"0/0{(current_seq + 1):06X}",
                timestamp=b_time,
                sha256_checksum=f"wal_sha256_{current_seq}",
                size_bytes=16777216,
            )
        )
    return blocks


def test_cold_restore_rehearsal_meets_rto_and_rpo_sla(tmp_path: Path):
    """
    AC-P08-005-01 & TC-P08-019:
    Cold restore rehearsal in staging achieves measured RTO <= 30m (1800s)
    and measured RPO <= 5m (300s).
    """
    runner = DisasterRecoveryRunner()
    fake_snap = tmp_path / "snap_prod_20260904_0200.tar.gz"
    fake_snap.write_text("MOCK_SNAPSHOT_CONTENT", encoding="utf-8")

    now = UtcDateTime.now()
    # Continuous WAL blocks flush every 60s, last block 72s before target
    wal_blocks = _create_mock_wal_blocks(
        start_seq=500,
        count=6,
        base_time=UtcDateTime(now.value - timedelta(seconds=372)),
        interval_seconds=60,
    )

    result: RecoveryRehearsalResult = runner.execute_cold_restore(
        snapshot_path=fake_snap,
        target_time=now,
        wal_blocks=wal_blocks,
        simulated_rto_seconds=750.0,  # 12.5 minutes <= 30m
    )

    assert result.status == "PASS"
    assert result.measured_rto_seconds == 750.0
    assert result.measured_rto_seconds <= 1800.0  # RTO <= 30m SLA
    assert result.measured_rpo_seconds <= 300.0   # RPO <= 5m SLA
    assert result.audit_chain_verified is True
    assert result.isolation_suite_passed is True

    # Audit event logged
    assert len(runner.audit_events) >= 1
    assert runner.audit_events[-1]["event_type"] == "DR_COLD_RESTORE_COMPLETED"


def test_cold_restore_rto_timeout_breach_fails_closed(tmp_path: Path):
    """
    RTO exceeding 30 minutes (1800 seconds) raises RestoreTimeoutError (500).
    """
    runner = DisasterRecoveryRunner()
    fake_snap = tmp_path / "snap_slow.tar.gz"
    fake_snap.write_text("MOCK_SNAPSHOT_CONTENT", encoding="utf-8")

    # 1950 seconds = 32.5 minutes > 30 minutes SLA
    with pytest.raises(RestoreTimeoutError) as exc_info:
        runner.execute_cold_restore(
            snapshot_path=fake_snap,
            simulated_rto_seconds=1950.0,
            simulated_rpo_seconds=60.0,
        )

    assert exc_info.value.code == "RESTORE_TIMEOUT"
    assert exc_info.value.status_code == 500
    assert exc_info.value.details["measured_rto_seconds"] == 1950.0


def test_cold_restore_rpo_breach_fails_closed(tmp_path: Path):
    """
    RPO exceeding 5 minutes (300 seconds) raises RestoreTimeoutError (500).
    """
    runner = DisasterRecoveryRunner()
    fake_snap = tmp_path / "snap_lagging_wal.tar.gz"
    fake_snap.write_text("MOCK_SNAPSHOT_CONTENT", encoding="utf-8")

    # 420 seconds = 7 minutes > 5 minutes SLA
    with pytest.raises(RestoreTimeoutError) as exc_info:
        runner.execute_cold_restore(
            snapshot_path=fake_snap,
            simulated_rto_seconds=600.0,
            simulated_rpo_seconds=420.0,
        )

    assert exc_info.value.code == "RESTORE_TIMEOUT"
    assert exc_info.value.status_code == 500


def test_wal_stream_gap_detection_fails_closed():
    """
    Missing WAL archive block raises WalGapDetectedError (422) indicating data loss.
    """
    verifier = WalVerifier()
    now = UtcDateTime.now()
    # Gap introduced at index 2 (skips sequence 103)
    gapped_blocks = _create_mock_wal_blocks(
        start_seq=100,
        count=5,
        base_time=now,
        introduce_gap_at=2,
    )

    with pytest.raises(WalGapDetectedError) as exc_info:
        verifier.verify_wal_stream(gapped_blocks, target_time=now)

    assert exc_info.value.code == "WAL_GAP_DETECTED"
    assert exc_info.value.status_code == 422
    assert "gaps" in exc_info.value.details
    assert len(exc_info.value.details["gaps"]) > 0


def test_8_step_restoration_dependency_order(tmp_path: Path):
    """
    Restoration must execute the exact 8 dependency steps in order (§2.3).
    """
    runner = DisasterRecoveryRunner()
    fake_snap = tmp_path / "snap_order.tar.gz"
    fake_snap.write_text("MOCK_SNAPSHOT_CONTENT", encoding="utf-8")

    result = runner.execute_cold_restore(snapshot_path=fake_snap)

    assert len(result.restoration_steps) == 8
    assert "1. KMS & Workload Identity" in result.restoration_steps[0]
    assert "2. PostgreSQL Primary Database Restore" in result.restoration_steps[1]
    assert "3. Audit Ledger Integrity" in result.restoration_steps[2]
    assert "4. IAM & Tenant Context" in result.restoration_steps[3]
    assert "5. Object Storage" in result.restoration_steps[4]
    assert "6. Temporal Workflow" in result.restoration_steps[5]
    assert "7. Vector embeddings projection rebuilt" in result.restoration_steps[6]
    assert "8. API Gateway & Ingress" in result.restoration_steps[7]


def test_disposable_projections_rebuilding_protocol(tmp_path: Path):
    """
    Vector DB and Cache projections are disposable projections rebuilt on restore (§2.2).
    """
    runner = DisasterRecoveryRunner()
    fake_snap = tmp_path / "snap_proj.tar.gz"
    fake_snap.write_text("MOCK_SNAPSHOT_CONTENT", encoding="utf-8")

    result = runner.execute_cold_restore(snapshot_path=fake_snap)

    assert "vector_embeddings_index" in result.rebuilt_projections
    assert "redis_session_cache" in result.rebuilt_projections
    assert "search_catalog_bm25" in result.rebuilt_projections
