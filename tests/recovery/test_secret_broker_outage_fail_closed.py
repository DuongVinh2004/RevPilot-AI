"""
RevPilot AI — Secret Broker Outage Fail-Closed Recovery Test
Specification: docs/15-security/SECURITY-ARCHITECTURE.md §7.3, ADR-0009
Conforms to INV-REL-001 and AC-P07-004-02.
"""

import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.modules.security.secrets import (
    CredentialBroker,
    SecretReference,
    BrokerUnavailableError,
)


def test_secret_broker_outage_fails_closed():
    """
    AC-P07-004-02 / INV-REL-001: When the Secret Broker or KMS dependency experiences an outage,
    all credential resolution requests MUST fail closed with 503 BROKER_UNAVAILABLE.
    Fallback to cached plaintext or unverified keys is strictly prohibited.
    """
    broker = CredentialBroker()

    tenant_id = TenantId.generate()
    secret_ref = SecretReference.generate()

    broker.register_secret(
        tenant_id=tenant_id,
        secret_ref=secret_ref,
        plaintext_secret="hubspot_api_key_production_token",
        provider_name="hubspot",
        granted_scopes=["contacts:read"],
        allowed_audiences=["https://api.hubspot.com"],
    )

    # Pre-outage: Normal resolution succeeds
    token = broker.get_scoped_token(
        tenant_id=tenant_id,
        secret_ref=secret_ref,
        required_scope="contacts:read",
        audience="https://api.hubspot.com",
    )
    assert token is not None
    assert token.token.startswith("eph_hubspot_")

    # 1. Trigger Secret Service Outage
    broker.set_outage(True)

    # 2. Invocations during outage must FAIL CLOSED with 503 BROKER_UNAVAILABLE
    with pytest.raises(BrokerUnavailableError) as exc_info:
        broker.get_scoped_token(
            tenant_id=tenant_id,
            secret_ref=secret_ref,
            required_scope="contacts:read",
            audience="https://api.hubspot.com",
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "BROKER_UNAVAILABLE"
    assert "unavailable" in exc_info.value.message.lower()

    # Even for previously cached tokens, outage must fail closed immediately
    with pytest.raises(BrokerUnavailableError):
        broker.get_scoped_token(
            tenant_id=tenant_id,
            secret_ref=secret_ref,
            required_scope="contacts:read",
            audience="https://api.hubspot.com",
        )

    # 3. Outage Recovery: Service restored to normal operation
    broker.set_outage(False)
    restored_token = broker.get_scoped_token(
        tenant_id=tenant_id,
        secret_ref=secret_ref,
        required_scope="contacts:read",
        audience="https://api.hubspot.com",
    )
    assert restored_token is not None
    assert restored_token.token.startswith("eph_hubspot_")
