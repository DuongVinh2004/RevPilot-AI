"""
RevPilot AI — Connector Rate Limit Degradation & Health Probing Test
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §3.1, §4
Conforms to INV-REL-001 and INV-REL-002.
"""

from __future__ import annotations
from datetime import timedelta
import sys
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.security.secrets.broker import SecretReference


@pytest.fixture(autouse=True)
def _isolate_connectors_module():
    """Ensure connectors module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.connectors"):
            sys.modules.pop(mod, None)


def test_connector_rate_limit_degradation_and_health_recovery():
    """
    Verifies automatic degradation when rate limit thresholds are exceeded (>= 3 consecutive 429s),
    sync lag calculation, and automated recovery to ACTIVE when health probe succeeds.
    """
    from revpilot.modules.connectors import (
        ConnectorLifecycleService,
        ConnectorHealthService,
        ConnectorStatus,
        HealthStatus,
    )

    service = ConnectorLifecycleService()
    health_service = ConnectorHealthService(lifecycle_service=service)

    tenant_id = TenantId.generate()
    secret_ref = SecretReference.generate()

    # 1. Initialize Active Connector
    cid = service.register_connector(
        tenant_id=tenant_id,
        provider="hubspot",
        capability="crm_sync",
    )
    service.configure_credentials(cid, secret_ref=secret_ref, scopes=["contacts:read"])
    service.validate_connectivity(cid, probe_fn=lambda: True)

    rec = service.get_connector(cid)
    assert rec.status == ConnectorStatus.ACTIVE

    # 2. Simulate 429 Rate Limits
    # 1st 429: Remains ACTIVE
    service.record_rate_limit(cid)
    assert rec.status == ConnectorStatus.ACTIVE
    assert rec.consecutive_rate_limits == 1

    # 2nd 429: Remains ACTIVE
    service.record_rate_limit(cid)
    assert rec.status == ConnectorStatus.ACTIVE
    assert rec.consecutive_rate_limits == 2

    # 3rd 429: Exceeds threshold -> Transitions to DEGRADED
    service.record_rate_limit(cid)
    assert rec.status == ConnectorStatus.DEGRADED
    assert "rate limit" in (rec.status_reason or "").lower()

    # 3. Verify Sync Lag Calculation
    now = UtcDateTime.now()
    older_checkpoint = UtcDateTime(now.value - timedelta(seconds=185))
    lag = health_service.calculate_sync_lag(cid, upstream_checkpoint_time=older_checkpoint)
    assert lag >= 180
    assert rec.sync_lag_seconds >= 180

    # 4. Probe Health with Transient Flake and Successful Retry
    attempts = [0]

    def flaky_canary():
        attempts[0] += 1
        if attempts[0] == 1:
            raise ConnectionError("Transient upstream timeout")
        return True

    probe_res = health_service.probe_health(cid, canary_fn=flaky_canary, max_retries=2)
    assert probe_res.status == HealthStatus.HEALTHY
    assert probe_res.retry_count == 1

    # 5. Automated Recovery to ACTIVE
    assert rec.status == ConnectorStatus.ACTIVE
    assert rec.consecutive_rate_limits == 0
    assert "recovered" in (rec.status_reason or "").lower()
