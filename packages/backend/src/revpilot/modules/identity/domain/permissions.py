"""
RevPilot AI — Identity Domain Permissions and Policy Attributes (Rail 4).
Canonical Permission value object and PolicyAttributes ABAC context.
Enforces INV-IAM-001, INV-TEN-002, and fail-closed validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from revpilot.shared.errors import ValidationError
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\*]+$")


@dataclass(frozen=True, slots=True)
class Permission:
    """
    Immutable permission value object in canonical format `resource:action`.
    Supports exact matching and wildcard actions/resources.
    """
    resource: str
    action: str

    def __post_init__(self) -> None:
        if not isinstance(self.resource, str):
            raise TypeError(f"resource must be str, got {type(self.resource).__name__}")
        if not isinstance(self.action, str):
            raise TypeError(f"action must be str, got {type(self.action).__name__}")

        res_clean = self.resource.strip().lower()
        act_clean = self.action.strip().lower()

        if not res_clean:
            raise ValidationError("Permission resource cannot be empty or whitespace-only")
        if not act_clean:
            raise ValidationError("Permission action cannot be empty or whitespace-only")

        if ":" in res_clean or ":" in act_clean:
            raise ValidationError("Permission resource and action must not contain colon character")

        if not _IDENTIFIER_PATTERN.match(res_clean):
            raise ValidationError(
                f"Permission resource contains invalid characters: '{self.resource}'"
            )
        if not _IDENTIFIER_PATTERN.match(act_clean):
            raise ValidationError(
                f"Permission action contains invalid characters: '{self.action}'"
            )

        object.__setattr__(self, "resource", res_clean)
        object.__setattr__(self, "action", act_clean)

    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"

    def __repr__(self) -> str:
        return f"Permission({self.resource!r}, {self.action!r})"

    def matches(self, required: Permission) -> bool:
        """
        Check if this granted permission satisfies the required permission.
        - Exact match: self.resource == required.resource and self.action == required.action.
        - Action wildcard: self.resource == required.resource and self.action == "*".
        - Full wildcard: self.resource == "*" and (self.action == "*" or self.action == required.action).
        """
        if not isinstance(required, Permission):
            return False

        if self.resource == "*":
            return self.action == "*" or self.action == required.action

        if self.resource == required.resource:
            return self.action == "*" or self.action == required.action

        return False

    @classmethod
    def from_string(cls, val: str) -> Permission:
        """
        Parse canonical 'resource:action' permission string.
        Raises ValidationError if format is invalid or parts are missing/empty.
        """
        if not isinstance(val, str):
            raise ValidationError(
                f"Permission specification must be a string, got {type(val).__name__}"
            )

        clean = val.strip()
        if not clean:
            raise ValidationError("Permission string cannot be empty or whitespace-only")

        if clean.count(":") != 1:
            raise ValidationError(
                f"Permission string must contain exactly one colon separating 'resource:action', got '{val}'"
            )

        resource, action = clean.split(":", 1)
        if not resource.strip():
            raise ValidationError("Permission string resource component cannot be empty")
        if not action.strip():
            raise ValidationError("Permission string action component cannot be empty")

        return cls(resource=resource.strip(), action=action.strip())


@dataclass(frozen=True, slots=True)
class PolicyAttributes:
    """
    Immutable ABAC policy attributes value object.
    Carries contextual metadata (tenant boundary, resource context, time, task) for authorization.
    """
    tenant_id: TenantId
    resource_id: str | None = None
    resource_tenant_id: TenantId | None = None
    task_id: str | None = None
    as_of: UtcDateTime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, TenantId):
            if isinstance(self.tenant_id, str) and self.tenant_id.strip():
                object.__setattr__(self, "tenant_id", TenantId(self.tenant_id.strip()))
            else:
                raise TypeError(
                    f"tenant_id must be TenantId instance, got {type(self.tenant_id).__name__}"
                )

        if self.resource_tenant_id is not None:
            if not isinstance(self.resource_tenant_id, TenantId):
                if isinstance(self.resource_tenant_id, str) and self.resource_tenant_id.strip():
                    object.__setattr__(
                        self, "resource_tenant_id", TenantId(self.resource_tenant_id.strip())
                    )
                else:
                    raise TypeError(
                        f"resource_tenant_id must be TenantId or None, got {type(self.resource_tenant_id).__name__}"
                    )

        if self.resource_id is not None:
            if not isinstance(self.resource_id, str):
                raise TypeError(
                    f"resource_id must be str or None, got {type(self.resource_id).__name__}"
                )
            res_id_clean = self.resource_id.strip()
            if not res_id_clean:
                raise ValidationError("resource_id cannot be empty or whitespace-only")
            object.__setattr__(self, "resource_id", res_id_clean)

        if self.task_id is not None:
            if not isinstance(self.task_id, str):
                raise TypeError(f"task_id must be str or None, got {type(self.task_id).__name__}")
            task_id_clean = self.task_id.strip()
            if not task_id_clean:
                raise ValidationError("task_id cannot be empty or whitespace-only")
            object.__setattr__(self, "task_id", task_id_clean)

        if self.as_of is not None and not isinstance(self.as_of, UtcDateTime):
            raise TypeError(f"as_of must be UtcDateTime or None, got {type(self.as_of).__name__}")
