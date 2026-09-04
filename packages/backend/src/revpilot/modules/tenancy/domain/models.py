"""
RevPilot AI — Tenancy Module Domain Models
Domain entities, value objects, and lifecycle state machines for multi-tenant isolation.
Conforms to ADR-0001, ADR-0005, MODULE-BOUNDARIES.md, and MULTI-TENANCY-SPEC.md.
"""

from __future__ import annotations
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

from revpilot.shared.identifiers import TenantId, OrganizationId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext
from revpilot.shared.errors import ValidationError, TenancyViolationError


class TenantStatus(str, Enum):
    """Lifecycle states for a tenant per TENANT-OPERATIONS-SPEC.md §2."""
    REQUESTED = "requested"
    PROVISIONING = "provisioning"
    ACTIVATING = "activating"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LEGAL_HOLD = "legal_hold"
    EXPORTING = "exporting"
    DELETING = "deleting"
    DELETION_STAGED = "deletion_staged"
    DELETED = "deleted"
    TERMINATED = "terminated"
    PROVISION_FAILED = "provision_failed"
    RECOVERING = "recovering"
    DEACTIVATED = "deactivated"


class SubscriptionTier(str, Enum):
    """Isolation and entitlement tiers per ADR-0005."""
    SHARED = "shared"
    ENTERPRISE = "enterprise"
    REGULATED = "regulated"


@dataclass(frozen=True, slots=True)
class Entitlement:
    """
    Immutable entitlement profile governing tenant capabilities and resource limits.
    """
    tier: SubscriptionTier
    max_seats: int = 5
    features: frozenset[str] = field(default_factory=frozenset)
    quotas: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.tier, SubscriptionTier):
            raise TypeError(f"tier must be a SubscriptionTier enum, got {type(self.tier).__name__}")
        if self.max_seats < 1:
            raise ValidationError(f"max_seats must be at least 1, got {self.max_seats}")

    def has_feature(self, feature_name: str) -> bool:
        """Check whether entitlement grants specified feature (case-insensitive)."""
        return feature_name.lower() in (f.lower() for f in self.features)

    def get_quota(self, quota_name: str, default: int = 0) -> int:
        """Get integer quota limit by key."""
        return self.quotas.get(quota_name, default)


@dataclass(frozen=True, slots=True)
class TenantProvisioningRequest:
    """Idempotent tenant creation and provisioning request (INV-TEN-001)."""
    request_id: UUIDv7
    organization_id: OrganizationId
    name: str
    admin_email: str
    tier: SubscriptionTier = SubscriptionTier.SHARED
    tenant_id: TenantId | None = None
    idempotency_key: str | None = None
    created_at: UtcDateTime = field(default_factory=UtcDateTime.now)


@dataclass(frozen=True, slots=True)
class LegalHoldRecord:
    """Immutable record of legal hold applied to a tenant (TENANT-OPERATIONS-SPEC.md §3.6)."""
    matter_id: str
    tenant_id: TenantId
    justification: str
    applied_by: str
    applied_at: UtcDateTime
    released_at: UtcDateTime | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class TenantExportBundle:
    """Packaged, tenant-isolated data export snapshot sealed with SHA-256 (DATA-GOVERNANCE.md §3)."""
    export_id: UUIDv7
    tenant_id: TenantId
    as_of_time: UtcDateTime
    manifest_json: str
    manifest_sha256: str
    record_count: int
    data_payload: dict[str, Any]
    status: str = "SEALED"


@dataclass(frozen=True, slots=True)
class DeletionCertificate:
    """Cryptographic receipt proving complete cascade deletion across all 10 stores (DATA-GOVERNANCE.md §4)."""
    certificate_id: UUIDv7
    tenant_id: TenantId
    deleted_at: UtcDateTime
    purged_partitions: list[str]
    deletion_digest_sha256: str
    dual_approvers: list[str]


@dataclass(frozen=True, slots=True)
class Organization:
    """
    Enterprise customer organization boundary owning one or more tenants.
    """
    id: OrganizationId
    name: str
    created_at: UtcDateTime
    is_active: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.id, OrganizationId):
            raise TypeError(f"id must be OrganizationId, got {type(self.id).__name__}")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Organization name cannot be empty or whitespace")
        if not isinstance(self.created_at, UtcDateTime):
            raise TypeError(f"created_at must be UtcDateTime, got {type(self.created_at).__name__}")


@dataclass
class Tenant:
    """
    Tenant aggregate root governing isolation boundary, lifecycle status, and context generation.
    """
    id: TenantId
    organization_id: OrganizationId
    name: str
    status: TenantStatus
    tier: SubscriptionTier
    entitlement: Entitlement
    created_at: UtcDateTime
    updated_at: UtcDateTime
    suspension_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, TenantId):
            raise TypeError(f"id must be TenantId, got {type(self.id).__name__}")
        if not isinstance(self.organization_id, OrganizationId):
            raise TypeError(f"organization_id must be OrganizationId, got {type(self.organization_id).__name__}")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Tenant name cannot be empty or whitespace")
        if not isinstance(self.status, TenantStatus):
            raise TypeError(f"status must be TenantStatus, got {type(self.status).__name__}")
        if not isinstance(self.tier, SubscriptionTier):
            raise TypeError(f"tier must be SubscriptionTier, got {type(self.tier).__name__}")
        if not isinstance(self.entitlement, Entitlement):
            raise TypeError(f"entitlement must be Entitlement, got {type(self.entitlement).__name__}")
        if not isinstance(self.created_at, UtcDateTime):
            raise TypeError(f"created_at must be UtcDateTime, got {type(self.created_at).__name__}")
        if not isinstance(self.updated_at, UtcDateTime):
            raise TypeError(f"updated_at must be UtcDateTime, got {type(self.updated_at).__name__}")

    def is_active(self) -> bool:
        """Check if tenant is in ACTIVE operational status."""
        return self.status == TenantStatus.ACTIVE

    def can_ingress(self) -> bool:
        """Check if tenant is permitted to accept ingress API traffic."""
        return self.status in (TenantStatus.ACTIVE, TenantStatus.EXPORTING)

    def activate(self) -> None:
        """
        Transition tenant to ACTIVE status.
        Terminal status DEACTIVATED, DELETED, or TERMINATED cannot be activated.
        """
        if self.status in (TenantStatus.DEACTIVATED, TenantStatus.DELETED, TenantStatus.TERMINATED):
            raise ValidationError(f"Cannot activate tenant in terminal state ({self.status.value})")
        self.status = TenantStatus.ACTIVE
        self.suspension_reason = None
        self.updated_at = UtcDateTime.now()

    def suspend(self, reason: str) -> None:
        """
        Transition tenant to SUSPENDED status.
        Requires explicit non-empty reason.
        """
        if self.status in (TenantStatus.DEACTIVATED, TenantStatus.DELETED, TenantStatus.TERMINATED):
            raise ValidationError(f"Cannot suspend tenant in terminal state ({self.status.value})")
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError("Suspension reason cannot be empty")
        self.status = TenantStatus.SUSPENDED
        self.suspension_reason = reason.strip()
        self.updated_at = UtcDateTime.now()

    def apply_legal_hold(self) -> None:
        """Apply legal hold to tenant."""
        if self.status in (TenantStatus.DELETED, TenantStatus.TERMINATED):
            raise ValidationError(f"Cannot apply legal hold to deleted tenant ({self.status.value})")
        self.status = TenantStatus.LEGAL_HOLD
        self.updated_at = UtcDateTime.now()

    def release_legal_hold(self, restore_status: TenantStatus = TenantStatus.SUSPENDED) -> None:
        """Release legal hold, restoring target status."""
        if self.status != TenantStatus.LEGAL_HOLD:
            return
        self.status = restore_status
        self.updated_at = UtcDateTime.now()

    def stage_deletion(self) -> None:
        """Stage tenant for cascade deletion."""
        if self.status == TenantStatus.LEGAL_HOLD:
            from revpilot.modules.tenancy.domain.errors import LegalHoldActiveError
            raise LegalHoldActiveError("Cannot delete tenant under legal hold")
        self.status = TenantStatus.DELETION_STAGED
        self.updated_at = UtcDateTime.now()

    def mark_deleted(self) -> None:
        """Transition tenant to DELETED terminal status."""
        self.status = TenantStatus.DELETED
        self.updated_at = UtcDateTime.now()

    def deactivate(self) -> None:
        """Transition tenant to terminal DEACTIVATED status."""
        self.status = TenantStatus.DEACTIVATED
        self.updated_at = UtcDateTime.now()

    def to_context(self) -> TenantContext:
        """
        Produce verified immutable TenantContext for execution pipelines.
        Enforces fail-closed isolation: only ACTIVE tenants may produce valid context.
        """
        if not self.is_active():
            raise TenancyViolationError(
                f"Cannot generate TenantContext: tenant '{self.id}' is not active (status: {self.status.value})",
                details={"tenant_id": str(self.id), "status": self.status.value},
            )
        return TenantContext(
            tenant_id=self.id,
            organization_id=self.organization_id,
            tier=self.tier.value,
            is_active=True,
        )
