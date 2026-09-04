"""
RevPilot AI — Domain Error Hierarchy
Provides standard domain exceptions with stable machine codes, retryable flags, and client-safe serialization.
"""

from __future__ import annotations
from typing import Any


class DomainError(Exception):
    """Base exception for all RevPilot domain errors."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        """Return safe dictionary serialization of error."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r}, retryable={self.retryable})"


class NotFoundError(DomainError):
    """Requested resource was not found."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="NOT_FOUND", message=message, details=details, retryable=False)


class ValidationError(DomainError):
    """Input parameters or domain invariants violated."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="VALIDATION_ERROR", message=message, details=details, retryable=False)


class ConflictError(DomainError):
    """Resource state conflict prevented operation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="CONFLICT", message=message, details=details, retryable=False)


class AuthorizationError(DomainError):
    """Caller lacks required permission for action."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="FORBIDDEN", message=message, details=details, retryable=False)


class AuthenticationError(DomainError):
    """Caller identity could not be verified."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="UNAUTHORIZED", message=message, details=details, retryable=False)


class TenancyViolationError(DomainError):
    """Cross-tenant boundary breach or missing tenant context (INV-TEN-001, INV-TEN-002)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="TENANCY_VIOLATION", message=message, details=details, retryable=False)


class ConcurrencyError(DomainError):
    """Optimistic lock conflict or concurrent modification occurred."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="CONCURRENCY_CONFLICT", message=message, details=details, retryable=True)


class RateLimitExceededError(DomainError):
    """Operation throttled by rate limit or spend budget."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="RATE_LIMITED", message=message, details=details, retryable=True)
