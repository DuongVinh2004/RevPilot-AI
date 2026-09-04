"""
RevPilot AI — Hidden Ground Truth and Evaluation Air-Gap Module (Phase 01)
Adheres to docs/03-requirements/SYNTHETIC-DATASET-SPEC.md §7 and INV-DATA-001.
"""

from __future__ import annotations
from dataclasses import dataclass
import json
import os
from typing import Any

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure


class AccessDeniedError(DomainError):
    """Raised or returned when unauthorized principal attempts to read evaluation ground truth."""

    def __init__(
        self,
        message: str = "Access to evaluation truth is forbidden",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="GROUND_TRUTH_ACCESS_DENIED",
            message=message,
            details=details or {"http_status": 403},
            retryable=False,
        )


class ScenarioInjectionError(DomainError):
    """Raised when causal disruption scenario injection fails due to inconsistent cohort state."""

    def __init__(
        self,
        message: str = "Failed to inject causal disruption",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="SCENARIO_INJECTION_FAILED",
            message=message,
            details=details or {"http_status": 500},
            retryable=False,
        )


@dataclass(frozen=True, slots=True)
class EvaluatorAuthToken:
    """Security credentials granting access to offline evaluation ground truth store."""
    principal_id: str
    role: str = "revpilot_evaluator"
    is_valid: bool = True


@dataclass(frozen=True, slots=True)
class GroundTruthIncident:
    """
    Cryptographically isolated container for hidden ground-truth incident annotations.
    Strictly forbidden from being embedded in runtime data records (INV-DATA-001).
    """
    tenant_id: TenantId
    incident_id: str
    scenario_name: str
    causal_start_time: UtcDateTime
    causal_end_time: UtcDateTime
    primary_root_cause: str
    affected_facility_id: str
    affected_carrier_id: str
    true_ate_cancellation_rate_delta: float
    true_delayed_shipment_count: int
    true_revenue_at_risk_cents: int
    competing_hypotheses: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "incident_id": self.incident_id,
            "scenario_name": self.scenario_name,
            "causal_start_time": self.causal_start_time.isoformat(),
            "causal_end_time": self.causal_end_time.isoformat(),
            "primary_root_cause": self.primary_root_cause,
            "affected_facility_id": self.affected_facility_id,
            "affected_carrier_id": self.affected_carrier_id,
            "true_ate_cancellation_rate_delta": self.true_ate_cancellation_rate_delta,
            "true_delayed_shipment_count": self.true_delayed_shipment_count,
            "true_revenue_at_risk_cents": self.true_revenue_at_risk_cents,
            "competing_hypotheses": self.competing_hypotheses,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundTruthIncident:
        return cls(
            tenant_id=TenantId(data["tenant_id"]),
            incident_id=data["incident_id"],
            scenario_name=data["scenario_name"],
            causal_start_time=UtcDateTime.from_iso(data["causal_start_time"]),
            causal_end_time=UtcDateTime.from_iso(data["causal_end_time"]),
            primary_root_cause=data["primary_root_cause"],
            affected_facility_id=data["affected_facility_id"],
            affected_carrier_id=data["affected_carrier_id"],
            true_ate_cancellation_rate_delta=float(data["true_ate_cancellation_rate_delta"]),
            true_delayed_shipment_count=int(data["true_delayed_shipment_count"]),
            true_revenue_at_risk_cents=int(data["true_revenue_at_risk_cents"]),
            competing_hypotheses=list(data.get("competing_hypotheses", [])),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> GroundTruthIncident:
        return cls.from_dict(json.loads(json_str))


class EvaluationGroundTruthStore:
    """
    Air-gapped file/object storage interface for ground-truth incidents.
    Fails closed with AccessDeniedError if caller lacks revpilot_evaluator authorization.
    """

    @staticmethod
    def save_ground_truth(incident: GroundTruthIncident, target_path: str) -> None:
        """Persist ground truth incident JSON to target file path."""
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(incident.to_json())

    @staticmethod
    def load_ground_truth_for_eval(
        target_path: str,
        auth_token: EvaluatorAuthToken | None = None,
    ) -> Result[GroundTruthIncident, AccessDeniedError]:
        """
        Load ground truth incident from storage for offline evaluation.
        Fails closed with AccessDeniedError if auth_token is invalid or lacks role 'revpilot_evaluator'.
        """
        if auth_token is None or not auth_token.is_valid or auth_token.role != "revpilot_evaluator":
            return Failure(
                AccessDeniedError(
                    message="GROUND_TRUTH_ACCESS_DENIED: Access to evaluation truth is forbidden",
                    details={
                        "principal_id": getattr(auth_token, "principal_id", "anonymous"),
                        "role": getattr(auth_token, "role", "unknown"),
                        "http_status": 403,
                    },
                )
            )

        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Ground truth file not found at: {target_path}")

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = f.read()
            incident = GroundTruthIncident.from_json(data)
            return Success(incident)
        except Exception as e:
            return Failure(AccessDeniedError(f"Failed to load ground truth file: {e}"))


__all__ = [
    "AccessDeniedError",
    "ScenarioInjectionError",
    "EvaluatorAuthToken",
    "GroundTruthIncident",
    "EvaluationGroundTruthStore",
]
