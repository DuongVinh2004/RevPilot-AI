"""
RevPilot AI — Commercial SaaS Connector Adapters Package
Conforms to DEC-001 (B2B SaaS), DEC-006 (Deduplication), DEC-007 (Broker TTL), and INV-SEC-003.
"""

from revpilot.modules.connectors.adapters.base import BaseConnectorAdapter
from revpilot.modules.connectors.adapters.broker import (
    MAX_TOKEN_TTL_SECONDS,
    CredentialBroker,
    CredentialBrokerError,
    ScopedToken,
    TokenTtlExceededError,
)
from revpilot.modules.connectors.adapters.egress import (
    DEFAULT_EGRESS_ALLOWLIST,
    EgressProxyGateway,
    EgressSecurityViolationError,
)
from revpilot.modules.connectors.adapters.salesforce import SalesforceConnectorAdapter
from revpilot.modules.connectors.adapters.stripe import StripeConnectorAdapter
from revpilot.modules.connectors.adapters.zendesk import ZendeskConnectorAdapter

__all__ = [
    "BaseConnectorAdapter",
    "CredentialBroker",
    "CredentialBrokerError",
    "DEFAULT_EGRESS_ALLOWLIST",
    "EgressProxyGateway",
    "EgressSecurityViolationError",
    "MAX_TOKEN_TTL_SECONDS",
    "SalesforceConnectorAdapter",
    "ScopedToken",
    "StripeConnectorAdapter",
    "TokenTtlExceededError",
    "ZendeskConnectorAdapter",
]
