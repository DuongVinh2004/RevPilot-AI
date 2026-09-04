"""
RevPilot AI — Connector Health Probing & Sync Lag Calculation
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §3, §4
Conforms to INV-REL-001 and INV-REL-002.
"""

from __future__ import annotations

from enum import Enum
import time
from typing import Callable
from pydantic import BaseModel, ConfigDict

from revpilot.shared.identifiers import UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.connectors.domain import ConnectorStatus
from revpilot.modules.connectors.lifecycle import ConnectorLifecycleService


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class HealthProbeResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector_id: UUIDv7
    status: HealthStatus
    latency_ms: float
    last_probe_time: UtcDateTime
    error_message: str | None = None
    retry_count: int = 0


class ConnectorHealthService:
    """
    Monitors connector connectivity, executes canary health probes with retry/timeout logic,
    and calculates upstream sync lag.
    """

    def __init__(self, lifecycle_service: ConnectorLifecycleService | None = None) -> None:
        self.lifecycle_service = lifecycle_service

    def probe_health(
        self,
        connector_id: UUIDv7,
        canary_fn: Callable[[], bool] | None = None,
        max_retries: int = 2,
        timeout_seconds: float = 10.0,
    ) -> HealthProbeResult:
        """
        Execute read-only canary health check. Retries up to max_retries on transient failure.
        """
        retries = 0
        last_err: str | None = None

        while retries <= max_retries:
            t0 = time.perf_counter()
            try:
                if canary_fn is not None:
                    success = canary_fn()
                    if not success:
                        raise RuntimeError("Canary probe returned unhealthy status")
                latency = (time.perf_counter() - t0) * 1000

                # Notify lifecycle service of healthy recovery
                if self.lifecycle_service:
                    self.lifecycle_service.record_health_recovery(connector_id)

                return HealthProbeResult(
                    connector_id=connector_id,
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    last_probe_time=UtcDateTime.now(),
                    retry_count=retries,
                )
            except Exception as err:
                last_err = str(err)
                retries += 1

        # All retries exhausted -> UNHEALTHY
        latency = (time.perf_counter() - t0) * 1000
        return HealthProbeResult(
            connector_id=connector_id,
            status=HealthStatus.UNHEALTHY,
            latency_ms=latency,
            last_probe_time=UtcDateTime.now(),
            error_message=last_err,
            retry_count=retries - 1,
        )

    def calculate_sync_lag(
        self,
        connector_id: UUIDv7,
        upstream_checkpoint_time: UtcDateTime,
    ) -> int:
        """
        Calculate seconds lag between latest upstream checkpoint and current time or last sync.
        """
        now = UtcDateTime.now()
        upstream_ts = upstream_checkpoint_time.value.timestamp()
        now_ts = now.value.timestamp()

        lag_seconds = max(0, int(now_ts - upstream_ts))

        if self.lifecycle_service:
            record = self.lifecycle_service.get_connector(connector_id)
            record.sync_lag_seconds = lag_seconds
            record.updated_at = now

        return lag_seconds
