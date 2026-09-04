"""
RevPilot AI — Operational Telemetry Pipeline & Alert Routing
Specification: docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md §8, §9
Conforms to NFR-OBS-001, NFR-OBS-002, NFR-PRV-001.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from revpilot.modules.observability.telemetry.scrubber import TelemetryScrubber
from revpilot.modules.observability.telemetry.sli_exporter import SliExporter
from revpilot.shared.correlation import CorrelationContext
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


class AlertSeverity(str, Enum):
    """Alert severity classifications (§8)."""
    P0_EMERGENCY = "P0"
    P1_CRITICAL = "P1"
    P2_MAJOR = "P2"
    P3_MINOR = "P3"
    P4_INFORMATIONAL = "P4"


ALERT_ROUTING_POLICIES: dict[AlertSeverity, dict[str, str]] = {
    AlertSeverity.P0_EMERGENCY: {
        "severity": "P0 (Emergency)",
        "response_sla": "< 15min",
        "paging_policy": "24/7 Phone / PagerDuty wake-up",
        "notification_channel": "Primary SRE On-Call + SecOps On-Call",
        "escalation_target": "Head of Engineering + SRE Lead",
    },
    AlertSeverity.P1_CRITICAL: {
        "severity": "P1 (Critical)",
        "response_sla": "< 30min",
        "paging_policy": "PagerDuty on-call alert",
        "notification_channel": "SRE On-Call + Owning Subsystem Lead",
        "escalation_target": "Principal Architect",
    },
    AlertSeverity.P2_MAJOR: {
        "severity": "P2 (Major)",
        "response_sla": "< 2hours",
        "paging_policy": "Business hours email + Slack",
        "notification_channel": "Slack #alerts-p2 + Domain Team Lead",
        "escalation_target": "Engineering Manager",
    },
    AlertSeverity.P3_MINOR: {
        "severity": "P3 (Minor)",
        "response_sla": "< 24hours",
        "paging_policy": "Ticket generated in Jira/Linear",
        "notification_channel": "Slack #alerts-p3 + Daily Standup",
        "escalation_target": "Domain On-Call",
    },
    AlertSeverity.P4_INFORMATIONAL: {
        "severity": "P4 (Informational)",
        "response_sla": "No action",
        "paging_policy": "Logged to telemetry sink",
        "notification_channel": "Slack #ops-activity",
        "escalation_target": "None",
    },
}


class TelemetryPipeline:
    """
    Central operational telemetry pipeline coordinating distributed trace correlation,
    PII and credential scrubbing, Prometheus SLI recording, and alert routing.
    """

    def __init__(
        self,
        scrubber: TelemetryScrubber | None = None,
        exporter: SliExporter | None = None,
    ) -> None:
        self.scrubber = scrubber or TelemetryScrubber()
        self.exporter = exporter or SliExporter()

    def process_span(
        self,
        span_name: str,
        correlation: CorrelationContext,
        tenant_id: str | TenantId,
        attributes: dict[str, Any] | None = None,
        duration_sec: float | None = None,
    ) -> dict[str, Any]:
        """
        Process and scrub an OpenTelemetry span event.
        Enforces NFR-OBS-001 (100% spans carry tenant_id and correlation_id)
        and NFR-PRV-001 (0 raw credentials or PII in exported span attributes).
        """
        t_id = str(tenant_id)
        if not t_id or not correlation.trace_id or not correlation.correlation_id:
            raise ValueError(
                "NFR-OBS-001 violation: Spans must strictly include valid tenant_id, "
                "trace_id, and correlation_id"
            )

        raw_attrs = attributes or {}
        scrubbed_attrs = self.scrubber.scrub_attributes(raw_attrs)

        span_record: dict[str, Any] = {
            "span_name": span_name,
            "trace_id": correlation.trace_id,
            "span_id": correlation.span_id,
            "correlation_id": correlation.correlation_id,
            "causation_id": correlation.causation_id,
            "tenant_id": t_id,
            "attributes": scrubbed_attrs,
            "timestamp": UtcDateTime.now().isoformat(),
        }
        if duration_sec is not None:
            span_record["duration_sec"] = max(0.0, duration_sec)

        return span_record

    def process_log(
        self,
        raw_message: str,
        correlation: CorrelationContext | None = None,
        tenant_id: str | TenantId | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process and scrub an operational log message (NFR-PRV-001).
        """
        scrubbed_message = self.scrubber.scrub_log_payload(raw_message)
        scrubbed_extra = self.scrubber.scrub_attributes(extra) if extra else {}

        log_record: dict[str, Any] = {
            "message": scrubbed_message,
            "timestamp": UtcDateTime.now().isoformat(),
            "extra": scrubbed_extra,
        }
        if correlation:
            log_record["trace_id"] = correlation.trace_id
            log_record["span_id"] = correlation.span_id
            log_record["correlation_id"] = correlation.correlation_id
        if tenant_id:
            log_record["tenant_id"] = str(tenant_id)

        return log_record

    @staticmethod
    def get_alert_routing(severity: AlertSeverity | str) -> dict[str, str]:
        """
        Retrieve paging policy and escalation target for an alert severity level (§8).
        """
        try:
            sev_enum = severity if isinstance(severity, AlertSeverity) else AlertSeverity(str(severity).upper())
        except ValueError:
            sev_enum = AlertSeverity.P1_CRITICAL

        return ALERT_ROUTING_POLICIES.get(sev_enum, ALERT_ROUTING_POLICIES[AlertSeverity.P1_CRITICAL])
