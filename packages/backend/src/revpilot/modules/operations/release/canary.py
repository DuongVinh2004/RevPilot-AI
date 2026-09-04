"""
RevPilot AI — Automated Canary Rollout & Health Evaluation Controller
Specification: docs/30-deployment/RELEASE-CANARY-ROLLBACK-SPEC.md §7, §9
Conforms to ADR-0008, INV-REL-001, AC-REL-02, AC-P08-003-02.
"""

from __future__ import annotations

from enum import Enum
import logging
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.modules.operations.release.manager import (
    CanaryHealthFailedError,
    ReleaseRegistry,
)
from revpilot.modules.operations.release.rollback import (
    RollbackCoordinator,
    RollbackSummary,
)

logger = logging.getLogger(__name__)


class CanaryStage(str, Enum):
    """Canary progressive rollout stages (§7)."""
    IDLE = "IDLE"
    CANARY_5 = "CANARY_5"
    CANARY_25 = "CANARY_25"
    GENERAL_100 = "GENERAL_100"
    ABORTED_ROLLED_BACK = "ABORTED_ROLLED_BACK"


class CanaryHealthVerdict(BaseModel):
    """Canary health status and metric breach telemetry."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    healthy: bool
    canary_bundle_id: str
    error_rate_5xx: float
    p95_latency_ms: float
    workflow_crashes: int
    rls_violations: int
    cost_burn_percent: float
    breaches: list[str] = Field(default_factory=list)


class CanaryController:
    """
    Manages progressive canary traffic shifting (5% -> 25% -> 100%) and continuously
    evaluates automated rollback triggers (5xx spikes, latency, crash loops, RLS violations).
    """

    def __init__(
        self,
        release_registry: ReleaseRegistry,
        rollback_coordinator: RollbackCoordinator | None = None,
        baseline_bundle_id: str = "bundle_baseline_stable_v1",
    ) -> None:
        self.registry = release_registry
        self.coordinator = rollback_coordinator or RollbackCoordinator()
        self.baseline_bundle_id = baseline_bundle_id

        self.current_stage: CanaryStage = CanaryStage.IDLE
        self.traffic_percentage: int = 0
        self.active_canary_bundle_id: str | None = None
        self.last_rollback_summary: RollbackSummary | None = None

    def start_canary(self, canary_bundle_id: str) -> None:
        """Admit bundle to Stage 1: 5% Canary rollout."""
        if self.registry.is_quarantined(canary_bundle_id):
            raise ValueError(f"Cannot deploy quarantined release bundle: {canary_bundle_id}")

        bundle = self.registry.get_bundle(canary_bundle_id)
        if not bundle:
            raise ValueError(f"Unknown release bundle: {canary_bundle_id}")

        self.active_canary_bundle_id = canary_bundle_id
        self.promote_canary_stage(canary_bundle_id, 5)

    def promote_canary_stage(self, canary_bundle_id: str, target_percentage: int) -> None:
        """Promote canary traffic percentage (5% -> 25% -> 100%)."""
        if self.registry.is_quarantined(canary_bundle_id):
            raise ValueError(f"Cannot promote quarantined release bundle: {canary_bundle_id}")

        if target_percentage == 5:
            self.current_stage = CanaryStage.CANARY_5
            self.traffic_percentage = 5
        elif target_percentage == 25:
            self.current_stage = CanaryStage.CANARY_25
            self.traffic_percentage = 25
        elif target_percentage == 100:
            self.current_stage = CanaryStage.GENERAL_100
            self.traffic_percentage = 100
        else:
            raise ValueError(f"Unsupported canary target percentage: {target_percentage} (must be 5, 25, or 100)")

        self.active_canary_bundle_id = canary_bundle_id
        logger.info(
            "CANARY_STAGE_PROMOTED: bundle=%s stage=%s traffic=%d%%",
            canary_bundle_id,
            self.current_stage.value,
            self.traffic_percentage,
        )

    def evaluate_canary_health(
        self,
        canary_bundle_id: str,
        error_rate_5xx: float = 0.0,
        p95_latency_ms: float = 200.0,
        baseline_p95_ms: float = 200.0,
        workflow_crashes: int = 0,
        rls_violations: int = 0,
        cost_burn_percent: float = 100.0,
        auto_rollback: bool = True,
    ) -> CanaryHealthVerdict:
        """
        Evaluate canary health metrics against automated rollback triggers (§7.1).
        If any trigger fires and auto_rollback=True, immediately aborts and rolls back to baseline.
        """
        breaches: list[str] = []

        # 1. HTTP 5xx Spike: > 0.5% (0.005)
        if error_rate_5xx > 0.005:
            breaches.append(f"HTTP 5xx rate {error_rate_5xx:.4f} breached 0.005 (0.5%) ceiling")

        # 2. P95 Latency Degradation: > 25% over baseline
        latency_ceiling = baseline_p95_ms * 1.25
        if p95_latency_ms > latency_ceiling:
            breaches.append(
                f"P95 latency {p95_latency_ms:.1f}ms degraded >25% over baseline {baseline_p95_ms:.1f}ms "
                f"(ceiling {latency_ceiling:.1f}ms)"
            )

        # 3. Workflow Crash Loop: > 0
        if workflow_crashes > 0:
            breaches.append(f"Temporal worker unhandled crash count {workflow_crashes} > 0")

        # 4. Tenant Isolation Breach: > 0
        if rls_violations > 0:
            breaches.append(f"Cross-tenant RLS violation alarms {rls_violations} > 0")

        # 5. Cost Anomaly: > 150%
        if cost_burn_percent > 150.0:
            breaches.append(f"Token spend rate {cost_burn_percent:.1f}% exceeded 150% budget threshold")

        healthy = len(breaches) == 0

        verdict = CanaryHealthVerdict(
            healthy=healthy,
            canary_bundle_id=canary_bundle_id,
            error_rate_5xx=error_rate_5xx,
            p95_latency_ms=p95_latency_ms,
            workflow_crashes=workflow_crashes,
            rls_violations=rls_violations,
            cost_burn_percent=cost_burn_percent,
            breaches=breaches,
        )

        if not healthy and auto_rollback:
            reason = f"Canary health check breached: {'; '.join(breaches)}"
            self.abort_and_rollback(canary_bundle_id, reason)
            raise CanaryHealthFailedError(
                f"Canary health check failed: {'; '.join(breaches)}",
                details={
                    "canary_bundle_id": canary_bundle_id,
                    "breaches": breaches,
                    "error_rate_5xx": error_rate_5xx,
                },
            )

        return verdict

    def abort_and_rollback(self, canary_bundle_id: str, reason: str) -> RollbackSummary:
        """
        Abort canary deployment, zero traffic routing (<30s), execute multi-tier rollback (<60s),
        and quarantine failed release bundle (§8, §9).
        """
        logger.warning("CANARY_ABORT_TRIGGERED: bundle=%s reason=%s", canary_bundle_id, reason)

        # 1. Zero out canary traffic immediately
        self.traffic_percentage = 0
        self.current_stage = CanaryStage.ABORTED_ROLLED_BACK

        # 2. Mark bundle as QUARANTINED in registry
        self.registry.quarantine_bundle(canary_bundle_id, reason)

        # 3. Execute coordinated multi-tier rollback sequence
        summary = self.coordinator.execute_coordinated_rollback(
            canary_bundle_id=canary_bundle_id,
            baseline_bundle_id=self.baseline_bundle_id,
            reason=reason,
        )
        self.last_rollback_summary = summary

        logger.info(
            "CANARY_ROLLBACK_COMPLETE: rollback_id=%s total_duration=%.3fs",
            summary.rollback_id,
            summary.total_duration_sec,
        )
        return summary
