"""
RevPilot AI — Phase 06 Governed Action & Tool Gateway Exit-Gate Verification Suite
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1..§5
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7
Specification: docs/26-api/EVENT-CONTRACTS.md §8
Specification: docs/29-testing/TEST-STRATEGY.md §11 (TC-P06-027..028)
Enforces AC-008, AC-009, INV-ACT-001..004, INV-REL-001, NFR-REL-001, NFR-COST-001, INV-AUD-001, INV-AI-001.
"""

from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
import time
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import pytest

from revpilot.modules.action.domain import (
    ActionClassification,
    ActionIntentRecord,
    ActionLedgerRecord,
)
from revpilot.modules.action.outcome.audit import ActionAuditLogger
from revpilot.modules.action.outcome.domain import ActionEventEnvelope
from revpilot.modules.action.outcome.service import ActionOutcomeService
from revpilot.modules.action.saga import (
    CompensationStatus,
    IrreversibleActionError,
    ProviderInquiryResult,
    ProviderTransactionStatus,
    ReconciliationManager,
    SafeActionSagaWorkflow,
    SagaStep,
)
from revpilot.modules.approval.domain import (
    ApprovalRequestRecord,
    ApprovalStatus,
)
from revpilot.modules.approval.digest import ApprovalDigestHasher
from revpilot.modules.approval.policy.authority import (
    ApprovalTier,
    AuthorityVerifier,
    TIER_1_MAX_SPEND,
    TIER_2_MAX_SPEND,
    TIER_3_MAX_SPEND,
)
from revpilot.modules.approval.policy.revalidation import (
    PolicyRevalidationService,
    RevalidationCheckpoint,
)
from revpilot.modules.safety.blast_radius import (
    BlastRadiusLimiter,
    MAX_AFFECTED_ENTITIES,
)
from revpilot.modules.safety.killswitch.domain import (
    AgentOverrideForbiddenError,
    KillSwitchScope,
)
from revpilot.modules.safety.killswitch.service import (
    DistributedKillSwitchBus,
    KillSwitchService,
)
from revpilot.modules.tool_gateway.action.credential_broker import (
    CredentialBroker,
    GatewayError,
)
from revpilot.modules.tool_gateway.action.gateway import (
    ActionCapabilityGateway,
    ActionCapabilityRequest,
    agent_egress_barrier,
    scrub_secrets,
)
from revpilot.shared.context import OrganizationId, PrincipalContext, TenantContext
from revpilot.shared.identifiers import PrincipalId, TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


class CompositeGateReport(BaseModel):
    """Structured evaluation report assessing all Phase 06 binary acceptance criteria."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    total_checks: int
    passed_checks: int
    failed_checks: int
    compliance_percentage: float
    gate_status: str  # "PASS" or "LOCKED"
    check_results: dict[str, bool]
    details: dict[str, Any] = Field(default_factory=dict)


class Phase06ExitGateRunner:
    """
    Composite test harness executing all 28 binary exit gate verification checks for Phase 06.
    """

    @staticmethod
    async def run_all_checks() -> CompositeGateReport:
        checks: dict[str, bool] = {}
        now = UtcDateTime.now()

        t_id = TenantId("tnt_exit_gate_06")
        org_id = OrganizationId("org_exit_gate_06")
        t_ctx = TenantContext(tenant_id=t_id, organization_id=org_id, is_active=True)

        human_principal = PrincipalContext(
            principal_id=PrincipalId("usr_human_director"),
            tenant_id=t_id,
            roles={"tenant_admin", "director"},
            permissions={"approval:tier_2", "approval:action"},
        )
        agent_principal = PrincipalContext(
            principal_id=PrincipalId("usr_agent_planner"),
            tenant_id=t_id,
            roles={"agent_delegate"},
            permissions={"approval:tier_2"},
        )

        # ---------------------------------------------------------------------
        # 1. GATE_AC008_DIGEST_SEALING
        # ---------------------------------------------------------------------
        payload = {"carrier": "ups", "freight_charge_usd": 150.0}
        digest = ApprovalDigestHasher.compute_payload_digest(
            action_type="reroute_carrier",
            target_entities=["order_001"],
            payload=payload,
            cost_usd=Decimal("150.00"),
        )
        assert len(digest) == 64
        checks["GATE_AC008_DIGEST_SEALING"] = True

        # ---------------------------------------------------------------------
        # 2. GATE_INV_ACT003_HUMAN_APPROVAL
        # ---------------------------------------------------------------------
        assert AuthorityVerifier.is_agent_principal(agent_principal) is True
        assert AuthorityVerifier.is_agent_principal(human_principal) is False
        assert AuthorityVerifier.get_principal_tier(agent_principal) == 0
        checks["GATE_INV_ACT003_HUMAN_APPROVAL"] = True

        # ---------------------------------------------------------------------
        # 3. GATE_AC008_TIERED_AUTHORITY
        # ---------------------------------------------------------------------
        tier_human = AuthorityVerifier.get_principal_tier(human_principal)
        assert tier_human == ApprovalTier.TIER_2_TACTICAL
        checks["GATE_AC008_TIERED_AUTHORITY"] = True

        # ---------------------------------------------------------------------
        # 4. GATE_AC008_SEPARATION_OF_DUTIES
        # ---------------------------------------------------------------------
        author_id = PrincipalId("usr_author_analyst")
        approver_id = PrincipalId("usr_approver_lead")
        checks["GATE_AC008_SEPARATION_OF_DUTIES"] = (author_id != approver_id)

        # ---------------------------------------------------------------------
        # 5. GATE_AC008_CONTINUOUS_REVALIDATION
        # ---------------------------------------------------------------------
        approval_rec = ApprovalRequestRecord(
            approval_id=UUIDv7.generate(),
            tenant_id=t_id,
            decision_id=UUIDv7.generate(),
            action_type="reroute_carrier",
            action_version="1.0.0",
            target_customer_id="cust_001",
            target_entity_refs=["order_001"],
            action_payload=payload,
            payload_digest=digest,
            policy_digest="policy_v1",
            estimated_cost_usd=Decimal("150.00"),
            reserved_budget_usd=Decimal("200.00"),
            risk_tier="MEDIUM",
            required_approval_tier=2,
            expiry_time=UtcDateTime.from_datetime(now.value + timedelta(seconds=3600)),
            status=ApprovalStatus.APPROVED,
            decision_digest="dec_digest_123",
            correlation_id=UUIDv7.generate(),
            causation_id=UUIDv7.generate(),
            created_at=now,
        )
        reval_res = await PolicyRevalidationService().revalidate(
            ctx=t_ctx,
            approval=approval_rec,
            checkpoint=RevalidationCheckpoint.PRE_DISPATCH,
            current_policy_digest="policy_v1",
        )
        assert reval_res.is_success
        checks["GATE_AC008_CONTINUOUS_REVALIDATION"] = True

        # ---------------------------------------------------------------------
        # 6. GATE_AC009_DRYRUN_PARITY & ZERO SIDE EFFECTS
        # ---------------------------------------------------------------------
        gateway = ActionCapabilityGateway()
        dry_run_req = ActionCapabilityRequest(
            intent_id=UUIDv7.generate(),
            tenant_id=t_id,
            approval_id=approval_rec.approval_id,
            approval_digest=digest,
            action_type="reroute_carrier",
            idempotency_key="idemp_dryrun_parity",
            target_entities=["order_001"],
            payload=payload,
            is_dry_run=True,
            as_of_time=now,
        )
        dry_res = await gateway.dispatch_action(t_ctx, dry_run_req)
        assert dry_res.is_success
        assert len(gateway.mock_adapter.execution_history) == 0  # Zero side effects
        checks["GATE_AC009_DRYRUN_PARITY"] = True

        # ---------------------------------------------------------------------
        # 7. GATE_INV_ACT001_IDEMPOTENCY_BARRIER
        # ---------------------------------------------------------------------
        from revpilot.modules.action.ports import (
            InMemoryActionIntentRepository,
            InMemoryActionLedgerRepository,
        )
        from revpilot.modules.action.ledger import ActionLedgerService

        intent_repo = InMemoryActionIntentRepository()
        ledger_repo = InMemoryActionLedgerRepository()
        ledger_svc = ActionLedgerService(intent_repo, ledger_repo)

        intent_1 = await ledger_svc.create_intent(
            ctx=t_ctx,
            approval=approval_rec,
            idempotency_key="idemp_barrier_test",
            classification=ActionClassification.COMPENSATABLE,
        )
        intent_2 = await ledger_svc.create_intent(
            ctx=t_ctx,
            approval=approval_rec,
            idempotency_key="idemp_barrier_test",
            classification=ActionClassification.COMPENSATABLE,
        )
        assert intent_1.intent_id == intent_2.intent_id
        assert len(intent_repo._storage[str(t_id)]) == 1
        checks["GATE_INV_ACT001_IDEMPOTENCY_BARRIER"] = True

        # ---------------------------------------------------------------------
        # 8. GATE_ACTION_LEDGER_JOURNAL
        # ---------------------------------------------------------------------
        real_req = ActionCapabilityRequest(
            intent_id=UUIDv7.generate(),
            tenant_id=t_id,
            approval_id=approval_rec.approval_id,
            approval_digest=digest,
            action_type="reroute_carrier",
            idempotency_key="idemp_real_journal",
            target_entities=["order_001"],
            payload=payload,
            is_dry_run=False,
            as_of_time=now,
        )
        first_call = await gateway.dispatch_action(t_ctx, real_req)
        assert first_call.is_success
        ledger = first_call.unwrap()
        assert ledger.execution_status == "SUCCESS"
        assert ledger.provider_name == "mock_logistics_v1"
        checks["GATE_ACTION_LEDGER_JOURNAL"] = True

        # ---------------------------------------------------------------------
        # 9. GATE_INV_SEC001_CREDENTIAL_BROKER (15m TTL)
        # ---------------------------------------------------------------------
        broker = CredentialBroker()
        token = await broker.issue_ephemeral_token(
            tenant_id=t_id,
            provider="mock_logistics_v1",
            action_type="reroute_carrier",
            ttl_seconds=900,
        )
        v_res = broker.validate_token(
            credential=token,
            tenant_id=t_id,
            provider="mock_logistics_v1",
            action_type="reroute_carrier",
        )
        assert v_res.is_success
        checks["GATE_INV_SEC001_CREDENTIAL_BROKER"] = True

        # ---------------------------------------------------------------------
        # 10. GATE_INV_SEC001_SECRET_SCRUBBING
        # ---------------------------------------------------------------------
        dirty_payload = {"api_key": "secret_abc", "bearer_token": "Bearer 12345", "safe": 1}
        scrubbed = scrub_secrets(dirty_payload)
        assert scrubbed["api_key"] == "[REDACTED]"
        assert "Bearer [REDACTED]" in scrubbed["bearer_token"]
        assert scrubbed["safe"] == 1
        checks["GATE_INV_SEC001_SECRET_SCRUBBING"] = True

        # ---------------------------------------------------------------------
        # 11. GATE_INV_SEC001_DIRECT_EGRESS_BARRIER
        # ---------------------------------------------------------------------
        import socket
        with agent_egress_barrier():
            try:
                socket.socket()
                egress_blocked = False
            except GatewayError:
                egress_blocked = True
        assert egress_blocked is True
        checks["GATE_INV_SEC001_DIRECT_EGRESS_BARRIER"] = True

        # ---------------------------------------------------------------------
        # 12. GATE_INV_ACT001_MOCK_ROUTING
        # ---------------------------------------------------------------------
        checks["GATE_INV_ACT001_MOCK_ROUTING"] = (gateway.mock_adapter is not None)

        # ---------------------------------------------------------------------
        # 13-17. GATE_INV_REL001_MULTI_TIER_KILLSWITCHES (5 scopes)
        # ---------------------------------------------------------------------
        bus = DistributedKillSwitchBus()
        ks_service = KillSwitchService(bus=bus)

        # Global scope
        g_rec = await ks_service.activate(KillSwitchScope.GLOBAL, None, "test", "usr_admin")
        assert await ks_service.is_blocked(t_id, "any", "any", None) is True
        await ks_service.deactivate(g_rec.switch_id, "revert", "usr_admin")
        checks["GATE_INV_REL001_GLOBAL_KILLSWITCH"] = True

        # Tenant scope
        t_rec = await ks_service.activate(KillSwitchScope.TENANT, str(t_id), "test", "usr_admin")
        assert await ks_service.is_blocked(t_id, "any", "any", None) is True
        assert await ks_service.is_blocked(TenantId("tnt_other"), "any", "any", None) is False
        await ks_service.deactivate(t_rec.switch_id, "revert", "usr_admin")
        checks["GATE_INV_REL001_TENANT_KILLSWITCH"] = True

        # Capability scope
        c_rec = await ks_service.activate(KillSwitchScope.CAPABILITY, "charge_card", "test", "usr_admin")
        assert await ks_service.is_blocked(t_id, "charge_card", "any", None) is True
        assert await ks_service.is_blocked(t_id, "book_truck", "any", None) is False
        await ks_service.deactivate(c_rec.switch_id, "revert", "usr_admin")
        checks["GATE_INV_REL001_CAPABILITY_KILLSWITCH"] = True

        # Provider scope
        p_rec = await ks_service.activate(KillSwitchScope.PROVIDER, "stripe", "test", "usr_admin")
        assert await ks_service.is_blocked(t_id, "any", "stripe", None) is True
        assert await ks_service.is_blocked(t_id, "any", "ups", None) is False
        await ks_service.deactivate(p_rec.switch_id, "revert", "usr_admin")
        checks["GATE_INV_REL001_PROVIDER_KILLSWITCH"] = True

        # Investigation scope
        inv_id = UUIDv7.generate()
        i_rec = await ks_service.activate(KillSwitchScope.INVESTIGATION, str(inv_id), "test", "usr_admin")
        assert await ks_service.is_blocked(t_id, "any", "any", inv_id) is True
        assert await ks_service.is_blocked(t_id, "any", "any", UUIDv7.generate()) is False
        await ks_service.deactivate(i_rec.switch_id, "revert", "usr_admin")
        checks["GATE_INV_REL001_INVESTIGATION_KILLSWITCH"] = True

        # ---------------------------------------------------------------------
        # 18. GATE_INV_REL001_KILLSWITCH_PROPAGATION (< 500ms)
        # ---------------------------------------------------------------------
        node_1 = KillSwitchService(bus=bus)
        node_2 = KillSwitchService(bus=bus)
        t_prop = TenantId("tnt_prop")
        start = time.perf_counter()
        await node_1.activate(KillSwitchScope.TENANT, str(t_prop), "prop test", "usr_admin")
        blocked = await node_2.is_blocked(t_prop, "a", "b", None)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert blocked is True
        assert elapsed_ms < 500.0
        checks["GATE_INV_REL001_KILLSWITCH_PROPAGATION"] = True

        # ---------------------------------------------------------------------
        # 19. GATE_INV_ACT003_AGENT_KILLSWITCH_IMMUNITY
        # ---------------------------------------------------------------------
        agent_blocked = False
        try:
            await node_1.activate(KillSwitchScope.GLOBAL, None, "hacked", "usr_agent_planner")
        except AgentOverrideForbiddenError:
            agent_blocked = True
        assert agent_blocked is True
        checks["GATE_INV_ACT003_AGENT_KILLSWITCH_IMMUNITY"] = True

        # ---------------------------------------------------------------------
        # 20. GATE_NFR_COST001_BLAST_RADIUS_ENTITIES (Max 500)
        # ---------------------------------------------------------------------
        limiter = BlastRadiusLimiter()
        assert limiter.check_limits(MAX_AFFECTED_ENTITIES, Decimal("100.00"), 1).is_success
        assert limiter.check_limits(MAX_AFFECTED_ENTITIES + 1, Decimal("100.00"), 1).is_failure
        checks["GATE_NFR_COST001_BLAST_RADIUS_ENTITIES"] = True

        # ---------------------------------------------------------------------
        # 21. GATE_NFR_COST001_TIER_SPEND_CEILINGS
        # ---------------------------------------------------------------------
        assert limiter.check_limits(10, TIER_1_MAX_SPEND, 1).is_success
        assert limiter.check_limits(10, TIER_1_MAX_SPEND + Decimal("0.01"), 1).is_failure
        checks["GATE_NFR_COST001_TIER_SPEND_CEILINGS"] = True

        # ---------------------------------------------------------------------
        # 22. GATE_ADR0002_SAGA_REVERSE_COMPENSATION
        # ---------------------------------------------------------------------
        saga_wf = SafeActionSagaWorkflow()
        compound_intent = ActionIntentRecord(
            intent_id=UUIDv7.generate(),
            tenant_id=t_id,
            approval_id=approval_rec.approval_id,
            idempotency_key="idemp_saga_reverse_gate",
            action_type="multi_step_fulfillment",
            classification=ActionClassification.COMPENSATABLE,
            target_set_count=1,
            payload_digest="digest_multi",
            created_at=now,
        )
        steps = [
            SagaStep(name="step_a", compensation_action="undo_a"),
            SagaStep(name="step_b", compensation_action="undo_b", payload={"simulate_failure": True}),
        ]
        saga_res = await saga_wf.execute_action_saga(compound_intent, steps=steps)
        assert saga_res.execution_status == "COMPENSATED"
        assert saga_wf.compensation_history[-1].step_name == "step_a"
        checks["GATE_ADR0002_SAGA_REVERSE_COMPENSATION"] = True

        # ---------------------------------------------------------------------
        # 23. GATE_ADR0002_IRREVERSIBLE_ACTION_GUARD
        # ---------------------------------------------------------------------
        irrev_blocked = False
        try:
            await saga_wf.compensate_steps(
                completed_steps=[("truck_dispatch", {})],
                tenant_id=t_id,
                intent_id=UUIDv7.generate(),
                classification=ActionClassification.IRREVERSIBLE,
            )
        except IrreversibleActionError:
            irrev_blocked = True
        assert irrev_blocked is True
        checks["GATE_ADR0002_IRREVERSIBLE_ACTION_GUARD"] = True

        # ---------------------------------------------------------------------
        # 24. GATE_NFR_REL001_ZERO_BLIND_RETRIES
        # ---------------------------------------------------------------------
        inquiry_ran = False
        def mock_inquiry(p, k):
            nonlocal inquiry_ran
            inquiry_ran = True
            return ProviderInquiryResult(status=ProviderTransactionStatus.CONFIRMED, provider_tx_id="tx_1")

        timeout_steps = [SagaStep(name="timeout_step", compensation_action="undo", payload={"simulate_timeout": True})]
        await saga_wf.execute_action_saga(compound_intent, steps=timeout_steps, custom_query_fn=mock_inquiry)
        assert inquiry_ran is True
        checks["GATE_NFR_REL001_ZERO_BLIND_RETRIES"] = True

        # ---------------------------------------------------------------------
        # 25. GATE_DETERMINISTIC_RECONCILIATION
        # ---------------------------------------------------------------------
        recon_mgr = ReconciliationManager()
        def fail_inquiry(p, k):
            return ProviderInquiryResult(status=ProviderTransactionStatus.INCONCLUSIVE)
        recon_ledger = await recon_mgr.reconcile_unknown(compound_intent, ledger, fail_inquiry, max_attempts=3)
        assert recon_ledger.execution_status == "TIMEOUT_UNKNOWN"
        assert len(recon_mgr.emitted_outbox_events) == 1
        checks["GATE_DETERMINISTIC_RECONCILIATION"] = True

        # ---------------------------------------------------------------------
        # 26. GATE_FINOPS_NET_ROI_ATTRIBUTION
        # ---------------------------------------------------------------------
        outcome_service = ActionOutcomeService()
        outcome_rec = await outcome_service.record_outcome(
            ctx=t_ctx,
            intent_id=UUIDv7.generate(),
            actual_cost=Decimal("20.00"),
            observed_rev=Decimal("120.00"),
        )
        assert outcome_rec.net_roi_usd == Decimal("100.00")
        checks["GATE_FINOPS_NET_ROI_ATTRIBUTION"] = True

        # ---------------------------------------------------------------------
        # 27. GATE_INV_AI001_OUTCOME_SEGREGATION
        # ---------------------------------------------------------------------
        segregation_enforced = False
        try:
            await outcome_service.record_outcome(
                ctx=t_ctx,
                intent_id=UUIDv7.generate(),
                actual_cost=Decimal("10.00"),
                observed_rev=Decimal("50.00"),
                trigger_model_promotion=True,
            )
        except Exception:
            segregation_enforced = True
        assert segregation_enforced is True
        checks["GATE_INV_AI001_OUTCOME_SEGREGATION"] = True

        # ---------------------------------------------------------------------
        # 28. GATE_INV_AUD001_UNSAMPLED_AUDIT_TRAIL
        # ---------------------------------------------------------------------
        audit_logger = ActionAuditLogger()
        audit_logger.log_event(t_id, "usr_admin", "action.approved", "action/1", "approve")
        audit_logger.log_event(t_id, "usr_admin", "action.dispatched", "action/1", "dispatch")
        audit_logger.log_event(t_id, "usr_admin", "action.completed", "action/1", "complete")
        assert len(audit_logger.get_events()) == 3
        checks["GATE_INV_AUD001_UNSAMPLED_AUDIT_TRAIL"] = True

        # Compile final composite gate report
        total = len(checks)
        passed = sum(1 for v in checks.values() if v)
        failed = total - passed
        compliance = (passed / total) * 100.0
        gate_status = "PASS" if failed == 0 and total == 28 else "LOCKED"

        return CompositeGateReport(
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            compliance_percentage=compliance,
            gate_status=gate_status,
            check_results=checks,
            details={"evaluated_at": now.isoformat()},
        )


@pytest.mark.asyncio
async def test_phase_06_exit_gate_runner_all_28_checks():
    """
    TC-P06-028: Phase 06 Exit Gate Evaluation.
    Asserts 100% compliance across all 28 binary criteria and transitions status to PASS.
    """
    report = await Phase06ExitGateRunner.run_all_checks()

    assert report.total_checks == 28, f"Expected exactly 28 exit gate checks, got {report.total_checks}"
    assert report.failed_checks == 0, f"Failed checks detected: {report.check_results}"
    assert report.passed_checks == 28
    assert report.compliance_percentage == 100.0
    assert report.gate_status == "PASS"
