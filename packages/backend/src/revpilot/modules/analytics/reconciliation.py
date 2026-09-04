"""
RevPilot AI — Late-Event Anomaly Reconciliation and Replay Engine (Phase 02)
Re-evaluates active anomaly aggregates when late-arriving canonical data arrives,
superseding invalid anomalies to SUPPRESSED with full audit trails while preserving immutable history.
Conforms to DATA-QUALITY-LINEAGE-SPEC.md §7.2, INV-DATA-002, and TASK-P02-005.
"""

from __future__ import annotations
from typing import Optional, Sequence
from uuid import uuid4

from revpilot.shared.identifiers import TenantId, PrincipalId, OrganizationId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import PrincipalContext, TenantContext
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure

from revpilot.modules.analytics.schemas import (
    TimeWindow,
    MetricQueryRequest,
)
from revpilot.modules.analytics.metrics.definitions import MetricEvaluationDataset
from revpilot.modules.analytics.metrics.registry import (
    MetricRegistry,
    CANONICAL_METRIC_REGISTRY,
)
from revpilot.modules.analytics.metric_service import MetricService
from revpilot.modules.analytics.lifecycle import (
    AnomalyAggregate,
    AnomalyState,
    LifecycleError,
)


class ReconciliationEngine:
    """
    Reconciliation and replay engine for late-arriving event processing.
    Evaluates trailing volatility windows and executes supersession without silent mutation.
    Conforms to INV-DATA-002 and DATA-QUALITY-LINEAGE-SPEC.md §7.2.
    """

    def __init__(
        self,
        metric_service: MetricService | None = None,
        registry: MetricRegistry | None = None,
        dataset: MetricEvaluationDataset | None = None,
    ) -> None:
        self._registry = registry or CANONICAL_METRIC_REGISTRY
        self._metric_service = metric_service or MetricService(dataset=dataset, registry=self._registry)
        if dataset is not None and metric_service is not None:
            self._metric_service.set_dataset(dataset)
        self._store: dict[str, AnomalyAggregate] = {}

    def set_dataset(self, dataset: MetricEvaluationDataset) -> None:
        """Update dataset in metric service."""
        self._metric_service.set_dataset(dataset)

    def register_anomaly(self, anomaly: AnomalyAggregate) -> None:
        """Register an active anomaly in the reconciliation store."""
        if not isinstance(anomaly, AnomalyAggregate):
            raise TypeError(f"anomaly must be AnomalyAggregate, got {type(anomaly).__name__}")
        self._store[anomaly.id] = anomaly

    def get_anomaly(self, anomaly_id: str) -> Optional[AnomalyAggregate]:
        """Retrieve stored anomaly by identifier."""
        return self._store.get(anomaly_id)

    def list_anomalies(self, tenant_id: TenantId | None = None) -> list[AnomalyAggregate]:
        """List all registered anomalies, optionally filtered by tenant."""
        if tenant_id is None:
            return list(self._store.values())
        return [a for a in self._store.values() if a.tenant_id == tenant_id]

    def reconcile_window(
        self,
        tenant_id: TenantId,
        metric_id: str,
        affected_window: TimeWindow,
        as_of: UtcDateTime | None = None,
        actor: PrincipalContext | None = None,
        dataset: MetricEvaluationDataset | None = None,
    ) -> list[AnomalyAggregate]:
        """
        Reconcile all active anomalies overlapping the affected window after late event arrival.
        Transitions superseded anomalies to SUPPRESSED with reason 'SUPERSEDED_BY_RECOMPUTATION'.
        Conforms to DATA-QUALITY-LINEAGE-SPEC.md §7.2 and INV-DATA-002.
        """
        reconciliation_time = as_of or UtcDateTime.now()
        system_actor = actor or PrincipalContext(
            principal_id=PrincipalId("usr_sys_reconciliation_worker"),
            tenant_id=tenant_id,
            is_system=True,
        )
        org_suffix = str(tenant_id).removeprefix("tnt_")
        tenant_context = TenantContext(
            tenant_id=tenant_id,
            organization_id=OrganizationId(f"org_{org_suffix}"),
        )

        # 1. Identify active candidates in the affected window
        affected_anomalies: list[AnomalyAggregate] = []
        win_s = affected_window.start_time.value
        win_e = affected_window.end_time.value

        for anomaly in self._store.values():
            if anomaly.tenant_id != tenant_id:
                continue
            if anomaly.metric_id != metric_id:
                continue
            if anomaly.state == AnomalyState.SUPPRESSED:
                continue  # Already superseded or suppressed

            # Overlap check
            anm_s = anomaly.observation_window_start.value
            anm_e = anomaly.observation_window_end.value
            if max(anm_s, win_s) <= min(anm_e, win_e):
                affected_anomalies.append(anomaly)

        # 2. Recompute each overlapping anomaly
        for anomaly in affected_anomalies:
            # Mark data freshness as RECALCULATING per DATA-QUALITY-LINEAGE-SPEC.md §7.2.3
            anomaly.data_freshness = "RECALCULATING"

            query_req = MetricQueryRequest(
                metric_id=anomaly.metric_id,
                metric_version=anomaly.metric_version,
                time_window=TimeWindow(
                    start_time=anomaly.observation_window_start,
                    end_time=anomaly.observation_window_end,
                ),
                grain="AS_OF_SNAPSHOT",
                filters=dict(anomaly.affected_scope),
                as_of_time=reconciliation_time,
            )

            query_res = self._metric_service.query(query_req, tenant_context, dataset=dataset)
            if query_res.is_failure:
                # If query fails, revert freshness to DEGRADED
                anomaly.data_freshness = "DEGRADED"
                continue

            query_resp = query_res.unwrap()
            recalculated_val = query_resp.series[0].actual_value if query_resp.series else 0.0

            # 3. Determine if metric still breaches upper prediction interval bound
            # Ratio and volume anomaly triggers rely on expected_interval upper bound
            lower_bound, upper_bound = anomaly.expected_interval
            is_still_anomalous = recalculated_val > upper_bound or (
                lower_bound > 0.0 and recalculated_val < lower_bound
            )

            if not is_still_anomalous:
                # Metric returned to normal: supersede anomaly (DATA-QUALITY-LINEAGE-SPEC.md §7.2.2)
                # Transition to SUPPRESSED with atomic outbox event emission
                # If state is already ACKNOWLEDGED, transition through RESOLVED or directly to SUPPRESSED
                target_state = AnomalyState.SUPPRESSED
                # Check if current state allows SUPPRESSED transition
                if anomaly.state in (
                    AnomalyState.DETECTED,
                    AnomalyState.VALIDATED,
                    AnomalyState.LOCALIZED,
                    AnomalyState.ACKNOWLEDGED,
                    AnomalyState.REOPENED,
                ):
                    trans_res = anomaly.transition_to(
                        target_state=target_state,
                        actor=system_actor,
                        reason="SUPERSEDED_BY_RECOMPUTATION",
                        metadata={
                            "recalculated_value": recalculated_val,
                            "previous_value": anomaly.actual_value,
                            "upper_bound": upper_bound,
                            "reconciliation_time": reconciliation_time.isoformat(),
                        },
                        transitioned_at=reconciliation_time,
                    )
                anomaly.data_freshness = "FRESH"
            else:
                # Still anomalous: update observed value and restore freshness
                anomaly.actual_value = recalculated_val
                anomaly.data_freshness = "FRESH"

        return affected_anomalies


__all__ = ["ReconciliationEngine"]
