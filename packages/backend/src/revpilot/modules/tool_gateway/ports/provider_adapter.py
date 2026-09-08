"""
RevPilot AI — Tool Gateway Provider Adapter Port Contract
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §4, §7.1
Conforms to INV-ACT-001, INV-ACT-002, ADR-0009.
"""

from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, ConfigDict, Field

from revpilot.modules.tool_gateway.action.credential_broker import EphemeralCredential, GatewayError
from revpilot.shared.results import Result


class ProviderResponse(BaseModel):
    """Normalized response payload returned by external or mock provider adapters."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    http_status_code: int = Field(ge=100, le=599, default=200)
    provider_tx_id: str = Field(min_length=1)
    response_payload: dict[str, Any]
    duration_ms: int = Field(ge=0, default=0)


@runtime_checkable
class ProviderAdapterPort(Protocol):
    """Authoritative port contract for external action dispatch adapters."""

    def execute(
        self,
        intent_id: str,
        action_type: str,
        target_entities: list[str],
        payload: dict[str, Any],
        credential: EphemeralCredential,
    ) -> Result[ProviderResponse, GatewayError]:
        ...
