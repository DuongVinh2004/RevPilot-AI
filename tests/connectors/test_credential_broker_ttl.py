"""
RevPilot AI — Tests: Ephemeral Credential Broker
Specification: docs/31-adr/ADR-0009-secrets-and-keys.md
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7.2
Conforms to DEC-007, INV-SEC-001, and INV-IAM-002.
"""

from __future__ import annotations

import sys
from datetime import timedelta
import pytest

from revpilot.modules.connectors.adapters.broker import (
    CredentialBroker,
    CredentialBrokerError,
    TokenTtlExceededError,
    MAX_TOKEN_TTL_SECONDS,
)
from revpilot.shared.errors import TenancyViolationError
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture(autouse=True)
def _isolate_connectors_module():
    """Ensure connectors module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.connectors"):
            sys.modules.pop(mod, None)


def test_credential_broker_issue_and_validate():
    """Verify ephemeral token issuance within DEC-007 policy limit (<= 15m / 900s)."""
    broker = CredentialBroker()
    tenant_id = TenantId.generate()

    token = broker.issue_ephemeral_token(
        tenant_id=tenant_id,
        provider="salesforce",
        requested_scopes=["api", "read"],
        ttl_seconds=600,
    )

    assert token.tenant_id == tenant_id
    assert token.provider == "salesforce"
    assert token.scopes == frozenset(["api", "read"])
    assert not token.is_expired()

    # Validation succeeds
    validated = broker.validate_token(token.token_value, required_tenant_id=tenant_id)
    assert validated.token_value == token.token_value


def test_credential_broker_rejects_excessive_ttl():
    """DEC-007: Tokens with TTL > 900 seconds are rejected fail-closed."""
    broker = CredentialBroker()
    tenant_id = TenantId.generate()

    # 901 seconds exceeds 15-minute maximum
    with pytest.raises(TokenTtlExceededError) as exc_info:
        broker.issue_ephemeral_token(
            tenant_id=tenant_id,
            provider="stripe",
            requested_scopes=["charges:read"],
            ttl_seconds=901,
        )

    assert exc_info.value.code == "ERR_EXCESSIVE_TOKEN_TTL"
    assert "exceeds maximum allowed 15-minute policy limit" in exc_info.value.message


def test_credential_broker_expiration_handling():
    """Verify expired ephemeral tokens cannot be validated."""
    broker = CredentialBroker()
    tenant_id = TenantId.generate()

    token = broker.issue_ephemeral_token(
        tenant_id=tenant_id,
        provider="zendesk",
        requested_scopes=["tickets:read"],
        ttl_seconds=60,
    )

    future_time = UtcDateTime(token.expires_at.value + timedelta(seconds=1))
    assert token.is_expired(as_of=future_time)


def test_credential_broker_tenant_isolation():
    """INV-TEN-001: Ephemeral token cannot be validated against a mismatched tenant."""
    broker = CredentialBroker()
    tenant_a = TenantId.generate()
    tenant_b = TenantId.generate()

    token = broker.issue_ephemeral_token(
        tenant_id=tenant_a,
        provider="salesforce",
        requested_scopes=["crm:read"],
        ttl_seconds=300,
    )

    with pytest.raises(TenancyViolationError) as exc_info:
        broker.validate_token(token.token_value, required_tenant_id=tenant_b)

    assert "Token tenant mismatch" in str(exc_info.value)


def test_scoped_token_repr_redaction():
    """INV-SEC-001: Raw token secret must NEVER appear in repr() or logs."""
    broker = CredentialBroker()
    tenant_id = TenantId.generate()

    token = broker.issue_ephemeral_token(
        tenant_id=tenant_id,
        provider="stripe",
        requested_scopes=["invoices:read"],
        ttl_seconds=300,
    )

    repr_output = repr(token)
    assert token.token_value not in repr_output
    assert "***REDACTED***" in repr_output
