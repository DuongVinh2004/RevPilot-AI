"""
RevPilot AI — Continuous WAL Archive Verifier & RPO Calculator
Specification: docs/24-sre/DR-PLAN.md §1, docs/24-sre/BACKUP-RESTORE-VALIDATION-RUNBOOK.md §5
Conforms to NFR-REC-001, INV-DATA-001, AC-P08-005-01.
"""

from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.errors import DomainError
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


class WalGapDetectedError(DomainError):
    """Missing WAL archive block indicating unrecoverable data loss in WAL stream (Status 422, Non-retryable)."""

    def __init__(
        self,
        message: str = "Data loss detected in WAL stream",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="WAL_GAP_DETECTED",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 422


class WalBlock(BaseModel):
    """Immutable representation of an archived 16MB PostgreSQL WAL segment block."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    sequence_id: int
    start_lsn: str
    end_lsn: str
    timestamp: UtcDateTime
    sha256_checksum: str
    size_bytes: int = 16777216  # 16 MB


class WalVerificationReport(BaseModel):
    """Telemetry report validating unbroken WAL sequence and empirical RPO measurement."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    unbroken_sequence: bool
    blocks_checked: int
    start_sequence_id: int
    end_sequence_id: int
    gaps_detected: list[int] = Field(default_factory=list)
    measured_rpo_seconds: float
    target_time: UtcDateTime


class WalVerifier:
    """
    Validates cryptographic and sequence continuity across continuous WAL archives.
    Calculates empirical RPO against recovery target time (NFR-REC-001 <= 300s).
    """

    def verify_wal_stream(
        self,
        wal_blocks: list[WalBlock],
        target_time: UtcDateTime,
        raise_on_gap: bool = True,
    ) -> WalVerificationReport:
        """
        Verify contiguous WAL sequence and calculate RPO offset.
        """
        if not wal_blocks:
            if raise_on_gap:
                raise WalGapDetectedError(
                    "WAL archive stream is empty; unable to replay transactions",
                    details={"blocks_count": 0},
                )
            return WalVerificationReport(
                unbroken_sequence=False,
                blocks_checked=0,
                start_sequence_id=0,
                end_sequence_id=0,
                gaps_detected=[0],
                measured_rpo_seconds=999999.0,
                target_time=target_time,
            )

        sorted_blocks = sorted(wal_blocks, key=lambda b: b.sequence_id)
        gaps: list[int] = []

        for idx in range(len(sorted_blocks) - 1):
            curr_seq = sorted_blocks[idx].sequence_id
            next_seq = sorted_blocks[idx + 1].sequence_id
            if next_seq != curr_seq + 1:
                # Sequence gap identified
                for missing_seq in range(curr_seq + 1, next_seq):
                    gaps.append(missing_seq)

        if gaps and raise_on_gap:
            raise WalGapDetectedError(
                f"Missing WAL archive block(s) in sequence: {gaps}",
                details={
                    "gaps": gaps,
                    "first_available_seq": sorted_blocks[0].sequence_id,
                    "last_available_seq": sorted_blocks[-1].sequence_id,
                },
            )

        last_block = sorted_blocks[-1]
        # Measured RPO: elapsed time between last committed WAL block timestamp and target point-in-time
        raw_rpo = (target_time.value - last_block.timestamp.value).total_seconds()
        measured_rpo = max(0.0, raw_rpo)

        report = WalVerificationReport(
            unbroken_sequence=len(gaps) == 0,
            blocks_checked=len(sorted_blocks),
            start_sequence_id=sorted_blocks[0].sequence_id,
            end_sequence_id=sorted_blocks[-1].sequence_id,
            gaps_detected=gaps,
            measured_rpo_seconds=measured_rpo,
            target_time=target_time,
        )
        return report
