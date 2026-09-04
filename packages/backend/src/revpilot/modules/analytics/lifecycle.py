"""
RevPilot AI — Anomaly Lifecycle Aggregate, State Machine, and Outbox Contracts (Phase 02)
Implements the 7-state Anomaly aggregate lifecycle, deterministic state machine enforcement,
immutable transition auditing, and transactional outbox event emission.
Conforms to ANOMALY-DOMAIN-SPEC.md §4, EVENT-CONTRACTS.md §4, and TASK-P02-005.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import PrincipalContext
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure


# =============================================================================
# Lifecycle State Enumeration
# =============================================================================

class AnomalyState(str, Enum):
    """
    Deterministic lifecycle states for revenue anomaly aggregates.
    Conforms to ANOMALY-DOMAIN-SPEC.md §4 and TASK-P02-005.
    """
    DETECTED = "DETECTED"
    VALIDATED = "VALIDATED"
    LOCALIZED = "LOCALIZED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    SUPPRESSED = "SUPPRESSED"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"


# =============================================================================
# Error Contract Hierarchy
# =============================================================================

class LifecycleError(DomainError):
    """Base domain exception for anomaly lifecycle operations."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=retryable)
        self.http_status = http_status


class InvalidStateTransitionError(LifecycleError):
    """Raised when state transition is not permitted by state machine (HTTP 409)."""

    def __init__(
        self,
        message: str = "Transition not allowed from current state",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INVALID_STATE_TRANSITION",
            message=message,
            http_status=409,
            details=details,
            retryable=False,
        )


class AnomalyAlreadyResolvedError(LifecycleError):
    """Raised when mutation attempted on closed resolved anomaly without reopening (HTTP 409)."""

    def __init__(
        self,
        message: str = "Anomaly is in terminal resolved state",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ANOMALY_ALREADY_RESOLVED",
            message=message,
            http_status=409,
            details=details,
            retryable=False,
        )


# =============================================================================
# Transition Audit and Outbox Event Models
# =============================================================================

@dataclass(frozen=True, slots=True)
class AnomalyTransitionRecord:
    """
    Immutable audit record documenting a single state transition on an anomaly aggregate.
    Conforms to ANOMALY-DOMAIN-SPEC.md §4.1, INV-AUD-001, and TASK-P02-005.
    """
    transition_id: str
    tenant_id: TenantId
    anomaly_id: str
    from_state: AnomalyState
    to_state: AnomalyState
    actor_id: str
    actor_type: str
    reason: str
    metadata: dict[str, Any]
    transitioned_at: UtcDateTime


@dataclass(frozen=True, slots=True)
class OutboxDomainEvent:
    """
    Transactional outbox domain event payload conforming to EVENT-CONTRACTS.md §4.
    Emitted atomically within aggregate transition boundaries.
    """
    event_id: str
    event_type: str
    event_version: int
    occurred_at: UtcDateTime
    producer: str
    aggregate_id: str
    aggregate_version: int
    tenant_id: TenantId
    correlation_id: str
    causation_id: str
    idempotency_key: str
    payload: dict[str, Any]


# =============================================================================
# Anomaly Aggregate
# =============================================================================

_LEGAL_TRANSITIONS: dict[AnomalyState, set[AnomalyState]] = {
    AnomalyState.DETECTED: {AnomalyState.VALIDATED, AnomalyState.SUPPRESSED},
    AnomalyState.VALIDATED: {AnomalyState.LOCALIZED, AnomalyState.SUPPRESSED},
    AnomalyState.LOCALIZED: {AnomalyState.ACKNOWLEDGED, AnomalyState.SUPPRESSED},
    AnomalyState.ACKNOWLEDGED: {AnomalyState.RESOLVED, AnomalyState.SUPPRESSED},
    AnomalyState.SUPPRESSED: set(),  # Terminal state
    AnomalyState.RESOLVED: {AnomalyState.REOPENED},
    AnomalyState.REOPENED: {
        AnomalyState.LOCALIZED,
        AnomalyState.ACKNOWLEDGED,
        AnomalyState.RESOLVED,
        AnomalyState.SUPPRESSED,
    },
}

_EVENT_TYPE_MAPPING: dict[AnomalyState, str] = {
    AnomalyState.DETECTED: "anomaly.detected.v1",
    AnomalyState.VALIDATED: "anomaly.validated.v1",
    AnomalyState.LOCALIZED: "anomaly.localized.v1",
    AnomalyState.ACKNOWLEDGED: "anomaly.acknowledged.v1",
    AnomalyState.SUPPRESSED: "anomaly.suppressed.v1",
    AnomalyState.RESOLVED: "anomaly.resolved.v1",
    AnomalyState.REOPENED: "anomaly.reopened.v1",
}


@dataclass
class AnomalyAggregate:
    """
    Authoritative domain aggregate for revenue anomaly lifecycles.
    Enforces deterministic state machine transitions, immutable transition records,
    atomic outbox event publishing, and supersession watermarking.
    Conforms to ANOMALY-DOMAIN-SPEC.md §2, §4 and TASK-P02-005.
    """
    id: str
    tenant_id: TenantId
    metric_id: str
    metric_version: str
    detector_id: str
    detector_version: str
    baseline_id: str
    baseline_version: str
    observation_window_start: UtcDateTime
    observation_window_end: UtcDateTime
    as_of_time: UtcDateTime
    actual_value: float
    expected_value: float
    expected_interval: tuple[float, float]
    anomaly_score: float
    severity: str
    state: AnomalyState = AnomalyState.DETECTED
    affected_scope: dict[str, str] = field(default_factory=dict)
    data_freshness: str = "FRESH"
    data_quality_state: str = "PASSED"
    confidence: float = 1.0
    version: int = 1
    effective_from: UtcDateTime = field(default_factory=UtcDateTime.now)
    effective_to: Optional[UtcDateTime] = None
    suppression_reason: Optional[str] = None
    created_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    updated_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    transitions: list[AnomalyTransitionRecord] = field(default_factory=list)
    pending_outbox_events: list[OutboxDomainEvent] = field(default_factory=list)

    @classmethod
    def create_detected(
        cls,
        id: str,
        tenant_id: TenantId,
        metric_id: str,
        metric_version: str,
        detector_id: str,
        detector_version: str,
        baseline_id: str,
        baseline_version: str,
        observation_window_start: UtcDateTime,
        observation_window_end: UtcDateTime,
        as_of_time: UtcDateTime,
        actual_value: float,
        expected_value: float,
        expected_interval: tuple[float, float],
        anomaly_score: float,
        severity: str,
        affected_scope: dict[str, str] | None = None,
        created_at: UtcDateTime | None = None,
        actor: PrincipalContext | None = None,
    ) -> AnomalyAggregate:
        """Factory initializing a new AnomalyAggregate in DETECTED state with initial audit record."""
        now = created_at or UtcDateTime.now()
        aggregate = cls(
            id=id,
            tenant_id=tenant_id,
            metric_id=metric_id,
            metric_version=metric_version,
            detector_id=detector_id,
            detector_version=detector_version,
            baseline_id=baseline_id,
            baseline_version=baseline_version,
            observation_window_start=observation_window_start,
            observation_window_end=observation_window_end,
            as_of_time=as_of_time,
            actual_value=actual_value,
            expected_value=expected_value,
            expected_interval=expected_interval,
            anomaly_score=anomaly_score,
            severity=severity,
            state=AnomalyState.DETECTED,
            affected_scope=affected_scope or {},
            effective_from=now,
            created_at=now,
            updated_at=now,
            version=1,
        )

        # Record initial DETECTED transition
        actor_id = actor.principal_id.value if actor else "system_detector_worker"
        actor_type = "PRINCIPAL" if (actor and not actor.is_system) else "SYSTEM_WORKER"
        trans_rec = AnomalyTransitionRecord(
            transition_id=f"trn_{uuid4().hex[:16]}",
            tenant_id=tenant_id,
            anomaly_id=id,
            from_state=AnomalyState.DETECTED,  # Initial state
            to_state=AnomalyState.DETECTED,
            actor_id=actor_id,
            actor_type=actor_type,
            reason="INITIAL_DETECTION",
            metadata={
                "actual_value": actual_value,
                "expected_value": expected_value,
                "anomaly_score": anomaly_score,
            },
            transitioned_at=now,
        )
        aggregate.transitions.append(trans_rec)

        # Enqueue initial anomaly.detected.v1 event
        event = OutboxDomainEvent(
            event_id=f"evt_{uuid4().hex[:16]}",
            event_type="anomaly.detected.v1",
            event_version=1,
            occurred_at=now,
            producer="revpilot.modules.analytics",
            aggregate_id=id,
            aggregate_version=1,
            tenant_id=tenant_id,
            correlation_id=f"cor_{uuid4().hex[:16]}",
            causation_id=f"det_{detector_id}",
            idempotency_key=f"anm_detect_{id}_v1",
            payload={
                "anomaly_id": id,
                "metric_id": metric_id,
                "metric_version": metric_version,
                "detector_id": detector_id,
                "actual_value": actual_value,
                "expected_value": expected_value,
                "expected_interval": list(expected_interval),
                "anomaly_score": anomaly_score,
                "severity": severity,
                "observation_window": {
                    "start_time": observation_window_start.isoformat(),
                    "end_time": observation_window_end.isoformat(),
                },
                "as_of_time": as_of_time.isoformat(),
            },
        )
        aggregate.pending_outbox_events.append(event)
        return aggregate

    def transition_to(
        self,
        target_state: AnomalyState,
        actor: PrincipalContext,
        reason: str,
        metadata: dict[str, Any] | None = None,
        transitioned_at: UtcDateTime | None = None,
    ) -> Result[AnomalyTransitionRecord, LifecycleError]:
        """
        Transition anomaly aggregate to target state with atomic auditing and outbox emission.
        Enforces INV-TEN-001, INV-AUD-001, and deterministic state machine rules.
        """
        # 1. Tenancy validation (INV-TEN-001)
        if not isinstance(actor, PrincipalContext):
            return Failure(
                LifecycleError(
                    code="UNAUTHORIZED",
                    message="Valid PrincipalContext required for anomaly lifecycle transitions",
                    http_status=401,
                )
            )

        if not actor.is_system and actor.tenant_id != self.tenant_id:
            return Failure(
                LifecycleError(
                    code="TENANCY_VIOLATION",
                    message=(
                        f"Cross-tenant transition denied: Actor tenant '{actor.tenant_id}' "
                        f"does not match anomaly tenant '{self.tenant_id}'"
                    ),
                    http_status=403,
                    details={
                        "actor_tenant": str(actor.tenant_id),
                        "anomaly_tenant": str(self.tenant_id),
                    },
                )
            )

        # 2. State machine checks
        current_state = self.state

        # Check terminal RESOLVED state guard
        if current_state == AnomalyState.RESOLVED and target_state != AnomalyState.REOPENED:
            return Failure(
                AnomalyAlreadyResolvedError(
                    "Anomaly is in terminal resolved state; must be REOPENED before further mutation",
                    details={
                        "current_state": current_state.value,
                        "target_state": target_state.value,
                        "anomaly_id": self.id,
                    },
                )
            )

        # Check legal transitions
        legal_targets = _LEGAL_TRANSITIONS.get(current_state, set())
        if target_state not in legal_targets:
            return Failure(
                InvalidStateTransitionError(
                    f"Transition from '{current_state.value}' to '{target_state.value}' is not permitted",
                    details={
                        "from_state": current_state.value,
                        "to_state": target_state.value,
                        "allowed_transitions": [s.value for s in legal_targets],
                        "anomaly_id": self.id,
                    },
                )
            )

        now = transitioned_at or UtcDateTime.now()
        meta = metadata or {}

        # 3. Apply state mutation
        from_state = self.state
        self.state = target_state
        self.version += 1
        self.updated_at = now

        # Specific state side-effects
        if target_state == AnomalyState.SUPPRESSED:
            self.suppression_reason = reason
            self.effective_to = now
        elif target_state == AnomalyState.RESOLVED:
            self.effective_to = now

        # 4. Record immutable audit record (INV-AUD-001)
        actor_id = actor.principal_id.value
        actor_type = "SYSTEM_WORKER" if actor.is_system else "PRINCIPAL"

        trans_rec = AnomalyTransitionRecord(
            transition_id=f"trn_{uuid4().hex[:16]}",
            tenant_id=self.tenant_id,
            anomaly_id=self.id,
            from_state=from_state,
            to_state=target_state,
            actor_id=actor_id,
            actor_type=actor_type,
            reason=reason,
            metadata=meta,
            transitioned_at=now,
        )
        self.transitions.append(trans_rec)

        # 5. Enqueue transactional outbox event (EVENT-CONTRACTS.md §4)
        event_type = _EVENT_TYPE_MAPPING[target_state]
        payload = self._build_event_payload(target_state, reason, meta, actor, now)

        outbox_event = OutboxDomainEvent(
            event_id=f"evt_{uuid4().hex[:16]}",
            event_type=event_type,
            event_version=1,
            occurred_at=now,
            producer="revpilot.modules.analytics",
            aggregate_id=self.id,
            aggregate_version=self.version,
            tenant_id=self.tenant_id,
            correlation_id=meta.get("correlation_id", f"cor_{uuid4().hex[:16]}"),
            causation_id=meta.get("causation_id", f"trn_{trans_rec.transition_id}"),
            idempotency_key=f"anm_{self.id}_{target_state.value.lower()}_v{self.version}",
            payload=payload,
        )
        self.pending_outbox_events.append(outbox_event)

        return Success(trans_rec)

    def _build_event_payload(
        self,
        state: AnomalyState,
        reason: str,
        metadata: dict[str, Any],
        actor: PrincipalContext,
        now: UtcDateTime,
    ) -> dict[str, Any]:
        """Construct strongly-typed payload adhering to EVENT-CONTRACTS.md §4."""
        base = {"anomaly_id": self.id}
        if state == AnomalyState.VALIDATED:
            return {
                **base,
                "data_quality_state": self.data_quality_state,
                "freshness_state": self.data_freshness,
                "validated_at": now.isoformat(),
            }
        elif state == AnomalyState.LOCALIZED:
            return {
                **base,
                "top_contributing_segments": metadata.get("top_contributing_segments", []),
                "primary_dimension": metadata.get("dimension", ""),
                "data_coverage_pct": metadata.get("data_coverage_pct", 100.0),
            }
        elif state == AnomalyState.ACKNOWLEDGED:
            return {
                **base,
                "acknowledged_by_principal": actor.principal_id.value,
                "investigation_id": metadata.get("investigation_id", ""),
                "acknowledged_at": now.isoformat(),
            }
        elif state == AnomalyState.SUPPRESSED:
            return {
                **base,
                "suppression_reason": reason,
                "suppression_rule_id": metadata.get("suppression_rule_id", ""),
                "suppressed_at": now.isoformat(),
            }
        elif state == AnomalyState.RESOLVED:
            return {
                **base,
                "resolution_type": metadata.get("resolution_type", "INCIDENT_SUBSIDED"),
                "resolved_at": now.isoformat(),
                "final_metric_value": metadata.get("final_metric_value", self.actual_value),
            }
        elif state == AnomalyState.REOPENED:
            return {
                **base,
                "reopened_at": now.isoformat(),
                "new_actual_value": metadata.get("new_actual_value", self.actual_value),
                "trigger_score": metadata.get("trigger_score", self.anomaly_score),
            }
        return base


__all__ = [
    "AnomalyState",
    "AnomalyTransitionRecord",
    "OutboxDomainEvent",
    "AnomalyAggregate",
    "LifecycleError",
    "InvalidStateTransitionError",
    "AnomalyAlreadyResolvedError",
]
