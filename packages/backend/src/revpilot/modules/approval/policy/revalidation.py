"""
RevPilot AI — Six-Point Continuous Policy Revalidation Service
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 3, §4
Conforms to INV-ACT-001..004, INV-COST-001, INV-TEN-001, AC-008, and ADR-0002.
"""

from __future__ import annotations
from decimal import Decimal
from enum import Enum
from typing import Any

from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.results import Result, Success, Failure
from revpilot.modules.approval.domain import ApprovalRequestRecord, ApprovalError
from revpilot.modules.approval.policy.authority import AuthorityVerifier


class RevalidationCheckpoint(str, Enum):
    """The 6 continuous revalidation checkpoints across the action lifecycle."""
    PRE_CREATION = "PRE_CREATION"
    ON_SUBMISSION = "ON_SUBMISSION"
    ON_APPROVAL = "ON_APPROVAL"
    PRE_DRY_RUN = "PRE_DRY_RUN"
    PRE_DISPATCH = "PRE_DISPATCH"
    POST_RESULT = "POST_RESULT"


class PolicyViolationError(ApprovalError):
    """Error raised or encapsulated when a policy revalidation check fails."""

    def __init__(
        self,
        code: str = "ERR_POLICY_VIOLATION",
        message: str = "Policy revalidation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details)


class PolicyRevalidationService:
    """
    Evaluates policy, authorization, tenant boundaries, kill-switches,
    and budget across the 6 action lifecycle milestones (AC-008).
    """

    def __init__(self) -> None:
        self._authority_verifier = AuthorityVerifier()

    def verify_approver_authority(
        self, principal: PrincipalContext, cost_usd: Decimal, tier: int
    ) -> bool:
        """Verify principal approval authority tier and spend ceiling."""
        return self._authority_verifier.verify_approver_authority(
            principal=principal, cost_usd=cost_usd, required_tier=tier
        )

    def check_separation_of_duties(
        self, proposer_id: str, approver_id: str, cost_usd: Decimal
    ) -> bool:
        """Check dual-authorization / proposer separation of duties."""
        return self._authority_verifier.check_separation_of_duties(
            proposer_id=proposer_id, approver_id=approver_id, cost_usd=cost_usd
        )

    async def revalidate(
        self,
        ctx: TenantContext,
        approval: ApprovalRequestRecord,
        checkpoint: RevalidationCheckpoint,
        current_policy_digest: str | None = None,
        is_kill_switch_active: bool = False,
        budget_remaining_usd: Decimal | None = None,
        current_time: UtcDateTime | None = None,
    ) -> Result[None, PolicyViolationError]:
        """
        Execute continuous policy revalidation at the specified checkpoint (AC-008).
        Fail-closed: Returns Failure on any constraint mismatch.
        """
        now = current_time or UtcDateTime.now()

        # 1. Tenant Boundary Validation (INV-TEN-001)
        if str(ctx.tenant_id) != str(approval.tenant_id):
            return Failure(
                PolicyViolationError(
                    code="ERR_TENANT_MISMATCH",
                    message=f"Tenant mismatch at checkpoint {checkpoint}: context '{ctx.tenant_id}' != record '{approval.tenant_id}'",
                    details={"context_tenant": str(ctx.tenant_id), "record_tenant": str(approval.tenant_id)},
                )
            )

        # 2. Multi-Tier Safety Kill Switch (INV-SEC-003)
        if is_kill_switch_active:
            return Failure(
                PolicyViolationError(
                    code="ERR_KILL_SWITCH_ACTIVE",
                    message=f"Action execution halted by active safety kill-switch at {checkpoint}",
                    details={"checkpoint": checkpoint.value, "tenant_id": str(ctx.tenant_id)},
                )
            )

        # 3. Expiration Check (24h TTL)
        if now >= approval.expiry_time:
            return Failure(
                PolicyViolationError(
                    code="ERR_APPROVAL_EXPIRED",
                    message=f"Approval request {approval.approval_id} expired prior to checkpoint {checkpoint}",
                    details={"checkpoint": checkpoint.value, "expiry_time": approval.expiry_time.isoformat()},
                )
            )

        # 4. Policy Freshness & Anti-Tamper Check (AC-008)
        if current_policy_digest is not None and current_policy_digest != approval.policy_digest:
            return Failure(
                PolicyViolationError(
                    code="ERR_POLICY_STALE",
                    message=f"Policy rules changed since approval creation; revalidation failed at {checkpoint}",
                    details={
                        "checkpoint": checkpoint.value,
                        "current_policy_digest": current_policy_digest,
                        "record_policy_digest": approval.policy_digest,
                    },
                )
            )

        # 5. Monetary Budget Sufficiency (INV-COST-001)
        if budget_remaining_usd is not None and budget_remaining_usd < approval.estimated_cost_usd:
            return Failure(
                PolicyViolationError(
                    code="ERR_BUDGET_EXCEEDED",
                    message=f"Insufficient remaining budget at checkpoint {checkpoint}: available {budget_remaining_usd} < required {approval.estimated_cost_usd}",
                    details={
                        "checkpoint": checkpoint.value,
                        "budget_remaining_usd": str(budget_remaining_usd),
                        "estimated_cost_usd": str(approval.estimated_cost_usd),
                    },
                )
            )

        return Success(None)
