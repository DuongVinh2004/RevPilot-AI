"""
RevPilot AI — Governed Forward Egress Proxy Gateway
Specification: docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §5.2
Specification: docs/15-security/SECURITY-ARCHITECTURE.md §4
Conforms to INV-SEC-003 and AC-DEP-02.
"""

from __future__ import annotations

import fnmatch
from urllib.parse import urlparse

from revpilot.shared.errors import DomainError

# Authorized external B2B SaaS domains for commercial pilot
DEFAULT_EGRESS_ALLOWLIST = [
    "api.stripe.com",
    "*.salesforce.com",
    "login.salesforce.com",
    "*.zendesk.com",
]


class EgressSecurityViolationError(DomainError):
    """Raised when an outbound connection targets an unauthorized domain."""
    def __init__(self, target_url: str, host: str) -> None:
        super().__init__(
            code="ERR_EGRESS_BLOCKED",
            message=f"Outbound connection to host '{host}' blocked by Governed Egress Proxy (INV-SEC-003).",
            details={"target_url": target_url, "host": host},
            retryable=False,
        )


class EgressProxyGateway:
    """
    Forward Egress Proxy enforcing strict domain allowlist.
    Prevents SSRF, data exfiltration, and unauthorized external socket calls (INV-SEC-003).
    """

    def __init__(self, allowlist: list[str] | None = None) -> None:
        self.allowlist = allowlist or DEFAULT_EGRESS_ALLOWLIST

    def is_domain_allowed(self, hostname: str) -> bool:
        """Check if hostname matches any allowlist pattern (including wildcards)."""
        host = hostname.lower().strip()
        for pattern in self.allowlist:
            pat = pattern.lower().strip()
            if host == pat or fnmatch.fnmatch(host, pat):
                return True
        return False

    def validate_outbound_url(self, target_url: str) -> str:
        """
        Validates URL against egress allowlist.
        Returns the clean hostname if permitted, raises EgressSecurityViolationError otherwise.
        """
        parsed = urlparse(target_url)
        hostname = parsed.hostname

        if not hostname:
            raise EgressSecurityViolationError(target_url, "UNKNOWN_HOST")

        if not self.is_domain_allowed(hostname):
            raise EgressSecurityViolationError(target_url, hostname)

        return hostname

    def execute_mock_egress(self, target_url: str, method: str = "GET") -> dict[str, str | int]:
        """
        Simulates an outbound request through the proxy.
        Validates domain allowlist before simulated socket transmission.
        """
        host = self.validate_outbound_url(target_url)
        return {
            "status": 200,
            "host": host,
            "method": method,
            "egress_proxy": "ALLOWED_VERIFIED",
        }
