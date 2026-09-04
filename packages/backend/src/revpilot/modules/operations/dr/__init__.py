"""
RevPilot AI — Disaster Recovery & Backup Validation Module
Specification: docs/24-sre/DR-PLAN.md, docs/24-sre/BACKUP-RESTORE-VALIDATION-RUNBOOK.md
"""

from revpilot.modules.operations.dr.runner import (
    DisasterRecoveryRunner,
    RecoveryRehearsalResult,
    RestoreIsolationBreachError,
    RestoreTimeoutError,
)
from revpilot.modules.operations.dr.tenant_extract import (
    TenantDataExtractor,
    TenantSliceManifest,
)
from revpilot.modules.operations.dr.wal_verifier import (
    WalBlock,
    WalGapDetectedError,
    WalVerificationReport,
    WalVerifier,
)

__all__ = [
    "DisasterRecoveryRunner",
    "RecoveryRehearsalResult",
    "RestoreIsolationBreachError",
    "RestoreTimeoutError",
    "TenantDataExtractor",
    "TenantSliceManifest",
    "WalBlock",
    "WalGapDetectedError",
    "WalVerificationReport",
    "WalVerifier",
]
