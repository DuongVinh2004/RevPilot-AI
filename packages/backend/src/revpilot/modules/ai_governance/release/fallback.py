"""
RevPilot AI — Real-Time Model Fallback Chain & Graceful Degradation
Specification: docs/20-evaluation/MODEL-RELEASE-PROCESS.md §6.1
Conforms to INV-REL-001, ADR-0011, AC-P08-004-01.
"""

from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, ConfigDict

from revpilot.shared.errors import DomainError

logger = logging.getLogger(__name__)


class FallbackExhaustedError(DomainError):
    """All calibrated models unavailable; complex investigation halted gracefully (Status 503, Retryable)."""

    def __init__(
        self,
        message: str = "Service temporarily degraded",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="FALLBACK_EXHAUSTED",
            message=message,
            details=details,
            retryable=True,
        )
        self.status_code = 503


class ResolvedModelEndpoint(BaseModel):
    """Resolved model execution target with fallback and degradation metadata."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    endpoint_id: str
    model_id: str
    provider: str
    tier: str = "frontier"
    is_fallback: bool
    degraded: bool
    status_message: str


class ModelFallbackRouter:
    """
    Manages primary-to-secondary model fallback during provider outages or rate limits (§6.1).
    Enforces INV-REL-001 (fail closed on exhaustion rather than uncalibrated delegation).
    """

    # Pre-calibrated paired frontier fallback endpoints (§6.1)
    DEFAULT_FALLBACK_PAIRS: dict[str, dict[str, str]] = {
        "claude-3-5-sonnet-20241022": {
            "provider": "anthropic",
            "secondary_model_id": "gpt-4o-2024-08-06",
            "secondary_provider": "openai",
        },
        "gpt-4o-2024-08-06": {
            "provider": "openai",
            "secondary_model_id": "claude-3-5-sonnet-20241022",
            "secondary_provider": "anthropic",
        },
    }

    def __init__(self, fallback_pairs: dict[str, dict[str, str]] | None = None) -> None:
        self._pairs = fallback_pairs or dict(self.DEFAULT_FALLBACK_PAIRS)
        self._outaged_models: set[str] = set()

    def mark_provider_outage(self, model_id: str) -> None:
        """Record model provider outage or rate-limiting (HTTP 429/503)."""
        self._outaged_models.add(model_id)
        logger.warning("MODEL_PROVIDER_OUTAGE_MARKED: model=%s", model_id)

    def recover_provider(self, model_id: str) -> None:
        """Mark model provider recovered."""
        self._outaged_models.discard(model_id)
        logger.info("MODEL_PROVIDER_RECOVERED: model=%s", model_id)

    def route_model_invocation(
        self,
        primary_model_id: str,
        tenant_id: str,
    ) -> ResolvedModelEndpoint:
        """
        Route request to active primary or calibrated secondary fallback (§6.1).
        Halts gracefully with 503 if both are exhausted.
        """
        pair_info = self._pairs.get(primary_model_id, {
            "provider": "default_provider",
            "secondary_model_id": f"{primary_model_id}_secondary",
            "secondary_provider": "secondary_provider",
        })

        # 1. Primary available
        if primary_model_id not in self._outaged_models:
            return ResolvedModelEndpoint(
                endpoint_id=f"ep_{primary_model_id}",
                model_id=primary_model_id,
                provider=pair_info["provider"],
                tier="frontier",
                is_fallback=False,
                degraded=False,
                status_message=f"Primary model active for tenant {tenant_id}",
            )

        # 2. Primary outaged -> Check secondary
        sec_model_id = pair_info["secondary_model_id"]
        if sec_model_id not in self._outaged_models:
            logger.info("FALLBACK_INVOCATION_ACTIVE: primary=%s -> secondary=%s", primary_model_id, sec_model_id)
            return ResolvedModelEndpoint(
                endpoint_id=f"ep_{sec_model_id}",
                model_id=sec_model_id,
                provider=pair_info["secondary_provider"],
                tier="frontier",
                is_fallback=True,
                degraded=True,
                status_message=f"Operating on calibrated secondary fallback {sec_model_id}",
            )

        # 3. Graceful degradation: all frontier models unavailable (INV-REL-001)
        logger.error(
            "ALL_MODELS_EXHAUSTED: primary=%s secondary=%s for tenant=%s",
            primary_model_id,
            sec_model_id,
            tenant_id,
        )
        raise FallbackExhaustedError(
            f"All frontier models unavailable for '{primary_model_id}'. "
            "Complex causal investigations halted gracefully to prevent uncalibrated hallucination (INV-REL-001).",
            details={
                "primary_model": primary_model_id,
                "secondary_model": sec_model_id,
                "tenant_id": str(tenant_id),
            },
        )

    def handle_provider_outage(self, primary_model_id: str) -> ResolvedModelEndpoint:
        """Convenience method to inject outage and resolve immediate fallback endpoint."""
        self.mark_provider_outage(primary_model_id)
        return self.route_model_invocation(primary_model_id, tenant_id="global")
