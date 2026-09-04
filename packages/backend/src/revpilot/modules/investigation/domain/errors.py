"""
RevPilot AI — Investigation Domain Errors
Conforms to docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md and TASK-P03-001.
"""

from __future__ import annotations
from typing import Any
from revpilot.shared.errors import DomainError


class InvestigationDomainError(DomainError):
    """Base domain error for all investigation lifecycle and execution failures."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=retryable)
        self.http_status = http_status


class InvalidStateTransitionError(InvestigationDomainError):
    """Raised when an illegal lifecycle state transition is attempted (HTTP 409)."""

    def __init__(
        self,
        message: str = "Invalid investigation state transition",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ERR_INVALID_STATE_TRANSITION",
            message=message,
            http_status=409,
            details=details,
            retryable=False,
        )


class BudgetExceededError(InvestigationDomainError):
    """Raised when investigation spend attempts to breach the hard stop ceiling (HTTP 429)."""

    def __init__(
        self,
        message: str = "Investigation budget exhausted",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ERR_BUDGET_EXCEEDED",
            message=message,
            http_status=429,
            details=details,
            retryable=False,
        )


class TemporalValidationException(InvestigationDomainError):
    """Raised when investigation temporal boundaries violate as_of watermarking (HTTP 400)."""

    def __init__(
        self,
        message: str = "Temporal window violates as_of boundary",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ERR_TEMPORAL_LEAKAGE",
            message=message,
            http_status=400,
            details=details,
            retryable=False,
        )


__all__ = [
    "InvestigationDomainError",
    "InvalidStateTransitionError",
    "BudgetExceededError",
    "TemporalValidationException",
]
