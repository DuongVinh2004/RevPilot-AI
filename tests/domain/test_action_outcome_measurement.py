"""
RevPilot AI — Action Outcome Measurement and Net ROI Attribution Tests
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §2, §3
Specification: docs/22-billing/AUDIT-LOG-SPEC.md §2
Conforms to INV-AUD-001, INV-AI-001, and TC-P06-026.
"""

from __future__ import annotations
from decimal import Decimal
import pytest

from revpilot.modules.action.outcome.audit import ActionAuditLogger
from revpilot.modules.action.outcome.domain import (
    ActionOutcomeError,
    OutcomeSegregationViolationError,
)
from revpilot.modules.action.outcome.service import ActionOutcomeService
from revpilot.shared.context import TenantContext
from revpilot.shared.identifiers import OrganizationId, TenantId, UUIDv7


@pytest.fixture
def test_setup():
    audit_logger = ActionAuditLogger()
    service = ActionOutcomeService(audit_logger=audit_logger)
    ctx = TenantContext(
        tenant_id=TenantId("tnt_roi_test"),
        organization_id=OrganizationId("org_roi_test"),
        is_active=True,
    )
    return service, audit_logger, ctx


@pytest.mark.asyncio
async def test_net_roi_attribution_exact_calculation(test_setup):
    """
    Net ROI is strictly computed as (observed_revenue_usd - actual_cost_usd)
    and bound to the approval_id and customer_id (TC-P06-026).
    """
    service, audit_logger, ctx = test_setup

    intent_id = UUIDv7.generate()
    approval_id = UUIDv7.generate()
    customer_id = "cust_enterprise_001"

    observed_rev = Decimal("12500.50")
    actual_cost = Decimal("250.25")
    expected_rev = Decimal("12000.00")

    outcome = await service.record_outcome(
        ctx=ctx,
        intent_id=intent_id,
        actual_cost=actual_cost,
        observed_rev=observed_rev,
        expected_rev=expected_rev,
        customer_id=customer_id,
        approval_id=approval_id,
    )

    # Net ROI assertion: 12500.50 - 250.25 = 12250.25
    assert outcome.net_roi_usd == Decimal("12250.25")
    assert outcome.actual_cost_usd == actual_cost
    assert outcome.observed_revenue_usd == observed_rev
    assert outcome.expected_revenue_usd == expected_rev
    assert outcome.customer_id == customer_id
    assert outcome.approval_id == approval_id
    assert outcome.tenant_id == ctx.tenant_id

    # Verify audit event emitted (INV-AUD-001)
    events = audit_logger.get_events(tenant_id=ctx.tenant_id, event_type="action.outcome.measured")
    assert len(events) == 1
    assert events[0].details["net_roi_usd"] == "12250.25"


@pytest.mark.asyncio
async def test_negative_net_roi_supported(test_setup):
    """Negative ROI (cost exceeding retained revenue) must be computed accurately."""
    service, _, ctx = test_setup

    outcome = await service.record_outcome(
        ctx=ctx,
        intent_id=UUIDv7.generate(),
        actual_cost=Decimal("150.00"),
        observed_rev=Decimal("50.00"),
    )
    assert outcome.net_roi_usd == Decimal("-100.00")


@pytest.mark.asyncio
async def test_outcome_segregation_bars_automated_model_promotion(test_setup):
    """
    INV-AI-001: Observed action outcomes cannot automatically trigger model promotion
    or policy relaxation.
    """
    service, _, ctx = test_setup

    with pytest.raises(OutcomeSegregationViolationError) as exc_info:
        await service.record_outcome(
            ctx=ctx,
            intent_id=UUIDv7.generate(),
            actual_cost=Decimal("10.00"),
            observed_rev=Decimal("100.00"),
            trigger_model_promotion=True,
        )

    err = exc_info.value
    assert err.code == "ERR_OUTCOME_SEGREGATION_VIOLATION"
    assert "INV-AI-001" in err.message


@pytest.mark.asyncio
async def test_transactional_outbox_failure_rolls_back_atomically(test_setup):
    """
    Rollback and Recovery Contract:
    If outbox event persistence fails, the entire transaction rolls back,
    preventing orphaned outcome records in the store.
    """
    service, _, ctx = test_setup
    intent_id = UUIDv7.generate()

    with pytest.raises(ActionOutcomeError) as exc_info:
        await service.record_outcome(
            ctx=ctx,
            intent_id=intent_id,
            actual_cost=Decimal("20.00"),
            observed_rev=Decimal("200.00"),
            simulate_outbox_failure=True,
        )

    assert "rollback" in exc_info.value.message.lower()

    # Verify zero orphaned records in outcome store or outbox list
    assert len(service.outcome_store) == 0
    assert len(service.outbox_events) == 0


@pytest.mark.asyncio
async def test_audit_scrubs_secrets_from_outcome_details(test_setup):
    """
    INV-AUD-002: Audit records must scrub sensitive keys from metadata.
    """
    _, audit_logger, ctx = test_setup

    audit_logger.log_event(
        tenant_id=ctx.tenant_id,
        actor_id="test_actor",
        event_type="action.audit.test",
        resource="test_resource",
        action="test_action",
        details={
            "api_key": "secret_key_12345",
            "token": "bearer_abcde",
            "auth_header": "Bearer eyJhbGciOi...",
            "safe_metric": 42,
        },
    )

    events = audit_logger.get_events(tenant_id=ctx.tenant_id, event_type="action.audit.test")
    assert len(events) == 1
    d = events[0].details
    assert d["api_key"] == "[REDACTED]"
    assert d["token"] == "[REDACTED]"
    assert "Bearer [REDACTED]" in d["auth_header"]
    assert d["safe_metric"] == 42
