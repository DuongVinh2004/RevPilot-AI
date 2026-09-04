"""
RevPilot AI — Tenancy Domain Errors
Standard lifecycle, isolation, and legal-hold domain exceptions per TENANT-OPERATIONS-SPEC.md §5.
"""

from __future__ import annotations
from typing import Any

from revpilot.shared.errors import DomainError


class TenantLifecycleError(DomainError):
    """Base error for tenant lifecycle operations and transitions."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=retryable)


class TenantSuspendedError(TenantLifecycleError):
    """Tenant is suspended; ingress and tool gateway access are rejected with 403."""

    def __init__(
        self,
        message: str = "Tenant is suspended",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code="TENANT_SUSPENDED", message=message, details=details, retryable=False)


class TenantInactiveError(TenantLifecycleError):
    """Tenant is inactive (e.g. PROVISIONING, DELETED, TERMINATED); ingress blocked with 403."""

    def __init__(
        self,
        message: str = "Tenant is inactive",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code="TENANT_INACTIVE", message=message, details=details, retryable=False)


class LegalHoldActiveError(TenantLifecycleError):
    """Deletion requested on tenant under legal hold; fails closed with 409 Conflict."""

    def __init__(
        self,
        message: str = "Tenant is under legal hold; deletion prohibited",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code="LEGAL_HOLD_ACTIVE", message=message, details=details, retryable=False)


class PartialProvisioningError(TenantLifecycleError):
    """Failure at resource allocation step; rolled back and marks PROVISION_FAILED."""

    def __init__(
        self,
        message: str = "Partial provisioning failure; resources rolled back",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code="PARTIAL_PROVISIONING_BLOCKED", message=message, details=details, retryable=False)


class IsolationVerificationFailedError(TenantLifecycleError):
    """Pre-activation isolation probes failed; tenant activation blocked."""

    def __init__(
        self,
        message: str = "Isolation probe verification failed; activation prohibited",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code="ISOLATION_VERIFICATION_FAILED", message=message, details=details, retryable=False)


class DeletionIncompleteError(TenantLifecycleError):
    """Storage engine failed to confirm purge; fails closed and alerts SRE."""

    def __init__(
        self,
        message: str = "Storage engine failed to confirm purge during cascade deletion",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code="DELETION_INCOMPLETE", message=message, details=details, retryable=False)
