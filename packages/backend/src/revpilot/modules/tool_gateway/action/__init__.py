"""
RevPilot AI — Tool Gateway Action Module
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7.1, §7.2
"""

from revpilot.modules.tool_gateway.action.credential_broker import (
    CredentialBroker,
    EphemeralCredential,
    GatewayError,
)
from revpilot.modules.tool_gateway.action.mock_adapter import (
    MockProviderAdapter,
    MockProviderResponse,
)
from revpilot.modules.tool_gateway.action.gateway import (
    ActionCapabilityGateway,
    ActionCapabilityRequest,
    agent_egress_barrier,
    compute_canonical_digest,
    scrub_secrets,
)

__all__ = [
    "ActionCapabilityGateway",
    "ActionCapabilityRequest",
    "CredentialBroker",
    "EphemeralCredential",
    "GatewayError",
    "MockProviderAdapter",
    "MockProviderResponse",
    "agent_egress_barrier",
    "compute_canonical_digest",
    "scrub_secrets",
]
