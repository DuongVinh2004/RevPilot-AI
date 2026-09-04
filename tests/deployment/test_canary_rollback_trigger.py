"""
RevPilot AI — Tests: Canary Progressive Rollout & Automated Multi-Tier Rollback
Specification: docs/30-deployment/RELEASE-CANARY-ROLLBACK-SPEC.md §7, §8
Conforms to ADR-0008, INV-REL-001, TC-P08-024, AC-REL-02, AC-P08-003-02.
"""

from __future__ import annotations

import pytest

from revpilot.modules.operations.release import (
    CanaryController,
    CanaryHealthFailedError,
    CanaryStage,
    ReleaseRegistry,
    RollbackCoordinator,
)


@pytest.fixture
def registry_with_bundles() -> tuple[ReleaseRegistry, str, str]:
    reg = ReleaseRegistry()
    baseline = reg.register_bundle({
        "bundle_id": "bundle_stable_baseline_v1",
        "t01_binary_digest": "sha256:baseline_binary_digest_001",
        "t02_api_version": "v1.0.0",
        "t03_schema_version": "20260901_v01",
        "t04_workflow_version": "wf_v1",
        "t05_connector_version": "conn_v1",
        "t06_prompt_digest": "pr_sha256:prompt_baseline",
        "t07_model_snapshot": "model_baseline",
        "t08_embedding_model": "embed_baseline",
        "t09_vector_index_version": "vec_baseline",
        "t10_retrieval_config_digest": "rag_baseline",
        "t11_policy_digest": "pol_baseline",
        "t12_feature_flags_digest": "ff_baseline",
        "t13_tenant_config_version": "tenant_v1",
    })

    canary = reg.register_bundle({
        "bundle_id": "bundle_candidate_canary_v2",
        "t01_binary_digest": "sha256:canary_binary_digest_002",
        "t02_api_version": "v1.1.0",
        "t03_schema_version": "20260904_v02",
        "t04_workflow_version": "wf_v2",
        "t05_connector_version": "conn_v2",
        "t06_prompt_digest": "pr_sha256:prompt_canary",
        "t07_model_snapshot": "model_canary",
        "t08_embedding_model": "embed_canary",
        "t09_vector_index_version": "vec_canary",
        "t10_retrieval_config_digest": "rag_canary",
        "t11_policy_digest": "pol_canary",
        "t12_feature_flags_digest": "ff_canary",
        "t13_tenant_config_version": "tenant_v2",
    })

    return reg, baseline.bundle_id, canary.bundle_id


def test_progressive_canary_rollout_stages(registry_with_bundles: tuple[ReleaseRegistry, str, str]):
    """
    Verifies normal progressive rollout sequence: 5% -> 25% -> 100% General availability (§7).
    """
    reg, baseline_id, canary_id = registry_with_bundles
    controller = CanaryController(release_registry=reg, baseline_bundle_id=baseline_id)

    # 1. Admit to 5%
    controller.start_canary(canary_id)
    assert controller.current_stage == CanaryStage.CANARY_5
    assert controller.traffic_percentage == 5
    assert controller.active_canary_bundle_id == canary_id

    # Healthy observation
    health = controller.evaluate_canary_health(canary_id, error_rate_5xx=0.001, p95_latency_ms=180.0)
    assert health.healthy is True

    # 2. Promote to 25%
    controller.promote_canary_stage(canary_id, 25)
    assert controller.current_stage == CanaryStage.CANARY_25
    assert controller.traffic_percentage == 25

    # 3. Promote to 100% General
    controller.promote_canary_stage(canary_id, 100)
    assert controller.current_stage == CanaryStage.GENERAL_100
    assert controller.traffic_percentage == 100


def test_canary_5xx_spike_triggers_automated_rollback_under_60s(registry_with_bundles: tuple[ReleaseRegistry, str, str]):
    """
    AC-P08-003-02 & TC-P08-024:
    Injected 5xx error spike (error_rate > 0.005) triggers automated rollback,
    restoring 100% baseline traffic routing within 60s, and quarantines canary bundle.
    """
    reg, baseline_id, canary_id = registry_with_bundles
    controller = CanaryController(release_registry=reg, baseline_bundle_id=baseline_id)

    controller.start_canary(canary_id)
    assert controller.traffic_percentage == 5

    # Inject 5xx spike (0.012 > 0.005 threshold)
    with pytest.raises(CanaryHealthFailedError) as exc_info:
        controller.evaluate_canary_health(
            canary_bundle_id=canary_id,
            error_rate_5xx=0.012,
            auto_rollback=True,
        )

    assert exc_info.value.code == "CANARY_HEALTH_FAILED"
    assert exc_info.value.status_code == 500

    # Verify Canary state immediately aborted and traffic zeroed (< 30s)
    assert controller.current_stage == CanaryStage.ABORTED_ROLLED_BACK
    assert controller.traffic_percentage == 0

    # Verify RollbackSummary metrics
    summary = controller.last_rollback_summary
    assert summary is not None
    assert summary.canary_bundle_id == canary_id
    assert summary.baseline_bundle_id == baseline_id
    assert summary.traffic_shifted_to_baseline is True
    assert summary.canary_quarantined is True
    assert summary.total_duration_sec < 60.0  # SLA < 60s (AC-P08-003-02)

    # Verify bundle quarantined in registry (§9.3)
    assert reg.is_quarantined(canary_id) is True

    # Quarantined bundle cannot be redeployed
    with pytest.raises(ValueError, match="Cannot deploy quarantined"):
        controller.start_canary(canary_id)


def test_coordinated_rollback_executes_all_6_steps(registry_with_bundles: tuple[ReleaseRegistry, str, str]):
    """
    Verifies that RollbackCoordinator strictly executes all 6 multi-tier dependency steps (§8.1).
    """
    reg, baseline_id, canary_id = registry_with_bundles
    coordinator = RollbackCoordinator()

    summary = coordinator.execute_coordinated_rollback(
        canary_bundle_id=canary_id,
        baseline_bundle_id=baseline_id,
        reason="P95 latency breach and worker panic",
    )

    assert summary.status == "COMPLETED"
    assert len(summary.steps_executed) == 6

    step_names = [s.name for s in summary.steps_executed]
    assert any("Step 1" in name and "Ingress Shift" in name for name in step_names)
    assert any("Step 2" in name and "Feature Flag" in name for name in step_names)
    assert any("Step 3" in name and "Workflow & Worker Drainage" in name for name in step_names)
    assert any("Step 4" in name and "AI Model & Prompt" in name for name in step_names)
    assert any("Step 5" in name and "Vector Index" in name for name in step_names)
    assert any("Step 6" in name and "Database Schema Contract" in name for name in step_names)

    # Check Step 1 duration < 30s
    step1 = summary.steps_executed[0]
    assert step1.duration_seconds <= step1.max_sla_seconds
    assert step1.details["baseline_traffic_percent"] == 100

    # Check Step 2 duration < 60s
    step2 = summary.steps_executed[1]
    assert step2.duration_seconds <= step2.max_sla_seconds

    # Audit events emitted
    assert len(coordinator.audit_events) >= 1
    assert coordinator.audit_events[0]["event_type"] == "COORDINATED_ROLLBACK_COMPLETED"


def test_additional_canary_rollback_triggers(registry_with_bundles: tuple[ReleaseRegistry, str, str]):
    """
    Verifies additional rollback triggers: P95 latency, workflow crashes, RLS breaches, cost anomaly (§7.1).
    """
    reg, baseline_id, canary_id = registry_with_bundles

    # 1. P95 latency breach (>25% degradation)
    c1 = CanaryController(release_registry=reg, baseline_bundle_id=baseline_id)
    c1.start_canary(canary_id)
    with pytest.raises(CanaryHealthFailedError):
        c1.evaluate_canary_health(canary_id, p95_latency_ms=300.0, baseline_p95_ms=200.0)
    assert c1.traffic_percentage == 0

    # Reset quarantine for next check
    reg._quarantine_reasons.clear()
    reg._bundles[canary_id] = reg._bundles[canary_id].model_copy(update={"status": "QUALIFIED"})

    # 2. Workflow crashes (>0)
    c2 = CanaryController(release_registry=reg, baseline_bundle_id=baseline_id)
    c2.start_canary(canary_id)
    with pytest.raises(CanaryHealthFailedError):
        c2.evaluate_canary_health(canary_id, workflow_crashes=2)
    assert c2.traffic_percentage == 0

    # Reset quarantine
    reg._quarantine_reasons.clear()
    reg._bundles[canary_id] = reg._bundles[canary_id].model_copy(update={"status": "QUALIFIED"})

    # 3. RLS violation (>0)
    c3 = CanaryController(release_registry=reg, baseline_bundle_id=baseline_id)
    c3.start_canary(canary_id)
    with pytest.raises(CanaryHealthFailedError):
        c3.evaluate_canary_health(canary_id, rls_violations=1)
    assert c3.traffic_percentage == 0

    # Reset quarantine
    reg._quarantine_reasons.clear()
    reg._bundles[canary_id] = reg._bundles[canary_id].model_copy(update={"status": "QUALIFIED"})

    # 4. Cost anomaly (>150%)
    c4 = CanaryController(release_registry=reg, baseline_bundle_id=baseline_id)
    c4.start_canary(canary_id)
    with pytest.raises(CanaryHealthFailedError):
        c4.evaluate_canary_health(canary_id, cost_burn_percent=180.0)
    assert c4.traffic_percentage == 0
