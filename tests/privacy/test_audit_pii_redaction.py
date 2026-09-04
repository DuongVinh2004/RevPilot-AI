"""
RevPilot AI — Audit Log PII Redaction & DLP Sanitization Tests
Specification: docs/25-compliance/COMPLIANCE-EVIDENCE-RUNBOOK.md §5 (CTL-AUD-02)
Specification: docs/22-billing/AUDIT-LOG-SPEC.md §4
Conforms to INV-PRV-001, INV-AUD-002, NFR-PRV-001, and AC-P08-007-02.
"""

from __future__ import annotations

import pytest

from revpilot.modules.compliance.evidence.dlp_scanner import (
    DlpScanner,
    DlpScanReport,
    PiiLeakInAuditError,
)


@pytest.fixture
def scanner() -> DlpScanner:
    return DlpScanner()


def test_dlp_scan_over_10000_audit_rows_zero_pii_leak(scanner: DlpScanner):
    """
    AC-P08-007-02: PASS only if DLP scan over 10,000 audit log sample rows
    confirms zero unmasked credentials or customer PII (INV-PRV-001).
    """
    report = scanner.scan_audit_records(
        sample_size=10000,
        raise_on_violation=True,
    )

    assert isinstance(report, DlpScanReport)
    assert report.total_scanned == 10000
    assert report.violations_count == 0
    assert report.clean is True
    assert len(report.violations) == 0


def test_dlp_scanner_detects_unmasked_credential_raises_error(scanner: DlpScanner):
    """
    Verify that unmasked bearer token or secret triggers PII_LEAK_IN_AUDIT (500).
    """
    tainted_records = [
        {
            "event_id": "evt_tainted_001",
            "event_type": "identity.auth.failure",
            "details": {
                "user_id": "usr_test",
                "auth_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sensitive_leak_token_sample_here",
            },
        },
    ]

    with pytest.raises(PiiLeakInAuditError) as exc_info:
        scanner.scan_audit_records(
            records=tainted_records,
            raise_on_violation=True,
        )

    err = exc_info.value
    assert err.code == "PII_LEAK_IN_AUDIT"
    assert err.status_code == 500
    assert err.retryable is False
    assert err.details["violations_count"] >= 1


def test_dlp_scanner_detects_raw_email_and_credit_card(scanner: DlpScanner):
    """
    Verify detection of unmasked customer email and payment numbers.
    """
    tainted_records = [
        {
            "event_id": "evt_tainted_002",
            "event_type": "billing.payment.attempt",
            "details": {
                "customer_email": "alice.smith@customer-domain.com",
                "pan": "4111111111111111",
            },
        },
    ]

    report = scanner.scan_audit_records(
        records=tainted_records,
        raise_on_violation=False,
    )

    assert report.clean is False
    assert report.violations_count == 2
    types = {v.violation_type for v in report.violations}
    assert "RAW_EMAIL" in types
    assert "CREDIT_CARD" in types


def test_masked_pii_passes_dlp_scan(scanner: DlpScanner):
    """
    Properly redacted and masked PII (e.g. [REDACTED], ***) passes without violations.
    """
    clean_records = [
        {
            "event_id": "evt_clean_001",
            "event_type": "identity.auth.success",
            "details": {
                "email_masked": "a***@customer.com",
                "token": "[REDACTED]",
                "password": "[REDACTED]",
                "source_ip": "192.168.1.1",
            },
        },
    ]

    report = scanner.scan_audit_records(
        records=clean_records,
        raise_on_violation=True,
    )

    assert report.clean is True
    assert report.violations_count == 0
