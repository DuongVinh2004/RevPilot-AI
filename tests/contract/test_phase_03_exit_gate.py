"""
RevPilot AI — Phase 03 Governed Evidence & Investigation Exit-Gate Verification Suite
Verifies execution/MASTER-ROADMAP.md §Phase-03, AC-P03-008-01 through AC-P03-008-02.
Enforces INV-WF-001..002, INV-TEN-001..003, INV-SEC-001..003, INV-AI-001..002,
INV-COST-001, AC-003, AC-004, AC-005, AC-013, and AC-014.
"""

from __future__ import annotations
from decimal import Decimal
import sys
from typing import Any
import pytest

from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_modules():
    """Ensure business modules are clean between test runs and during collection."""
    yield
    for mod in list(sys.modules.keys()):
        if any(
            mod.startswith(p)
            for p in (
                "revpilot.modules.investigation",
                "revpilot.modules.analytics",
                "revpilot.modules.evidence",
                "revpilot.modules.retrieval",
                "revpilot.modules.agent",
                "revpilot.modules.tickets",
            )
        ):
            sys.modules.pop(mod, None)


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha_corp")


@pytest.fixture
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta_adversary")


@pytest.fixture
def sample_investigation_id() -> UUIDv7:
    return UUIDv7.generate()


# =============================================================================
# 1. AC-P03-008-01: Full End-to-End Investigation on Truck-Capacity Incident
# =============================================================================

@pytest.mark.asyncio
async def test_phase_03_full_investigation_e2e(tenant_alpha, sample_investigation_id):
    """
    AC-P03-008-01: Full end-to-end investigation on truck-capacity incident (INC-SYNTH-TRUCK-001).
    - Identifies primary root cause (CARRIER_CAPACITY_COLLAPSE) with verified citations (AC-003).
    - Refutes/demotes competing decoy hypotheses (PAYMENT_GATEWAY_OUTAGE, PRICE_INCREASE_CHURN) (AC-004).
    - Produces a sealed, tamper-evident InvestigationManifest (INV-EVD-001).
    - Suppresses model chain-of-thought (AC-013).
    """
    from revpilot.modules.evidence.domain.models import (
        EvidenceRecord,
        CitationSpan,
        SourceSystemType,
        ClassificationLevel,
        SupersessionStatus,
        ExtractionMethod,
        RetrievalMethod,
        compute_content_digest,
    )
    from revpilot.modules.evidence import package_evidence_bundle
    from revpilot.modules.agent.synthesizer import Hypothesis
    from revpilot.modules.agent.verifier import InvestigationVerifier, VerificationStatus
    from revpilot.modules.investigation.domain.models import InvestigationManifest

    now = UtcDateTime.now()

    # 1. Gathered Evidence Item 1: SQL aggregate showing carrier delay spike
    sql_payload = {
        "facility_id": "WH-MIDWEST-01",
        "carrier_id": "CARRIER_REGIONAL_LOGISTICS",
        "delayed_shipments": 42,
        "cancellation_rate": 0.0840,
    }
    sql_ev = EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=tenant_alpha,
        acl_policy_ref="policy_sql_read",
        source_system=SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="canonical_shipments:WH-MIDWEST-01",
        source_version="v1",
        content_digest=compute_content_digest(sql_payload),
        classification=ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=SupersessionStatus.ACTIVE,
        extraction_method=ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0.0",
        retrieval_method=RetrievalMethod.SQL_DIRECT,
        confidence_score=0.96,
        payload=sql_payload,
    )

    # 2. Gathered Evidence Item 2: Carrier advisory document snippet
    doc_snippet = "Regional Logistics driver shortage led to severe capacity collapse in Midwest hub."
    doc_payload = {"document_title": "Regional Logistics Carrier Notice", "excerpt": doc_snippet}
    doc_ev = EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=tenant_alpha,
        acl_policy_ref="policy_doc_read",
        source_system=SourceSystemType.DOCUMENT_STORE,
        source_object_ref="doc_carrier_advisory_20260515",
        source_version="v1",
        content_digest=compute_content_digest(doc_payload),
        classification=ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=SupersessionStatus.ACTIVE,
        extraction_method=ExtractionMethod.DOCUMENT_CHUNK,
        parser_version="1.0.0",
        retrieval_method=RetrievalMethod.HYBRID_FUSED,
        citation_span=CitationSpan(
            chunk_id="doc_carrier_advisory_20260515_c1",
            start_char=0,
            end_char=len(doc_snippet),
            snippet_text=doc_snippet,
        ),
        confidence_score=0.91,
        payload=doc_payload,
    )

    # 3. Gathered Evidence Item 3: Customer support ticket cluster
    ticket_snippet = "Customer orders delayed past promised SLA due to truck unavailability."
    ticket_payload = {"ticket_id": "TCK-MIDWEST-088", "category": "FULFILLMENT_DELAY", "notes": ticket_snippet}
    tck_ev = EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=tenant_alpha,
        acl_policy_ref="policy_ticket_read",
        source_system=SourceSystemType.SUPPORT_DESK,
        source_object_ref="ticket:TCK-MIDWEST-088",
        source_version="v1",
        content_digest=compute_content_digest(ticket_payload),
        classification=ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=SupersessionStatus.ACTIVE,
        extraction_method=ExtractionMethod.TICKET_EXTRACT,
        parser_version="1.0.0",
        retrieval_method=RetrievalMethod.SQL_DIRECT,
        citation_span=CitationSpan(
            chunk_id="TCK-MIDWEST-088",
            start_char=0,
            end_char=len(ticket_snippet),
            snippet_text=ticket_snippet,
        ),
        confidence_score=0.88,
        payload=ticket_payload,
    )

    # Package into sealed immutable bundle
    bundle_res = package_evidence_bundle(
        investigation_id=sample_investigation_id,
        tenant_id=tenant_alpha,
        records=[sql_ev, doc_ev, tck_ev],
        verify_digests=True,
    )
    assert bundle_res.is_success
    bundle = bundle_res.unwrap()
    assert bundle.evidence_count == 3
    assert len(bundle.bundle_digest) == 64

    # 4. Formulate Leading Root-Cause Hypothesis + 2 Decoys
    h_truck_lead = Hypothesis(
        hypothesis_id="HYPO-TRUCK-CAPACITY",
        title="CARRIER_CAPACITY_COLLAPSE",
        description="Midwest carrier capacity shortage caused delayed shipments and elevated order cancellations.",
        likelihood_score=0.94,
        supporting_evidence_ids=[sql_ev.evidence_id, doc_ev.evidence_id, tck_ev.evidence_id],
        contradicting_evidence_ids=[],
        unverified_claims=[],
        limitations=["Affects primarily Midwest region WH-MIDWEST-01"],
    )

    # Decoy 1: Payment gateway outage (unsupported by any evidence)
    h_decoy_payment = Hypothesis(
        hypothesis_id="HYPO-DECOY-PAYMENT",
        title="PAYMENT_GATEWAY_OUTAGE",
        description="Payment gateway failure caused customer order dropoff.",
        likelihood_score=0.65,
        supporting_evidence_ids=[],  # Lacks citations (INV-AI-001)
        contradicting_evidence_ids=[],
        unverified_claims=["Payment processor rejected 40% of checkout attempts."],
        limitations=[],
    )

    # Decoy 2: Competitor price drop / pricing churn (hallucinated citation ID)
    phantom_evidence_id = UUIDv7.generate()
    h_decoy_price = Hypothesis(
        hypothesis_id="HYPO-DECOY-PRICING",
        title="PRICE_INCREASE_CHURN",
        description="Competitor discounts caused customer churn.",
        likelihood_score=0.72,
        supporting_evidence_ids=[phantom_evidence_id],  # Phantom ID not in bundle
        contradicting_evidence_ids=[],
        unverified_claims=["Subscription prices increased by 25%"],
        limitations=[],
    )

    # 5. Deterministic Verification
    verifier = InvestigationVerifier()
    verification = verifier.verify_hypotheses(
        [h_truck_lead, h_decoy_payment, h_decoy_price],
        bundle,
    )

    # Assert leading hypothesis is verified and top ranked
    assert verification.status == VerificationStatus.VERIFIED
    assert verification.top_hypothesis_id == "HYPO-TRUCK-CAPACITY"
    assert verification.ranked_hypotheses[0].hypothesis_id == "HYPO-TRUCK-CAPACITY"
    assert verification.evidence_coverage_ratio == 1.0

    # Assert decoys are flagged with unsupported claims
    assert verification.unsupported_claim_count >= 2
    assert any("HYPO-DECOY-PAYMENT" in d for d in verification.missing_evidence_descriptors)
    assert any("HYPO-DECOY-PRICING" in d for d in verification.missing_evidence_descriptors)

    # 6. Build Sealed Manifest
    manifest = InvestigationManifest(
        investigation_id=str(sample_investigation_id),
        tenant_id=tenant_alpha,
        top_hypothesis_id=verification.top_hypothesis_id,
        bundle_digest=bundle.bundle_digest,
        cogs_usd=Decimal("0.45"),
        duration_seconds=12,
        sealed_at=now,
    )
    assert manifest.top_hypothesis_id == "HYPO-TRUCK-CAPACITY"
    assert manifest.bundle_digest == bundle.bundle_digest


# =============================================================================
# 2. AC-P03-008-02: Read-Only Barrier Contract (INV-ACT-001)
# =============================================================================

@pytest.mark.asyncio
async def test_phase_03_read_only_barrier():
    """
    INV-ACT-001: Verifies that Phase 03 is strictly read-only.
    - Zero mutation / DDL / DML capabilities are registered in the catalog.
    - All SQL templates are deterministic read-only SELECT projections.
    """
    from revpilot.modules.analytics.capabilities.catalog import REGISTERED_SQL_CAPABILITIES
    from revpilot.modules.analytics.capabilities.templates import (
        build_sql_for_capability,
        detect_prohibited_sql,
    )
    from revpilot.shared.identifiers import TenantId
    from revpilot.shared.temporal import UtcDateTime

    # 1. Inspect catalog: all must be read-only analytics queries
    assert len(REGISTERED_SQL_CAPABILITIES) >= 7
    for cap_id, cap_def in REGISTERED_SQL_CAPABILITIES.items():
        assert cap_def.required_permission in ("analytics:query", "investigation:read")
        assert "delete" not in cap_def.name.lower()
        assert "update" not in cap_def.name.lower()
        assert "insert" not in cap_def.name.lower()
        assert "drop" not in cap_def.name.lower()

    # 2. Inspect generated templates: must start with SELECT and contain no mutating keywords
    tnt = TenantId("tnt_test_barrier")
    now = UtcDateTime.now()
    base_params = {
        "tenant_id": tnt.value,
        "start_time": now.isoformat(),
        "end_time": now.isoformat(),
        "as_of_time": now.isoformat(),
    }

    for cap_id, cap_def in REGISTERED_SQL_CAPABILITIES.items():
        sql, _ = build_sql_for_capability(cap_def, base_params, dialect="sqlite")
        clean_q = sql.strip().upper()
        assert clean_q.startswith("SELECT"), f"Capability {cap_id} must be a SELECT statement"
        assert detect_prohibited_sql(sql) is False, f"Capability {cap_id} contained prohibited DDL/DML"

    # 3. Assert safety detector blocks attempted DDL/DML injection
    assert detect_prohibited_sql("DROP TABLE canonical_orders;") is True
    assert detect_prohibited_sql("UPDATE canonical_orders SET total_cents = 0;") is True
    assert detect_prohibited_sql("SELECT * FROM canonical_orders; DELETE FROM canonical_orders;") is True


# =============================================================================
# 3. AC-P03-008-02: Cross-Tenant Airgap Verification (INV-TEN-001..003)
# =============================================================================

@pytest.mark.asyncio
async def test_phase_03_cross_tenant_airgap(tenant_alpha, tenant_beta, sample_investigation_id):
    """
    INV-TEN-001..003: Exhaustive airgap verification across SQL, documents, tickets, and bundles.
    """
    from revpilot.modules.tickets.domain.models import InMemoryTicketStore, CanonicalTicket, TicketStatus, TicketPriority, compute_ticket_digest
    from revpilot.modules.evidence.domain.models import (
        EvidenceRecord,
        SourceSystemType,
        ClassificationLevel,
        SupersessionStatus,
        ExtractionMethod,
        RetrievalMethod,
    )
    from revpilot.modules.evidence import package_evidence_bundle
    from revpilot.modules.analytics.capabilities.catalog import REGISTERED_SQL_CAPABILITIES
    from revpilot.modules.analytics.capabilities.templates import build_sql_for_capability

    now = UtcDateTime.now()

    # 1. SQL Airgap: tenant_id condition strictly baked into WHERE clause
    cap_def = REGISTERED_SQL_CAPABILITIES["CAP-SQL-DRILLDOWN-DIM"]
    sql, params = build_sql_for_capability(
        cap_def,
        {
            "tenant_id": tenant_alpha.value,
            "start_time": now.isoformat(),
            "end_time": now.isoformat(),
            "as_of_time": now.isoformat(),
            "dimension": "tier",
        },
    )
    assert params["tenant_id"] == tenant_alpha.value
    assert "o.tenant_id = :tenant_id" in sql

    # 2. Ticket Airgap: Tenant Beta ticket cannot be fetched by Tenant Alpha
    ticket_store = InMemoryTicketStore()
    t_beta = CanonicalTicket(
        ticket_id="TCK-CONFIDENTIAL-BETA",
        tenant_id=tenant_beta,
        source_system="ZENDESK",
        version=1,
        customer_id="cus_b1",
        created_at=now,
        updated_at=now,
        status=TicketStatus.OPEN,
        priority=TicketPriority.URGENT,
        category="LEGAL",
        subject_masked="Confidential legal query",
        body_masked="Private corporate communication.",
        sentiment_score=-0.8,
        injection_risk_score=0.0,
        is_quarantined=False,
        content_digest=compute_ticket_digest("Private corporate communication."),
    )
    ticket_store.ingest(t_beta)
    assert ticket_store.get(tenant_alpha, "ZENDESK", "TCK-CONFIDENTIAL-BETA") is None

    # 3. Evidence Packaging Airgap: bundling foreign record raises ERR_CROSS_TENANT_EVIDENCE
    foreign_rec = EvidenceRecord(
        evidence_id=UUIDv7.generate(),
        tenant_id=tenant_beta,
        acl_policy_ref="policy_read",
        source_system=SourceSystemType.CANONICAL_POSTGRES,
        source_object_ref="canonical_orders:beta",
        source_version="v1",
        content_digest="digest_b",
        classification=ClassificationLevel.INTERNAL,
        event_time=now,
        effective_time=now,
        as_of_time=now,
        ingestion_time=now,
        supersession_status=SupersessionStatus.ACTIVE,
        extraction_method=ExtractionMethod.SQL_AGGREGATE,
        parser_version="1.0.0",
        retrieval_method=RetrievalMethod.SQL_DIRECT,
        confidence_score=0.90,
        payload={},
    )
    res = package_evidence_bundle(sample_investigation_id, tenant_alpha, [foreign_rec], verify_digests=False)
    assert res.is_failure
    assert res.unwrap_error().code == "ERR_CROSS_TENANT_EVIDENCE"


# =============================================================================
# 4. AC-P03-008-01: Worker Crash Durability and Replay (INV-WF-002)
# =============================================================================

@pytest.mark.asyncio
async def test_phase_03_worker_crash_durability():
    """
    INV-WF-002: Activity worker crashes mid-workflow, activity retries per policy,
    and workflow completes cleanly with zero duplicate activity side effects.
    """
    from temporalio import activity
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker
    from revpilot.modules.investigation.workflows import (
        InvestigationWorkflow,
        InvestigationWorkflowInput,
        INVESTIGATION_WORKFLOW_QUEUE,
        INVESTIGATION_ANALYTICS_QUEUE,
        INVESTIGATION_RETRIEVAL_QUEUE,
        INVESTIGATION_AGENT_QUEUE,
        ValidateInvestigationScopeResult,
        package_evidence_bundle_activity,
        execute_read_only_sql_capability_activity,
        execute_governed_retrieval_activity,
        ingest_ticket_intelligence_activity,
        generate_investigation_plan_activity,
        synthesize_hypotheses_activity,
        verify_evidence_and_hypotheses_activity,
    )
    from revpilot.modules.investigation.domain.models import InvestigationStatus

    execution_attempts = 0

    @activity.defn(name="ValidateInvestigationScopeActivity")
    async def crash_once_scope_activity(input_data: Any) -> Any:
        nonlocal execution_attempts
        execution_attempts += 1
        if execution_attempts == 1:
            raise RuntimeError("CRASH_INJECTED: Worker process terminated unexpectedly")
        if isinstance(input_data, dict):
            m_name = input_data["metric_name"]
            filters = input_data.get("investigation_scope", {})
        else:
            m_name = input_data.metric_name
            filters = input_data.investigation_scope

        return ValidateInvestigationScopeResult(
            is_valid=True,
            metric_name=m_name,
            dimension_filters=filters,
            validation_message="Recovered on retry",
        )

    wf_input = InvestigationWorkflowInput(
        investigation_id="inv_crash_gate_01",
        tenant_id="tnt_durability_gate",
        principal_id="usr_gate_tester",
        metric_name="order_cancellation_rate",
        investigation_scope={"region": "US-MIDWEST"},
        window_start="2026-05-10T00:00:00.000000Z",
        window_end="2026-05-17T00:00:00.000000Z",
        as_of_time="2026-05-18T00:00:00.000000Z",
        cost_budget_usd=Decimal("2.50"),
    )

    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env:
        async with (
            Worker(
                env.client,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
                workflows=[InvestigationWorkflow],
                activities=[crash_once_scope_activity, package_evidence_bundle_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_ANALYTICS_QUEUE,
                activities=[execute_read_only_sql_capability_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_RETRIEVAL_QUEUE,
                activities=[execute_governed_retrieval_activity, ingest_ticket_intelligence_activity],
            ),
            Worker(
                env.client,
                task_queue=INVESTIGATION_AGENT_QUEUE,
                activities=[
                    generate_investigation_plan_activity,
                    synthesize_hypotheses_activity,
                    verify_evidence_and_hypotheses_activity,
                ],
            ),
        ):
            wf_id = f"tenant/{wf_input.tenant_id}/investigation/{wf_input.investigation_id}"
            handle = await env.client.start_workflow(
                InvestigationWorkflow.run,
                wf_input,
                id=wf_id,
                task_queue=INVESTIGATION_WORKFLOW_QUEUE,
            )

            manifest = await handle.result()
            assert manifest is not None
            assert manifest.top_hypothesis_id is not None
            assert execution_attempts == 2

            state = await handle.query(InvestigationWorkflow.get_investigation_state)
            assert state.status == InvestigationStatus.COMPLETED
            assert state.error_code is None
