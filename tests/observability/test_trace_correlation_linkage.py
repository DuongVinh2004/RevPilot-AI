"""
RevPilot AI — Tests: Distributed Trace Correlation Linkage & SLI Metrics
Specification: docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md §7, §8
Conforms to NFR-OBS-001, NFR-AVL-001, TC-P08-016, TC-P08-017, AC-P08-002-02.
"""

from __future__ import annotations

import pytest

from revpilot.modules.observability.telemetry.pipeline import (
    ALERT_ROUTING_POLICIES,
    AlertSeverity,
    TelemetryPipeline,
)
from revpilot.modules.observability.telemetry.scrubber import (
    CardinalityLimitExceededError,
    TelemetryScrubber,
)
from revpilot.modules.observability.telemetry.sli_exporter import (
    MAX_TRACKED_ENDPOINTS,
    MAX_TRACKED_TENANTS,
    SliExporter,
)
from revpilot.shared.correlation import CorrelationContext
from revpilot.shared.identifiers import TenantId


def test_distributed_trace_correlation_linkage_across_tiers():
    """
    TC-P08-016 & NFR-OBS-001:
    Verifies that span context is strictly propagated across HTTP, queue, and worker tiers
    with 100% presence of trace_id, span_id, correlation_id, and tenant_id.
    """
    pipeline = TelemetryPipeline()
    tenant_id = TenantId.generate()

    # 1. Ingress HTTP Root Span
    root_corr = CorrelationContext.create_root(correlation_id="corr_req_1001")
    http_span = pipeline.process_span(
        span_name="http.ingress.request",
        correlation=root_corr,
        tenant_id=tenant_id,
        attributes={
            "http.method": "POST",
            "http.target": "/api/v1/investigations",
            "auth.token": "Bearer test-secret-token",
        },
        duration_sec=0.125,
    )

    assert http_span["trace_id"] == root_corr.trace_id
    assert http_span["span_id"] == root_corr.span_id
    assert http_span["correlation_id"] == "corr_req_1001"
    assert http_span["causation_id"] is None
    assert http_span["tenant_id"] == str(tenant_id)
    # PII / Secret redacted
    assert "test-secret-token" not in str(http_span["attributes"])
    assert "Bearer [REDACTED_BEARER_TOKEN]" in http_span["attributes"]["auth.token"]

    # 2. Asynchronous Queue Message Child Span
    queue_corr = root_corr.create_child()
    queue_span = pipeline.process_span(
        span_name="queue.message.dispatch",
        correlation=queue_corr,
        tenant_id=tenant_id,
        attributes={"queue.name": "investigations.dispatch"},
        duration_sec=0.015,
    )

    assert queue_span["trace_id"] == root_corr.trace_id
    assert queue_span["causation_id"] == root_corr.span_id
    assert queue_span["correlation_id"] == "corr_req_1001"
    assert queue_span["tenant_id"] == str(tenant_id)

    # 3. Temporal Worker Execution Grandchild Span
    worker_corr = queue_corr.create_child()
    worker_span = pipeline.process_span(
        span_name="temporal.activity.execute",
        correlation=worker_corr,
        tenant_id=tenant_id,
        attributes={
            "activity.type": "GenerateHypothesis",
            "user_email": "analyst@customer.io",
        },
        duration_sec=0.450,
    )

    assert worker_span["trace_id"] == root_corr.trace_id
    assert worker_span["causation_id"] == queue_corr.span_id
    assert worker_span["correlation_id"] == "corr_req_1001"
    assert worker_span["tenant_id"] == str(tenant_id)
    assert "analyst@customer.io" not in str(worker_span["attributes"])
    assert "[REDACTED_EMAIL]" in worker_span["attributes"]["user_email"]


def test_sli_exporter_metrics_promql_compliance():
    """
    AC-P08-002-02:
    Verifies Prometheus /metrics exporter outputs required SLI counters and histograms:
    API Availability, Latency buckets, Workflow success, and RLS violations.
    """
    exporter = SliExporter(service_name="revpilot-test")

    # Record sample HTTP requests
    exporter.record_http_request("GET", "/api/v1/investigations", 200, 0.120, "ten_01")
    exporter.record_http_request("GET", "/api/v1/investigations", 200, 0.450, "ten_01")
    exporter.record_http_request("POST", "/api/v1/actions/dispatch", 500, 1.250, "ten_02")

    # Record Workflow executions
    exporter.record_workflow_execution("InvestigationSaga", "COMPLETED", 4.2)
    exporter.record_workflow_execution("InvestigationSaga", "FAILED", 1.8)

    # Record RLS violation
    exporter.record_rls_violation("ten_02", "customer_orders")

    # Record Connector sync & Audit drops
    exporter.record_connector_sync(success=True)
    exporter.record_audit_drop(count=0)

    # Export metrics string
    metrics_text = exporter.export_prometheus_metrics()

    # 1. Check HTTP counters & histograms
    assert "http_requests_total" in metrics_text
    assert 'method="GET"' in metrics_text
    assert 'endpoint="/api/v1/investigations"' in metrics_text
    assert 'status="200"' in metrics_text
    assert 'status="500"' in metrics_text
    assert "http_request_duration_seconds_bucket" in metrics_text
    assert 'le="0.25"' in metrics_text
    assert 'le="1.5"' in metrics_text
    assert 'le="+Inf"' in metrics_text

    # 2. Check Workflow execution counters
    assert "temporal_workflow_started_total" in metrics_text
    assert 'workflow_type="InvestigationSaga"' in metrics_text
    assert "temporal_workflow_completed_total" in metrics_text
    assert 'status="COMPLETED"' in metrics_text
    assert 'status="FAILED"' in metrics_text

    # 3. Check RLS violation counter
    assert "database_rls_violations_total" in metrics_text
    assert 'tenant_id="ten_02"' in metrics_text
    assert 'table="customer_orders"' in metrics_text

    # 4. Check Connector and Audit metrics
    assert "connector_sync_runs_total" in metrics_text
    assert "connector_sync_success_total" in metrics_text
    assert "audit_events_dropped_total" in metrics_text


def test_cardinality_boundary_enforcement():
    """
    AC-P08-002-02 & §9.1:
    Verifies that excessive cardinality on endpoints or tenants overflows cleanly
    or raises CardinalityLimitExceededError under strict enforcement.
    """
    exporter = SliExporter()

    # Saturate endpoint tracking
    for i in range(MAX_TRACKED_ENDPOINTS):
        exporter.record_http_request("GET", f"/api/v1/resource_{i}", 200, 0.05, "ten_base")

    # Non-strict overflow maps to /other
    exporter.record_http_request("GET", "/api/v1/dynamic_overflow_endpoint", 200, 0.05, "ten_base")
    metrics = exporter.export_prometheus_metrics()
    assert 'endpoint="/other"' in metrics

    # Strict enforcement raises CardinalityLimitExceededError
    with pytest.raises(CardinalityLimitExceededError) as exc_info:
        exporter.record_http_request(
            "GET",
            "/api/v1/strictly_blocked_endpoint",
            200,
            0.05,
            "ten_base",
            strict_cardinality=True,
        )
    assert exc_info.value.code == "CARDINALITY_LIMIT_EXCEEDED"
    assert exc_info.value.status_code == 422


def test_alert_routing_policies_definitions():
    """
    Verifies P0..P4 alert severity classifications and paging policies match §8.
    """
    # P0 Emergency
    p0 = TelemetryPipeline.get_alert_routing(AlertSeverity.P0_EMERGENCY)
    assert p0["response_sla"] == "< 15min"
    assert "24/7 Phone" in p0["paging_policy"]
    assert "Primary SRE" in p0["notification_channel"]

    # P1 Critical
    p1 = TelemetryPipeline.get_alert_routing("P1")
    assert p1["response_sla"] == "< 30min"
    assert "PagerDuty" in p1["paging_policy"]

    # P2 Major
    p2 = TelemetryPipeline.get_alert_routing("P2")
    assert p2["response_sla"] == "< 2hours"
    assert "Slack" in p2["paging_policy"]

    # P3 Minor
    p3 = TelemetryPipeline.get_alert_routing("P3")
    assert p3["response_sla"] == "< 24hours"
    assert "Linear" in p3["paging_policy"] or "Jira" in p3["paging_policy"]

    # P4 Informational
    p4 = TelemetryPipeline.get_alert_routing("P4")
    assert p4["response_sla"] == "No action"
