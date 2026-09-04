"""
RevPilot AI — Tests: Governed Forward Egress Proxy Gateway
Specification: docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §5.2
Specification: docs/15-security/SECURITY-ARCHITECTURE.md §4
Conforms to INV-SEC-003 and AC-DEP-02.
"""

from __future__ import annotations

import sys
import pytest

from revpilot.modules.connectors.adapters.egress import (
    EgressProxyGateway,
    EgressSecurityViolationError,
)


@pytest.fixture(autouse=True)
def _isolate_connectors_module():
    """Ensure connectors module is not leaked to cross-module dependency checks."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.connectors"):
            sys.modules.pop(mod, None)


def test_egress_proxy_allows_authorized_saas_endpoints():
    """INV-SEC-003: Governed proxy permits outbound traffic only to authorized SaaS domains."""
    proxy = EgressProxyGateway()

    allowed_urls = [
        "https://api.stripe.com/v1/invoices",
        "https://api.stripe.com/v1/balance",
        "https://login.salesforce.com/services/oauth2/token",
        "https://revpilot-corp.my.salesforce.com/services/data/v60.0/",
        "https://acme-support.zendesk.com/api/v2/tickets.json",
    ]

    for url in allowed_urls:
        result = proxy.execute_mock_egress(url, method="GET")
        assert result["status"] == 200
        assert result["egress_proxy"] == "ALLOWED_VERIFIED"


def test_egress_proxy_blocks_unauthorized_endpoints():
    """INV-SEC-003: Outbound traffic to unauthorized hosts is strictly blocked fail-closed."""
    proxy = EgressProxyGateway()

    unauthorized_urls = [
        "https://attacker.com/leak-keys",
        "https://evil-salesforce.com/exfiltrate",
        "https://stripe.com.attacker.net/api",
        "http://169.254.169.254/latest/meta-data/",  # AWS IMDS SSRF attempt
        "http://localhost:8080/admin",
    ]

    for url in unauthorized_urls:
        with pytest.raises(EgressSecurityViolationError) as exc_info:
            proxy.execute_mock_egress(url)
        assert exc_info.value.code == "ERR_EGRESS_BLOCKED"
        assert "blocked by Governed Egress Proxy" in exc_info.value.message


def test_egress_proxy_custom_allowlist():
    """Verify custom allowlist enforcement."""
    custom_proxy = EgressProxyGateway(allowlist=["custom.internal.service", "*.acme.org"])

    assert custom_proxy.is_domain_allowed("custom.internal.service")
    assert custom_proxy.is_domain_allowed("app.acme.org")
    assert not custom_proxy.is_domain_allowed("api.stripe.com")
