"""
RevPilot AI — Governed Approval Lifecycle and State Machine Service
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1, §3.1
Conforms to INV-ACT-001..004, INV-IAM-001..002, INV-TEN-001..003, AC-008, and ADR-0003.
"""

from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
from typing import Any, Literal

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.approval.domain import (
    ApprovalRequestRecord,
    ApprovalStatus,
    ApprovalError,
)
from revpilot.modules.approval.digest import ApprovalDigestHasher
from revpilot.modules.approval.ports import ApprovalRepository


class ApprovalService:
    """
    Manages the human-in-the-loop approval lifecycle, cryptographic tamper-proofing,
    and state transitions for high-impact business actions.
    """

    def __init__(self, repository: ApprovalRepository) -> None:
        self._repo = repository

    async def create_request(
        self,
        tenant_id: TenantId,
        decision_id: UUIDv7,
        action_type: str,
        target_customer_id: str,
        target_entity_refs: list[str],
        action_payload: dict[str, Any],
        estimated_cost_usd: Decimal,
        risk_tier: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW",
        decision_digest: str = "",
        policy_rules: Any = "v1.0",
        ttl_hours: int = 24,
        investigation_id: UUIDv7 | None = None,
        correlation_id: UUIDv7 | None = None,
        causation_id: UUIDv7 | None = None,
    ) -> ApprovalRequestRecord:
        """
        Create a new governed approval request sealed with cryptographic SHA-256 digests.
        """
        if not str(tenant_id).strip():
            raise ApprovalError(code="ERR_TENANT_MISMATCH", message="Tenant ID must not be empty")
        if not target_customer_id.strip():
            raise ApprovalError(code="ERR_INVALID_REQUEST", message="Target customer ID must not be empty")

        now = UtcDateTime.now()
        approval_id = UUIDv7.generate()
        corr_id = correlation_id or approval_id
        caus_id = causation_id or decision_id

        # Determine required approval tier based on risk and financial threshold
        required_tier = self._compute_required_tier(risk_tier, estimated_cost_usd)

        # Cryptographic sealing (INV-ACT-002, AC-008)
        payload_digest = ApprovalDigestHasher.compute_payload_digest(
            action_type=action_type,
            target_entities=target_entity_refs,
            payload=action_payload,
            cost_usd=estimated_cost_usd,
        )
        policy_digest = ApprovalDigestHasher.compute_policy_digest(policy_rules)

        # Expiry time (24h TTL)
        expiry_time = UtcDateTime.from_datetime(now.value + timedelta(hours=ttl_hours))

        record = ApprovalRequestRecord(
            approval_id=approval_id,
            tenant_id=tenant_id,
            decision_id=decision_id,
            investigation_id=investigation_id,
            action_type=action_type,
            action_version="1.0.0",
            target_customer_id=target_customer_id,
            target_entity_refs=target_entity_refs,
            action_payload=action_payload,
            payload_digest=payload_digest,
            policy_digest=policy_digest,
            estimated_cost_usd=estimated_cost_usd,
            reserved_budget_usd=estimated_cost_usd,
            risk_tier=risk_tier,
            required_approval_tier=required_tier,
            expiry_time=expiry_time,
            status=ApprovalStatus.PENDING,
            decision_digest=decision_digest,
            correlation_id=corr_id,
            causation_id=caus_id,
            created_at=now,
        )

        await self._repo.save(record)
        return record

    async def grant_approval(
        self,
        tenant_id: TenantId,
        approval_id: UUIDv7,
        approver_principal_id: str,
        approver_tier: int,
        expected_digest: str,
        is_human: bool = True,
        current_time: UtcDateTime | None = None,
    ) -> ApprovalRequestRecord:
        """
        Authorize execution of an approval request with human verification and digest check.
        """
        now = current_time or UtcDateTime.now()

        # 1. Tenant boundary check
        record = await self._repo.get(tenant_id, approval_id)
        if record is None:
            raise ApprovalError(
                code="ERR_TENANT_MISMATCH",
                message=f"Approval request {approval_id} not found for tenant {tenant_id}",
            )

        # 2. Strict Human-in-the-Loop Authority (INV-ACT-003)
        if not is_human:
            raise ApprovalError(
                code="ERR_AGENT_SELF_APPROVAL",
                message="AI agents, automated planners, and service accounts are strictly prohibited from approving actions",
            )

        # 2b. Separation of Duties (SoD) Invariant
        if record.requester_principal_id and approver_principal_id == record.requester_principal_id:
            raise ApprovalError(
                code="ERR_SEPARATION_OF_DUTIES_VIOLATION",
                message="Separation of Duties violation: requester cannot approve their own action request",
            )

        # 3. State machine transitions & Replay Protection
        if record.status == ApprovalStatus.APPROVED:
            raise ApprovalError(
                code="ERR_ALREADY_USED",
                message="Approval request has already been approved and cannot be reused (replay prevented)",
            )
        if record.status == ApprovalStatus.EXPIRED:
            raise ApprovalError(
                code="ERR_APPROVAL_EXPIRED",
                message="Approval request has expired and cannot be approved",
            )
        if record.status == ApprovalStatus.REVOKED:
            raise ApprovalError(
                code="ERR_APPROVAL_REVOKED",
                message="Approval request was revoked and cannot be approved",
            )
        if record.status == ApprovalStatus.SUPERSEDED:
            raise ApprovalError(
                code="ERR_INVALID_APPROVAL_STATE",
                message="Approval request was superseded by an amendment and cannot be approved",
            )
        if record.status != ApprovalStatus.PENDING:
            raise ApprovalError(
                code="ERR_INVALID_APPROVAL_STATE",
                message=f"Cannot approve request in status {record.status}",
            )

        # 4. Expiration check (fail-closed)
        if now >= record.expiry_time:
            expired_rec = record.model_copy(update={"status": ApprovalStatus.EXPIRED})
            await self._repo.update(expired_rec)
            raise ApprovalError(
                code="ERR_APPROVAL_EXPIRED",
                message="Approval request has expired past its 24h TTL",
            )

        # 5. Approver tier authority
        if approver_tier < record.required_approval_tier:
            raise ApprovalError(
                code="ERR_INSUFFICIENT_APPROVAL_TIER",
                message=f"Approver tier {approver_tier} below required tier {record.required_approval_tier}",
            )

        # 6. Cryptographic payload digest verification (INV-ACT-002, AC-008)
        current_digest = ApprovalDigestHasher.compute_payload_digest(
            action_type=record.action_type,
            target_entities=record.target_entity_refs,
            payload=record.action_payload,
            cost_usd=record.estimated_cost_usd,
        )

        if current_digest != expected_digest or current_digest != record.payload_digest:
            raise ApprovalError(
                code="ERR_APPROVAL_DIGEST_MISMATCH",
                message="Payload tampering detected: digest does not match the immutable signed approval request",
                details={
                    "expected_digest": expected_digest,
                    "record_digest": record.payload_digest,
                    "current_digest": current_digest,
                },
            )

        # 7. Update to APPROVED
        approved_rec = record.model_copy(
            update={
                "status": ApprovalStatus.APPROVED,
                "approver_principal_id": approver_principal_id,
                "approval_timestamp": now,
            }
        )
        await self._repo.update(approved_rec)
        return approved_rec

    async def reject_request(
        self,
        tenant_id: TenantId,
        approval_id: UUIDv7,
        approver_principal_id: str,
        rejection_reason: str,
    ) -> ApprovalRequestRecord:
        """Reject a pending approval request."""
        record = await self._repo.get(tenant_id, approval_id)
        if record is None:
            raise ApprovalError(code="ERR_TENANT_MISMATCH", message="Approval request not found")
        if record.status != ApprovalStatus.PENDING:
            raise ApprovalError(
                code="ERR_INVALID_APPROVAL_STATE",
                message=f"Cannot reject request in status {record.status}",
            )

        rejected_rec = record.model_copy(
            update={
                "status": ApprovalStatus.REJECTED,
                "approver_principal_id": approver_principal_id,
                "rejection_reason": rejection_reason,
            }
        )
        await self._repo.update(rejected_rec)
        return rejected_rec

    async def revoke_approval(
        self,
        tenant_id: TenantId,
        approval_id: UUIDv7,
        revoker_principal_id: str,
        revocation_reason: str,
    ) -> ApprovalRequestRecord:
        """Revoke a pending or approved request before physical execution."""
        record = await self._repo.get(tenant_id, approval_id)
        if record is None:
            raise ApprovalError(code="ERR_TENANT_MISMATCH", message="Approval request not found")
        if record.status in (ApprovalStatus.EXECUTING, ApprovalStatus.COMPLETED):
            raise ApprovalError(
                code="ERR_INVALID_APPROVAL_STATE",
                message=f"Cannot revoke request already in execution state {record.status}",
            )

        revoked_rec = record.model_copy(
            update={
                "status": ApprovalStatus.REVOKED,
                "revocation_reason": revocation_reason,
            }
        )
        await self._repo.update(revoked_rec)
        return revoked_rec

    async def amend_request(
        self,
        tenant_id: TenantId,
        approval_id: UUIDv7,
        modifier_principal_id: str,
        new_payload: dict[str, Any],
        new_cost_usd: Decimal | None = None,
        new_target_entities: list[str] | None = None,
    ) -> tuple[ApprovalRequestRecord, ApprovalRequestRecord]:
        """
        Amend an existing request. Marks original as SUPERSEDED and generates
        a fresh PENDING request with recomputed digest requiring fresh human approval.
        """
        original = await self._repo.get(tenant_id, approval_id)
        if original is None:
            raise ApprovalError(code="ERR_TENANT_MISMATCH", message="Approval request not found")
        if original.status in (ApprovalStatus.EXECUTING, ApprovalStatus.COMPLETED, ApprovalStatus.SUPERSEDED):
            raise ApprovalError(
                code="ERR_INVALID_APPROVAL_STATE",
                message=f"Cannot amend request in status {original.status}",
            )

        cost = new_cost_usd if new_cost_usd is not None else original.estimated_cost_usd
        targets = new_target_entities if new_target_entities is not None else original.target_entity_refs

        now = UtcDateTime.now()
        new_id = UUIDv7.generate()

        # Supersede original
        superseded_orig = original.model_copy(
            update={
                "status": ApprovalStatus.SUPERSEDED,
                "superseded_by": new_id,
            }
        )
        await self._repo.update(superseded_orig)

        # Create new request
        new_payload_digest = ApprovalDigestHasher.compute_payload_digest(
            action_type=original.action_type,
            target_entities=targets,
            payload=new_payload,
            cost_usd=cost,
        )
        required_tier = self._compute_required_tier(original.risk_tier, cost)

        new_record = ApprovalRequestRecord(
            approval_id=new_id,
            tenant_id=tenant_id,
            decision_id=original.decision_id,
            investigation_id=original.investigation_id,
            action_type=original.action_type,
            action_version=original.action_version,
            target_customer_id=original.target_customer_id,
            target_entity_refs=targets,
            action_payload=new_payload,
            payload_digest=new_payload_digest,
            policy_digest=original.policy_digest,
            estimated_cost_usd=cost,
            reserved_budget_usd=cost,
            risk_tier=original.risk_tier,
            required_approval_tier=required_tier,
            expiry_time=UtcDateTime.from_datetime(now.value + timedelta(hours=24)),
            status=ApprovalStatus.PENDING,
            decision_digest=original.decision_digest,
            correlation_id=original.correlation_id,
            causation_id=original.approval_id,  # Points to superseded original
            created_at=now,
        )
        await self._repo.save(new_record)
        return superseded_orig, new_record

    async def expire_stale_requests(
        self, tenant_id: TenantId, current_time: UtcDateTime
    ) -> int:
        """Scan and transition expired requests to EXPIRED."""
        pending = await self._repo.list_pending(tenant_id)
        expired_count = 0
        for rec in pending:
            if current_time >= rec.expiry_time:
                expired_rec = rec.model_copy(update={"status": ApprovalStatus.EXPIRED})
                await self._repo.update(expired_rec)
                expired_count += 1
        return expired_count

    @staticmethod
    def _compute_required_tier(risk_tier: str, cost_usd: Decimal) -> int:
        if risk_tier in ("HIGH", "CRITICAL") or cost_usd > Decimal("1000.00"):
            return 3  # VP / Executive
        if risk_tier == "MEDIUM" or cost_usd > Decimal("250.00"):
            return 2  # Director
        return 1  # Operations
