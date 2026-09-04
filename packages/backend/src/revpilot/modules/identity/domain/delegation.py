"""
RevPilot AI — Delegation Domain Entity, Factory, and Revocation Registry (Rail 4).
Enforces INV-IAM-002, INV-ACT-003, INV-SEC-001, and fail-closed isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import threading
from typing import Iterable
import uuid

from revpilot.modules.identity.domain.models import Principal, PrincipalType
from revpilot.modules.identity.domain.permissions import Permission
from revpilot.shared.errors import (
    AuthorizationError,
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.identifiers import PrincipalId, TenantId
from revpilot.shared.temporal import UtcDateTime


@dataclass(frozen=True, slots=True)
class DelegationToken:
    """
    Immutable delegation token representing constrained, time-bound transfer of authority
    from a human delegator to an AI agent actor.
    """
    delegation_id: str
    delegator_id: PrincipalId
    tenant_id: TenantId
    task_id: str
    allowed_capabilities: frozenset[Permission]
    target_resources: frozenset[str]
    issued_at: UtcDateTime
    expires_at: UtcDateTime
    revocation_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.delegation_id, str) or not self.delegation_id.strip():
            raise ValidationError("delegation_id must be a non-empty string")
        if not self.delegation_id.startswith("del_"):
            raise ValidationError(
                f"delegation_id must start with 'del_', got '{self.delegation_id}'"
            )

        if not isinstance(self.delegator_id, PrincipalId):
            raise TypeError(
                f"delegator_id must be PrincipalId, got {type(self.delegator_id).__name__}"
            )

        if not isinstance(self.tenant_id, TenantId):
            raise TypeError(
                f"tenant_id must be TenantId, got {type(self.tenant_id).__name__}"
            )

        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise ValidationError("task_id must be a non-empty string")

        if not isinstance(self.allowed_capabilities, frozenset):
            object.__setattr__(self, "allowed_capabilities", frozenset(self.allowed_capabilities))
        if not self.allowed_capabilities:
            raise ValidationError("allowed_capabilities cannot be empty")
        for cap in self.allowed_capabilities:
            if not isinstance(cap, Permission):
                raise TypeError(
                    f"allowed_capabilities must contain only Permission instances, got {type(cap).__name__}"
                )

        if not isinstance(self.target_resources, frozenset):
            object.__setattr__(self, "target_resources", frozenset(self.target_resources))
        if not self.target_resources:
            raise ValidationError("target_resources cannot be empty")
        for target in self.target_resources:
            if not isinstance(target, str) or not target.strip():
                raise ValidationError("target_resources items must be non-empty strings")

        if not isinstance(self.issued_at, UtcDateTime):
            raise TypeError(
                f"issued_at must be UtcDateTime, got {type(self.issued_at).__name__}"
            )
        if not isinstance(self.expires_at, UtcDateTime):
            raise TypeError(
                f"expires_at must be UtcDateTime, got {type(self.expires_at).__name__}"
            )

        if self.expires_at.value <= self.issued_at.value:
            raise ValidationError("expires_at must be strictly after issued_at")

        if not isinstance(self.revocation_version, int) or self.revocation_version < 1:
            raise ValidationError("revocation_version must be an integer >= 1")

    def is_expired(self, as_of: UtcDateTime | None = None) -> bool:
        """
        Check if delegation token is expired as of given time (defaults to UtcDateTime.now()).
        Evaluates fail-closed: as_of >= expires_at returns True.
        """
        check_time = as_of or UtcDateTime.now()
        return check_time.value >= self.expires_at.value

    def allows_capability(self, capability: Permission | str) -> bool:
        """
        Check if this delegation grants the requested capability.
        Evaluates deny-by-default.
        """
        if isinstance(capability, str):
            try:
                target_perm = Permission.from_string(capability)
            except ValidationError:
                return False
        elif isinstance(capability, Permission):
            target_perm = capability
        else:
            return False

        return any(cap.matches(target_perm) for cap in self.allowed_capabilities)

    def allows_target(self, resource: str) -> bool:
        """
        Check if resource matches any target in target_resources.
        Target matching rules:
        - Exact match: resource == target.
        - Segment boundary prefix match:
          - resource.startswith(f"{target}/") or resource.startswith(f"{target}:")
          - If target ends with '/' or ':', resource.startswith(target)
          - If target ends with '/*', resource.startswith(target[:-1])
        - Fail-closed: Arbitrary string prefixes without segment boundaries (e.g. /tenant/a matching /tenant/abc)
          are strictly prohibited and return False.
        """
        if not isinstance(resource, str) or not resource.strip():
            return False

        clean_res = resource.strip()
        for target in self.target_resources:
            clean_tgt = target.strip()
            if clean_tgt == "*":
                return True
            if clean_res == clean_tgt:
                return True

            if clean_tgt.endswith("/*"):
                prefix = clean_tgt[:-1]  # leaves trailing '/'
                if clean_res.startswith(prefix):
                    return True
            elif clean_tgt.endswith("/") or clean_tgt.endswith(":"):
                if clean_res.startswith(clean_tgt):
                    return True
            else:
                if clean_res.startswith(f"{clean_tgt}/") or clean_res.startswith(f"{clean_tgt}:"):
                    return True

        return False


def _delegator_has_permission(delegator: Principal, required: Permission) -> bool:
    """Helper to check if principal possesses permission via exact or wildcard role permissions."""
    for p_str in delegator.permissions:
        try:
            p = Permission.from_string(p_str)
            if p.matches(required):
                return True
        except ValidationError:
            if p_str.strip().lower() == str(required).lower():
                return True
    return False


def issue_delegation(
    delegator: Principal,
    tenant_id: TenantId,
    task_id: str,
    capabilities: Iterable[Permission],
    target_resources: Iterable[str],
    duration_seconds: int = 3600,
    as_of: UtcDateTime | None = None,
) -> DelegationToken:
    """
    Factory function for issuing a new DelegationToken with invariant enforcement.
    - Delegator cannot be AGENT (sub-delegation prohibited).
    - Duration between 60 and 86,400 seconds.
    - Tenant strictly matches delegator tenant.
    - Capabilities cannot be empty and cannot contain approval authority (INV-ACT-003).
    - Requested capabilities cannot exceed delegator's held permissions (INV-IAM-002).
    - Target resources cannot be empty.
    """
    if not isinstance(delegator, Principal):
        raise TypeError(f"delegator must be Principal, got {type(delegator).__name__}")

    if delegator.type == PrincipalType.AGENT:
        raise AuthorizationError("Delegated agents cannot sub-delegate authority")

    if not isinstance(tenant_id, TenantId):
        raise TypeError(f"tenant_id must be TenantId, got {type(tenant_id).__name__}")

    if delegator.tenant_id is None or delegator.tenant_id != tenant_id:
        raise TenancyViolationError(
            f"Delegation tenant '{tenant_id}' does not match delegator tenant '{delegator.tenant_id}'"
        )

    if not isinstance(task_id, str) or not task_id.strip():
        raise ValidationError("task_id must be a non-empty string")

    if not isinstance(duration_seconds, int) or isinstance(duration_seconds, bool):
        raise ValidationError("duration_seconds must be an integer")

    if duration_seconds < 60 or duration_seconds > 86400:
        raise ValidationError(
            f"Delegation duration must be between 60 and 86,400 seconds, got {duration_seconds}s"
        )

    caps = frozenset(capabilities) if not isinstance(capabilities, frozenset) else capabilities
    if not caps:
        raise ValidationError("capabilities cannot be empty")

    for cap in caps:
        if not isinstance(cap, Permission):
            raise TypeError(
                f"All capabilities must be Permission instances, got {type(cap).__name__}"
            )

        # Enforce INV-ACT-003: Delegation cannot grant approval authority
        if cap.resource == "approval" or (cap.resource == "*" and cap.action in ("*", "grant")):
            raise AuthorizationError(
                "Delegated agents cannot receive approval authority (INV-ACT-003)"
            )
        if cap.matches(Permission("approval", "grant")):
            raise AuthorizationError(
                "Delegated agents cannot receive approval authority (INV-ACT-003)"
            )

        # Enforce INV-IAM-002: Capability cannot exceed delegator scope
        if not _delegator_has_permission(delegator, cap):
            raise AuthorizationError(
                f"Delegation capability '{cap}' exceeds delegator permissions (INV-IAM-002)"
            )

    targets = frozenset(target_resources) if not isinstance(target_resources, frozenset) else target_resources
    if not targets:
        raise ValidationError("target_resources cannot be empty")

    for tgt in targets:
        if not isinstance(tgt, str) or not tgt.strip():
            raise ValidationError("target_resources items must be non-empty strings")

    start_time = as_of or UtcDateTime.now()
    end_time = UtcDateTime(start_time.value + timedelta(seconds=duration_seconds))

    del_id = f"del_{uuid.uuid4().hex[:16]}"

    return DelegationToken(
        delegation_id=del_id,
        delegator_id=delegator.id,
        tenant_id=tenant_id,
        task_id=task_id.strip(),
        allowed_capabilities=caps,
        target_resources=targets,
        issued_at=start_time,
        expires_at=end_time,
        revocation_version=1,
    )


class DelegationRevocationRegistry:
    """
    Thread-safe in-memory registry tracking revoked delegation tokens.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._revocations: dict[str, str] = {}

    def revoke(self, delegation_id: str, reason: str = "") -> None:
        """
        Record early revocation of a delegation token.
        """
        if not isinstance(delegation_id, str) or not delegation_id.strip():
            raise ValidationError("delegation_id must be a non-empty string")

        with self._lock:
            self._revocations[delegation_id.strip()] = reason.strip()

    def is_revoked(self, delegation_id: str) -> bool:
        """
        Check if a delegation token has been revoked.
        """
        if not isinstance(delegation_id, str) or not delegation_id.strip():
            return False

        with self._lock:
            return delegation_id.strip() in self._revocations

    def get_revocation_reason(self, delegation_id: str) -> str | None:
        """
        Get revocation reason for a revoked delegation token, or None if not revoked.
        """
        with self._lock:
            return self._revocations.get(delegation_id.strip())
