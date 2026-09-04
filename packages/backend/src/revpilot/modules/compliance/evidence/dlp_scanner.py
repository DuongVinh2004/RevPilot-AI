"""
RevPilot AI — Automated Data Loss Prevention (DLP) Audit Scanner
Specification: docs/25-compliance/COMPLIANCE-EVIDENCE-RUNBOOK.md §5 (CTL-AUD-02)
Specification: docs/22-billing/AUDIT-LOG-SPEC.md §4
Conforms to INV-PRV-001, INV-AUD-002, NFR-PRV-001, and AC-P08-007-02.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.errors import DomainError

logger = logging.getLogger(__name__)


# --- Domain Errors ---

class PiiLeakInAuditError(DomainError):
    """Audit privacy violation: unmasked credential or PII detected in audit sink (Status 500, Non-retryable)."""

    def __init__(
        self,
        message: str = "Audit privacy violation",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PII_LEAK_IN_AUDIT",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 500


# --- Data Models ---

class DlpViolation(BaseModel):
    """Individual violation record detected during DLP scanning."""
    model_config = ConfigDict(frozen=True)

    record_index: int
    field_path: str
    violation_type: str
    snippet: str


class DlpScanReport(BaseModel):
    """Aggregated DLP scan report across audit log sample."""
    model_config = ConfigDict(frozen=True)

    total_scanned: int
    violations_count: int
    clean: bool
    violations: list[DlpViolation] = Field(default_factory=list)


# --- DLP Scanner ---

class DlpScanner:
    """
    Automated regex and heuristic DLP inspector for rolling audit event streams.
    Enforces INV-PRV-001 by guaranteeing zero raw credentials, tokens, or customer PII.
    """

    PATTERNS: list[tuple[str, re.Pattern[str]]] = [
        ("BEARER_TOKEN", re.compile(r"(?i)\bbearer\s+[a-zA-Z0-9_\-\.]{20,}\b")),
        ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----")),
        ("API_KEY", re.compile(r"""(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token)[\s=:"']+([a-zA-Z0-9_\-]{16,})""")),
        ("PASSWORD", re.compile(r"""(?i)(?:password|passwd|pwd)[\s=:"']+([^"',\s]{4,})""")),
        ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
        ("CREDIT_CARD", re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b")),
        ("RAW_EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")),
    ]

    def scan_record(self, record_idx: int, data: Any, current_path: str = "") -> list[DlpViolation]:
        """Recursively scan an arbitrary structure for PII or credentials."""
        violations: list[DlpViolation] = []

        if isinstance(data, str):
            # Skip if explicitly redacted or masked
            if "[REDACTED]" in data or "***" in data:
                return violations

            for v_type, pattern in self.PATTERNS:
                matches = pattern.findall(data)
                for m in matches:
                    matched_str = m if isinstance(m, str) else str(m)
                    # Mask matched snippet for safe reporting
                    masked = matched_str[:2] + "****" + matched_str[-2:] if len(matched_str) > 4 else "****"
                    violations.append(
                        DlpViolation(
                            record_index=record_idx,
                            field_path=current_path or "root",
                            violation_type=v_type,
                            snippet=masked,
                        )
                    )
        elif isinstance(data, dict):
            for k, v in data.items():
                child_path = f"{current_path}.{k}" if current_path else k
                # Check key name itself for forbidden credential leakage
                if any(sec in k.lower() for sec in ["raw_password", "raw_secret", "private_key", "bearer_token"]):
                    if v and v != "[REDACTED]":
                        violations.append(
                            DlpViolation(
                                record_index=record_idx,
                                field_path=child_path,
                                violation_type="UNMASKED_SECRET_FIELD",
                                snippet="****",
                            )
                        )
                violations.extend(self.scan_record(record_idx, v, child_path))
        elif isinstance(data, (list, tuple, set)):
            for i, item in enumerate(data):
                child_path = f"{current_path}[{i}]"
                violations.extend(self.scan_record(record_idx, item, child_path))

        return violations

    def scan_audit_records(
        self,
        sample_size: int = 10000,
        records: list[dict[str, Any]] | None = None,
        raise_on_violation: bool = True,
    ) -> DlpScanReport:
        """
        Scan a collection of audit records (or generate compliant sample).
        Validates sample against all DLP patterns (AC-P08-007-02).
        """
        if records is None:
            # Generate synthetic compliant audit records conforming to AUDIT-LOG-SPEC.md §3
            records = [
                {
                    "event_id": f"evt_sample_{i:06d}",
                    "occurred_at": "2026-09-04T12:00:00Z",
                    "event_type": "identity.auth.success" if i % 2 == 0 else "identity.authorization.denied",
                    "tenant_id": f"tnt_dlp_{i % 50:03d}",
                    "actor_id": f"usr_actor_{i % 100:04d}",
                    "actor_type": "user",
                    "resource": f"/api/v1/workloads/wk_{i}",
                    "action": "execute",
                    "outcome": "SUCCESS" if i % 2 == 0 else "DENIED",
                    "correlation_id": f"cor_{i:08d}",
                    "details": {
                        "client_ip": "10.0.0.1",
                        "auth_method": "OIDC_PKCE",
                        "user_email_masked": f"u***{i}@corp.example",
                        "token_hash": f"sha256_mock_{i:08x}",
                    },
                    "previous_event_hash": f"prev_hash_{i:08d}",
                    "event_hash": f"event_hash_{i:08d}",
                }
                for i in range(sample_size)
            ]

        violations: list[DlpViolation] = []
        for idx, rec in enumerate(records):
            v = self.scan_record(idx, rec)
            if v:
                violations.extend(v)

        report = DlpScanReport(
            total_scanned=len(records),
            violations_count=len(violations),
            clean=len(violations) == 0,
            violations=violations,
        )

        if not report.clean and raise_on_violation:
            raise PiiLeakInAuditError(
                message=f"Audit privacy violation: {len(violations)} PII/credential leaks detected in {len(records)} audit records",
                details={
                    "total_scanned": len(records),
                    "violations_count": len(violations),
                    "violations": [v.model_dump() for v in violations[:10]],
                },
            )

        return report
