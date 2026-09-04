"""
RevPilot AI — Release Governance, Canary Rollout, and Multi-Tier Rollback Module
Specification: docs/30-deployment/RELEASE-CANARY-ROLLBACK-SPEC.md
"""

from revpilot.modules.operations.release.canary import (
    CanaryController,
    CanaryHealthVerdict,
    CanaryStage,
)
from revpilot.modules.operations.release.manager import (
    CanaryHealthFailedError,
    IncompleteTierManifestError,
    ReleaseManifest,
    ReleaseManifestValidator,
    ReleaseRegistry,
    RollbackExecutionError,
    TIER_DEFINITIONS,
)
from revpilot.modules.operations.release.rollback import (
    RollbackCoordinator,
    RollbackStep,
    RollbackSummary,
)

__all__ = [
    "CanaryController",
    "CanaryHealthFailedError",
    "CanaryHealthVerdict",
    "CanaryStage",
    "IncompleteTierManifestError",
    "ReleaseManifest",
    "ReleaseManifestValidator",
    "ReleaseRegistry",
    "RollbackCoordinator",
    "RollbackExecutionError",
    "RollbackStep",
    "RollbackSummary",
    "TIER_DEFINITIONS",
]
