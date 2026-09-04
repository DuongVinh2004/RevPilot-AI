"""
RevPilot AI — Prometheus SLI Metric Exporter with Cardinality Bounds
Specification: docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md §7, §9
Conforms to NFR-OBS-001, NFR-AVL-001, AC-P08-002-02.
"""

from __future__ import annotations

from collections import defaultdict
import threading
from typing import Any

from revpilot.modules.observability.telemetry.scrubber import CardinalityLimitExceededError

# Cardinality protection bounds (§9.1)
MAX_TRACKED_TENANTS = 100
MAX_TRACKED_ENDPOINTS = 50

ALLOWED_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
PROHIBITED_LABEL_KEYS = {
    "user_id",
    "principal_id",
    "correlation_id",
    "trace_id",
    "span_id",
    "email",
    "query",
    "prompt",
    "body",
}

# Standard Prometheus histogram buckets in seconds
LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 0.8, 1.0, 1.5, 2.0, 5.0, 8.0, 10.0, float("inf"))
WEBHOOK_DELAY_BUCKETS = (0.1, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, float("inf"))
AI_INFERENCE_BUCKETS = (0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 20.0, float("inf"))


class SliExporter:
    """
    Thread-safe in-memory metric collector exposing standard Prometheus text format (/metrics).
    Enforces strict label cardinality to prevent metric explosion (AC-P08-002-02).
    """

    def __init__(self, service_name: str = "revpilot-backend") -> None:
        self.service_name = service_name
        self._lock = threading.Lock()

        # Tracked cardinality sets
        self._known_tenants: set[str] = set()
        self._known_endpoints: set[str] = set()

        # Metric containers
        # http_requests_total: (method, endpoint, status, tenant) -> count
        self._http_requests_total: dict[tuple[str, str, str, str], int] = defaultdict(int)
        # http_request_duration_seconds: (method, endpoint) -> [count per bucket]
        self._http_duration_buckets: dict[tuple[str, str], list[int]] = defaultdict(
            lambda: [0] * len(LATENCY_BUCKETS)
        )
        self._http_duration_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._http_duration_count: dict[tuple[str, str], int] = defaultdict(int)

        # Workflow execution metrics
        self._workflow_started_total: dict[str, int] = defaultdict(int)
        self._workflow_completed_total: dict[tuple[str, str], int] = defaultdict(int)
        self._workflow_duration_sum: dict[str, float] = defaultdict(float)
        self._workflow_duration_count: dict[str, int] = defaultdict(int)

        # Security & RLS Violations
        self._rls_violations_total: dict[tuple[str, str], int] = defaultdict(int)

        # Additional operational SLIs (§7)
        self._connector_sync_runs_total: int = 0
        self._connector_sync_success_total: int = 0
        self._audit_events_dropped_total: int = 0

        # AI inference duration
        self._ai_inference_buckets: dict[str, list[int]] = defaultdict(
            lambda: [0] * len(AI_INFERENCE_BUCKETS)
        )
        self._ai_inference_sum: dict[str, float] = defaultdict(float)
        self._ai_inference_count: dict[str, int] = defaultdict(int)

    def validate_labels(self, labels: dict[str, Any], strict: bool = False) -> dict[str, str]:
        """
        Validate label names and reject prohibited high-cardinality keys.
        """
        cleaned: dict[str, str] = {}
        for k, v in labels.items():
            if k.lower() in PROHIBITED_LABEL_KEYS:
                if strict:
                    raise CardinalityLimitExceededError(
                        f"Prohibited high-cardinality dimension: '{k}'",
                        details={"rejected_key": k},
                    )
                continue
            cleaned[k] = str(v)
        return cleaned

    def record_http_request(
        self,
        method: str,
        path_template: str,
        status_code: int,
        duration_sec: float,
        tenant_id: str = "global",
        strict_cardinality: bool = False,
    ) -> None:
        """
        Record HTTP request counters and duration histogram (SLI: API Availability & Latency).
        """
        norm_method = method.upper() if method.upper() in ALLOWED_HTTP_METHODS else "OTHER"
        norm_status = str(status_code)
        norm_endpoint = path_template if path_template.startswith("/") else f"/{path_template}"

        with self._lock:
            # Cardinality boundary for endpoints
            if norm_endpoint not in self._known_endpoints:
                if len(self._known_endpoints) >= MAX_TRACKED_ENDPOINTS:
                    if strict_cardinality:
                        raise CardinalityLimitExceededError(
                            f"Endpoint template cardinality limit ({MAX_TRACKED_ENDPOINTS}) exceeded",
                            details={"endpoint": norm_endpoint},
                        )
                    norm_endpoint = "/other"
                else:
                    self._known_endpoints.add(norm_endpoint)

            # Cardinality boundary for tenants
            norm_tenant = tenant_id or "global"
            if norm_tenant not in self._known_tenants:
                if len(self._known_tenants) >= MAX_TRACKED_TENANTS:
                    if strict_cardinality:
                        raise CardinalityLimitExceededError(
                            f"Tenant cardinality limit ({MAX_TRACKED_TENANTS}) exceeded",
                            details={"tenant_id": norm_tenant},
                        )
                    norm_tenant = "tenant_overflow"
                else:
                    self._known_tenants.add(norm_tenant)

            # Record counter
            self._http_requests_total[(norm_method, norm_endpoint, norm_status, norm_tenant)] += 1

            # Record histogram
            key = (norm_method, norm_endpoint)
            self._http_duration_sum[key] += max(0.0, duration_sec)
            self._http_duration_count[key] += 1
            for idx, bound in enumerate(LATENCY_BUCKETS):
                if duration_sec <= bound:
                    self._http_duration_buckets[key][idx] += 1

    def record_workflow_execution(
        self,
        workflow_type: str,
        status: str,
        duration_sec: float,
    ) -> None:
        """
        Record Temporal Saga workflow execution (SLI: Workflow Execution Success).
        """
        wf = workflow_type.strip() or "unknown_workflow"
        norm_status = status.upper()

        with self._lock:
            self._workflow_started_total[wf] += 1
            self._workflow_completed_total[(wf, norm_status)] += 1
            self._workflow_duration_sum[wf] += max(0.0, duration_sec)
            self._workflow_duration_count[wf] += 1

    def record_rls_violation(self, tenant_id: str, table_name: str) -> None:
        """
        Record cross-tenant isolation breach attempt (SLI: Tenant Isolation Breaches == 0).
        """
        t = tenant_id or "unknown"
        tbl = table_name or "unknown_table"
        with self._lock:
            self._rls_violations_total[(t, tbl)] += 1

    def record_connector_sync(self, success: bool) -> None:
        """Record connector synchronization attempt (SLI: Connector Sync Success)."""
        with self._lock:
            self._connector_sync_runs_total += 1
            if success:
                self._connector_sync_success_total += 1

    def record_ai_inference(self, model_id: str, duration_sec: float) -> None:
        """Record model inference roundtrip latency (SLI: AI Inference Latency)."""
        m = model_id or "default_model"
        with self._lock:
            self._ai_inference_sum[m] += max(0.0, duration_sec)
            self._ai_inference_count[m] += 1
            for idx, bound in enumerate(AI_INFERENCE_BUCKETS):
                if duration_sec <= bound:
                    self._ai_inference_buckets[m][idx] += 1

    def record_audit_drop(self, count: int = 1) -> None:
        """Record dropped audit event (SLI: Audit Delivery Integrity == 100%)."""
        with self._lock:
            self._audit_events_dropped_total += count

    def reset(self) -> None:
        """Reset all metrics (primarily for test fixtures)."""
        with self._lock:
            self._known_tenants.clear()
            self._known_endpoints.clear()
            self._http_requests_total.clear()
            self._http_duration_buckets.clear()
            self._http_duration_sum.clear()
            self._http_duration_count.clear()
            self._workflow_started_total.clear()
            self._workflow_completed_total.clear()
            self._workflow_duration_sum.clear()
            self._workflow_duration_count.clear()
            self._rls_violations_total.clear()
            self._connector_sync_runs_total = 0
            self._connector_sync_success_total = 0
            self._audit_events_dropped_total = 0
            self._ai_inference_buckets.clear()
            self._ai_inference_sum.clear()
            self._ai_inference_count.clear()

    def export_prometheus_metrics(self) -> str:
        """
        Format metrics as standard Prometheus text representation.
        """
        lines: list[str] = []

        with self._lock:
            # 1. http_requests_total
            lines.append("# HELP http_requests_total Total number of HTTP requests processed.")
            lines.append("# TYPE http_requests_total counter")
            for (method, endpoint, status, tenant), count in sorted(self._http_requests_total.items()):
                lines.append(
                    f'http_requests_total{{service="{self.service_name}",method="{method}",'
                    f'endpoint="{endpoint}",status="{status}",tenant_id="{tenant}"}} {count}'
                )

            # 2. http_request_duration_seconds
            lines.append("# HELP http_request_duration_seconds HTTP request latency histogram in seconds.")
            lines.append("# TYPE http_request_duration_seconds histogram")
            for (method, endpoint), counts in sorted(self._http_duration_buckets.items()):
                cum = 0
                for idx, bound in enumerate(LATENCY_BUCKETS):
                    cum = counts[idx]
                    bound_str = "+Inf" if bound == float("inf") else str(bound)
                    lines.append(
                        f'http_request_duration_seconds_bucket{{service="{self.service_name}",'
                        f'method="{method}",endpoint="{endpoint}",le="{bound_str}"}} {cum}'
                    )
                sum_val = self._http_duration_sum.get((method, endpoint), 0.0)
                cnt_val = self._http_duration_count.get((method, endpoint), 0)
                lines.append(
                    f'http_request_duration_seconds_sum{{service="{self.service_name}",method="{method}",endpoint="{endpoint}"}} {sum_val:.6f}'
                )
                lines.append(
                    f'http_request_duration_seconds_count{{service="{self.service_name}",method="{method}",endpoint="{endpoint}"}} {cnt_val}'
                )

            # 3. temporal_workflow metrics
            lines.append("# HELP temporal_workflow_started_total Total started Temporal workflows.")
            lines.append("# TYPE temporal_workflow_started_total counter")
            for wf, count in sorted(self._workflow_started_total.items()):
                lines.append(f'temporal_workflow_started_total{{service="{self.service_name}",workflow_type="{wf}"}} {count}')

            lines.append("# HELP temporal_workflow_completed_total Completed workflows by terminal status.")
            lines.append("# TYPE temporal_workflow_completed_total counter")
            for (wf, status), count in sorted(self._workflow_completed_total.items()):
                lines.append(
                    f'temporal_workflow_completed_total{{service="{self.service_name}",workflow_type="{wf}",status="{status}"}} {count}'
                )

            # 4. database_rls_violations_total
            lines.append("# HELP database_rls_violations_total RLS policy violation attempts across tenants.")
            lines.append("# TYPE database_rls_violations_total counter")
            for (tenant, table), count in sorted(self._rls_violations_total.items()):
                lines.append(
                    f'database_rls_violations_total{{service="{self.service_name}",tenant_id="{tenant}",table="{table}"}} {count}'
                )

            # 5. Connector sync metrics
            lines.append("# HELP connector_sync_runs_total Total scheduled connector sync jobs executed.")
            lines.append("# TYPE connector_sync_runs_total counter")
            lines.append(f'connector_sync_runs_total{{service="{self.service_name}"}} {self._connector_sync_runs_total}')

            lines.append("# HELP connector_sync_success_total Successful connector sync runs.")
            lines.append("# TYPE connector_sync_success_total counter")
            lines.append(f'connector_sync_success_total{{service="{self.service_name}"}} {self._connector_sync_success_total}')

            # 6. Audit integrity metric
            lines.append("# HELP audit_events_dropped_total Dropped audit log events (must be 0).")
            lines.append("# TYPE audit_events_dropped_total counter")
            lines.append(f'audit_events_dropped_total{{service="{self.service_name}"}} {self._audit_events_dropped_total}')

            # 7. AI inference duration
            lines.append("# HELP ai_inference_duration_seconds Model inference roundtrip latency histogram.")
            lines.append("# TYPE ai_inference_duration_seconds histogram")
            for m, counts in sorted(self._ai_inference_buckets.items()):
                cum = 0
                for idx, bound in enumerate(AI_INFERENCE_BUCKETS):
                    cum = counts[idx]
                    bound_str = "+Inf" if bound == float("inf") else str(bound)
                    lines.append(
                        f'ai_inference_duration_seconds_bucket{{service="{self.service_name}",model_id="{m}",le="{bound_str}"}} {cum}'
                    )
                sum_val = self._ai_inference_sum.get(m, 0.0)
                cnt_val = self._ai_inference_count.get(m, 0)
                lines.append(f'ai_inference_duration_seconds_sum{{service="{self.service_name}",model_id="{m}"}} {sum_val:.6f}')
                lines.append(f'ai_inference_duration_seconds_count{{service="{self.service_name}",model_id="{m}"}} {cnt_val}')

        return "\n".join(lines) + "\n"
