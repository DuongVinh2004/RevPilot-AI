"""
RevPilot AI — Operational Telemetry Scrubber & PII Redaction
Specification: docs/23-observability/OPERATIONS-TELEMETRY-SPEC.md §9
Conforms to NFR-PRV-001, NFR-OBS-001, AC-P08-002-01.
"""

from __future__ import annotations

import re
from typing import Any

from revpilot.shared.errors import DomainError

# --- Domain Errors ---

class ScrubberParserError(DomainError):
    """Malformed span attribute or unparseable telemetry payload (Status 500, Non-retryable)."""

    def __init__(
        self,
        message: str = "Telemetry parse error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="SCRUBBER_PARSER_ERROR",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 500


class CardinalityLimitExceededError(DomainError):
    """Dimension overload or unlisted high-cardinality label (Status 422, Non-retryable)."""

    def __init__(
        self,
        message: str = "High-cardinality label dropped",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="CARDINALITY_LIMIT_EXCEEDED",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 422


# --- Regex Patterns (§9.2) ---

BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[a-z0-9\-\._~\+\/]+=*", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b")
CREDENTIAL_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(password|secret|api_key|token)[\"']?\s*[:=]\s*[\"']?([^\"'\s]+)[\"']?",
    re.IGNORECASE,
)

SENSITIVE_KEY_NAMES = {
    "password",
    "secret",
    "api_key",
    "apikey",
    "token",
    "auth_token",
    "bearer_token",
    "access_token",
    "refresh_token",
    "authorization",
    "private_key",
    "credential",
    "credentials",
}


class TelemetryScrubber:
    """
    Regex processor to scrub bearer tokens, API keys, passwords, and email addresses
    from OpenTelemetry span attributes and operational log strings (NFR-PRV-001).
    """

    def scrub_log_payload(self, raw_log: str) -> str:
        """
        Scrub sensitive tokens, credentials, and emails from raw text string.
        Conforms to §9.2 transformations.
        """
        if not isinstance(raw_log, str):
            try:
                raw_log = str(raw_log)
            except Exception as exc:
                raise ScrubberParserError(
                    f"Failed to serialize log payload: {exc}",
                    details={"error": str(exc)},
                ) from exc

        # 1. Redact Bearer Tokens
        scrubbed = BEARER_PATTERN.sub("Bearer [REDACTED_BEARER_TOKEN]", raw_log)

        # 2. Redact Key-Value Credentials (password=..., api_key: ...) -> $1: [REDACTED]
        scrubbed = CREDENTIAL_KEY_VALUE_PATTERN.sub(r"\1: [REDACTED]", scrubbed)

        # 3. Redact Email Addresses
        scrubbed = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", scrubbed)

        return scrubbed

    def scrub_attributes(self, attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively redact sensitive key names and string values within span attributes.
        """
        if not isinstance(attributes, dict):
            raise ScrubberParserError(
                f"Span attributes must be a dictionary, got {type(attributes).__name__}",
                details={"provided_type": type(attributes).__name__},
            )

        try:
            return self._scrub_dict_recursive(attributes)
        except ScrubberParserError:
            raise
        except Exception as exc:
            raise ScrubberParserError(
                f"Error scrubbing span attributes: {exc}",
                details={"error": str(exc)},
            ) from exc

    def _scrub_dict_recursive(self, d: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for k, v in d.items():
            key_str = str(k)
            key_normalized = key_str.lower().replace("-", "_").replace(".", "_")

            if isinstance(v, dict):
                cleaned[key_str] = self._scrub_dict_recursive(v)
            elif isinstance(v, list):
                cleaned[key_str] = self._scrub_list_recursive(v)
            elif isinstance(v, str):
                scrubbed_val = self.scrub_log_payload(v)
                # If key name itself indicates sensitive credential and value was not transformed
                if any(s == key_normalized or key_normalized.endswith(f"_{s}") for s in SENSITIVE_KEY_NAMES):
                    if scrubbed_val == v:
                        cleaned[key_str] = "[REDACTED]"
                    else:
                        cleaned[key_str] = scrubbed_val
                else:
                    cleaned[key_str] = scrubbed_val
            else:
                if any(s == key_normalized or key_normalized.endswith(f"_{s}") for s in SENSITIVE_KEY_NAMES):
                    cleaned[key_str] = "[REDACTED]"
                else:
                    cleaned[key_str] = v
        return cleaned

    def _scrub_list_recursive(self, lst: list[Any]) -> list[Any]:
        cleaned_list: list[Any] = []
        for item in lst:
            if isinstance(item, dict):
                cleaned_list.append(self._scrub_dict_recursive(item))
            elif isinstance(item, list):
                cleaned_list.append(self._scrub_list_recursive(item))
            elif isinstance(item, str):
                cleaned_list.append(self.scrub_log_payload(item))
            else:
                cleaned_list.append(item)
        return cleaned_list
