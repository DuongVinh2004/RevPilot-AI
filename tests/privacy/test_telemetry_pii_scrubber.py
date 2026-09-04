"""
RevPilot AI — Tests: Telemetry PII & Credential Scrubber
Specification: docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md §9.2
Conforms to NFR-PRV-001, AC-P08-002-01.
"""

from __future__ import annotations

import pytest

from revpilot.modules.observability.telemetry.scrubber import (
    ScrubberParserError,
    TelemetryScrubber,
)


@pytest.fixture
def scrubber() -> TelemetryScrubber:
    return TelemetryScrubber()


def test_bearer_token_redaction_in_log(scrubber: TelemetryScrubber):
    """
    AC-P08-002-01: Redacts 100% of Bearer tokens in raw log text.
    """
    raw = "Client authenticated with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID for tenant ten_alpha"
    scrubbed = scrubber.scrub_log_payload(raw)

    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed
    assert "Bearer [REDACTED_BEARER_TOKEN]" in scrubbed
    assert "ten_alpha" in scrubbed


def test_password_and_secret_redaction_in_log(scrubber: TelemetryScrubber):
    """
    AC-P08-002-01: Redacts password, secret, api_key, and token key-values.
    """
    raw = (
        "Connecting to upstream service with password=SuperSecretPassword123! "
        "and api_key: key_live_999888777666 and token='tok_xyz123abc'"
    )
    scrubbed = scrubber.scrub_log_payload(raw)

    assert "SuperSecretPassword123!" not in scrubbed
    assert "key_live_999888777666" not in scrubbed
    assert "tok_xyz123abc" not in scrubbed
    assert "password: [REDACTED]" in scrubbed
    assert "api_key: [REDACTED]" in scrubbed
    assert "token: [REDACTED]" in scrubbed


def test_email_address_redaction_in_log(scrubber: TelemetryScrubber):
    """
    AC-P08-002-01: Redacts customer and operator email addresses.
    """
    raw = "Audit event triggered by user john.doe@enterprise.com and notified alert-lead@revpilot.ai"
    scrubbed = scrubber.scrub_log_payload(raw)

    assert "john.doe@enterprise.com" not in scrubbed
    assert "alert-lead@revpilot.ai" not in scrubbed
    assert "[REDACTED_EMAIL]" in scrubbed


def test_nested_span_attributes_pii_scrubbing(scrubber: TelemetryScrubber):
    """
    Recursively redacts nested dictionary and list values in span attributes.
    """
    attrs = {
        "service": "billing-engine",
        "tenant_id": "ten_test_01",
        "nested_meta": {
            "contact_email": "finance-admin@customer.org",
            "auth_header": "Bearer secret-access-token-9988",
            "db_conn": "postgres://user:password=secret_db_pass@db.internal:5432/revpilot",
        },
        "items": [
            "Normal item text",
            "User email: alert@domain.co.uk in list",
            {"item_token": "token: tok_internal_item_secret"},
        ],
    }

    scrubbed = scrubber.scrub_attributes(attrs)

    # Invariants
    assert scrubbed["service"] == "billing-engine"
    assert scrubbed["tenant_id"] == "ten_test_01"

    nested = scrubbed["nested_meta"]
    assert "finance-admin@customer.org" not in str(nested)
    assert "[REDACTED_EMAIL]" in nested["contact_email"]
    assert "secret-access-token-9988" not in str(nested)
    assert "Bearer [REDACTED_BEARER_TOKEN]" in nested["auth_header"]
    assert "secret_db_pass" not in str(nested)

    # List items
    items = scrubbed["items"]
    assert "alert@domain.co.uk" not in str(items)
    assert "[REDACTED_EMAIL]" in items[1]
    assert "tok_internal_item_secret" not in str(items)


def test_sensitive_key_name_override(scrubber: TelemetryScrubber):
    """
    Attributes with explicitly sensitive key names are immediately replaced with [REDACTED].
    """
    attrs = {
        "normal_key": "safe_value",
        "password": "raw_plaintext_password",
        "apiKey": "ak_live_abcdef12345",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----...",
    }

    scrubbed = scrubber.scrub_attributes(attrs)

    assert scrubbed["normal_key"] == "safe_value"
    assert scrubbed["password"] == "[REDACTED]"
    assert scrubbed["apiKey"] == "[REDACTED]"
    assert scrubbed["private_key"] == "[REDACTED]"


def test_invalid_attributes_type_raises_scrubber_parser_error(scrubber: TelemetryScrubber):
    """
    Passing a non-dict to scrub_attributes raises ScrubberParserError (500).
    """
    with pytest.raises(ScrubberParserError) as exc_info:
        scrubber.scrub_attributes("not_a_dict")  # type: ignore

    assert exc_info.value.code == "SCRUBBER_PARSER_ERROR"
    assert exc_info.value.status_code == 500
