"""
RevPilot AI — Governed Approval and Safe Action Lifecycle Module
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md
"""

from revpilot.modules.approval.domain import (
    ApprovalStatus,
    ApprovalRequestRecord,
    ApprovalError,
)
from revpilot.modules.approval.digest import (
    ApprovalDigestHasher,
    ApprovalArtifact,
    compute_approval_digest,
    verify_approval_digest,
)
from revpilot.modules.approval.ports import (
    ApprovalRepository,
    InMemoryApprovalRepository,
)
from revpilot.modules.approval.service import ApprovalService

__all__ = [
    "ApprovalStatus",
    "ApprovalRequestRecord",
    "ApprovalError",
    "ApprovalDigestHasher",
    "ApprovalArtifact",
    "compute_approval_digest",
    "verify_approval_digest",
    "ApprovalRepository",
    "InMemoryApprovalRepository",
    "ApprovalService",
]
