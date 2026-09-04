"""
RevPilot AI — Mock Provider Adapter Boundary
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §4, §7.1
Conforms to INV-ACT-001: Production external adapters remain disabled in Phase 06.
Simulates external third-party execution with zero network side-effects.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.modules.tool_gateway.action.credential_broker import EphemeralCredential, GatewayError
from revpilot.shared.results import Result, Success, Failure


class MockProviderResponse(BaseModel):
    """Simulated provider response returned by the mock adapter boundary."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    http_status_code: int = Field(ge=100, le=599, default=200)
    provider_tx_id: str = Field(min_length=1)
    response_payload: dict[str, Any]
    duration_ms: int = Field(ge=0, default=15)


class MockProviderAdapter:
    """
    Sandboxed mock provider boundary.
    Executes mock actions without opening network sockets or making external API calls.
    """

    def __init__(self, default_status_code: int = 200, fail_all: bool = False) -> None:
        self.default_status_code = default_status_code
        self.fail_all = fail_all
        self.execution_history: list[dict[str, Any]] = []

    def execute(
        self,
        intent_id: str,
        action_type: str,
        target_entities: list[str],
        payload: dict[str, Any],
        credential: EphemeralCredential,
    ) -> Result[MockProviderResponse, GatewayError]:
        """
        Execute simulated external call against mock boundary.
        """
        if self.fail_all or self.default_status_code >= 500:
            return Failure(
                GatewayError(
                    code="ERR_PROVIDER_EXECUTION_FAILED",
                    message=f"Mock provider simulated external service failure ({self.default_status_code})",
                    details={"action_type": action_type, "status_code": self.default_status_code},
                )
            )

        tx_id = f"tx_mock_{intent_id[:12]}"
        response_payload = {
            "status": "DISPATCH_ACCEPTED",
            "action_type": action_type,
            "target_count": len(target_entities),
            "carrier_ref": payload.get("carrier", "mock_logistics_v1"),
            "confirmation": f"CONF-{tx_id}",
        }

        response = MockProviderResponse(
            http_status_code=self.default_status_code,
            provider_tx_id=tx_id,
            response_payload=response_payload,
            duration_ms=20,
        )

        self.execution_history.append({
            "intent_id": intent_id,
            "action_type": action_type,
            "token_id": credential.token_id,
            "response": response,
        })

        return Success(response)
