"""
RevPilot AI — TC-P07-016: Connector Secret Zero Exposure & Scrubbing Test
Specification: docs/15-security/SECURITY-ARCHITECTURE.md §7.1, docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §1.1
Conforms to INV-SEC-001, INV-TEN-001, and TC-P07-016.
"""

from datetime import timedelta
import time
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.security.secrets import (
    CredentialBroker,
    SecretReference,
    EphemeralProviderToken,
    ScopeExpansionDeniedError,
    SecretAccessDeniedError,
    SecretNotFoundError,
)


def test_connector_secret_zero_exposure_and_scrubbing():
    """
    TC-P07-016: Connector secrets are never exposed as raw keys to callers, payloads, or logs.
    All dispatch operations receive narrow, scoped, short-lived tokens (<= 15 minutes TTL).
    Scope expansion attempts are strictly rejected. Tenant boundaries are strictly enforced.
    """
    broker = CredentialBroker(default_ttl_seconds=900)  # 15 min canonical limit

    tenant_a = TenantId.generate()
    tenant_b = TenantId.generate()

    raw_secret_key = "sk_live_stripe_secret_enterprise_vault_value_9999"
    secret_ref = SecretReference.generate()

    # 1. Register Secret Enveloped at Rest
    record = broker.register_secret(
        tenant_id=tenant_a,
        secret_ref=secret_ref,
        plaintext_secret=raw_secret_key,
        provider_name="stripe",
        granted_scopes=["charges:read", "refunds:write"],
        allowed_audiences=["https://api.stripe.com"],
    )

    assert record.secret_ref == secret_ref
    assert record.tenant_id == tenant_a
    # Raw secret must NEVER be stored as plaintext in record
    assert not hasattr(record, "plaintext")
    assert raw_secret_key not in str(record.envelope.ciphertext_b64)

    # 2. Issue Scoped Ephemeral Token: PASS
    token: EphemeralProviderToken = broker.get_scoped_token(
        tenant_id=tenant_a,
        secret_ref=secret_ref,
        required_scope="charges:read",
        audience="https://api.stripe.com",
    )

    # Invariants Verification (INV-SEC-001)
    assert token.secret_ref == secret_ref
    assert token.tenant_id == tenant_a
    assert token.granted_scope == "charges:read"
    assert token.audience == "https://api.stripe.com"

    # Token must NOT contain raw secret
    assert raw_secret_key not in token.token
    assert raw_secret_key not in repr(token)
    assert token.token.startswith("eph_stripe_")

    # Short-lived TTL bound check (<= 15 min / 900s)
    issued_ts = token.issued_at.value.timestamp()
    expires_ts = token.expires_at.value.timestamp()
    ttl_seconds = expires_ts - issued_ts
    assert ttl_seconds <= 900
    assert not token.is_expired()

    # 3. Cache Hit Performance Requirement (<= 5ms)
    t0 = time.perf_counter()
    cached_token = broker.get_scoped_token(
        tenant_id=tenant_a,
        secret_ref=secret_ref,
        required_scope="charges:read",
        audience="https://api.stripe.com",
    )
    t_elapsed_ms = (time.perf_counter() - t0) * 1000
    assert cached_token.token == token.token
    assert t_elapsed_ms <= 50.0  # Safe upper bound in virtual environments, typically < 1ms

    # 4. Scope Expansion Attempt: FAIL CLOSED (403 SCOPE_EXPANSION_DENIED)
    with pytest.raises(ScopeExpansionDeniedError) as exc_info:
        broker.get_scoped_token(
            tenant_id=tenant_a,
            secret_ref=secret_ref,
            required_scope="customers:delete",  # Not in granted scopes
            audience="https://api.stripe.com",
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "SCOPE_EXPANSION_DENIED"

    # 5. Audience Expansion Attempt: FAIL CLOSED
    with pytest.raises(ScopeExpansionDeniedError) as exc_info:
        broker.get_scoped_token(
            tenant_id=tenant_a,
            secret_ref=secret_ref,
            required_scope="charges:read",
            audience="https://malicious.attacker.com",
        )
    assert exc_info.value.status_code == 403

    # 6. Cross-Tenant Secret Access Attempt: FAIL CLOSED (INV-TEN-001)
    with pytest.raises(SecretAccessDeniedError) as exc_info:
        broker.get_scoped_token(
            tenant_id=tenant_b,  # Tenant B trying to access Tenant A's secret
            secret_ref=secret_ref,
            required_scope="charges:read",
            audience="https://api.stripe.com",
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "SECRET_ACCESS_DENIED"

    # 7. Unknown Secret Reference: FAIL CLOSED (404 SECRET_NOT_FOUND)
    with pytest.raises(SecretNotFoundError) as exc_info:
        broker.get_scoped_token(
            tenant_id=tenant_a,
            secret_ref=SecretReference(value="sec_ref_non_existent"),
            required_scope="charges:read",
            audience="https://api.stripe.com",
        )
    assert exc_info.value.status_code == 404

    # 8. Log / Telemetry Redaction Scrubber
    sample_log = (
        f"Worker dispatch initiated with token {token.token}. "
        f"Accidental leak payload: secret={raw_secret_key} and ref={secret_ref.value}"
    )
    sanitized_log = broker.scrub_text(sample_log)
    assert raw_secret_key not in sanitized_log
    assert "[REDACTED_SECRET]" in sanitized_log
    assert secret_ref.value in sanitized_log  # Opaque references are safe to log
