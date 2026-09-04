"""
RevPilot AI — Identity Domain Roles and Role Registry (Rail 4).
Defines immutable Role value object and StandardRoles canonical matrix.
Enforces INV-IAM-001, INV-TEN-002, and fail-closed validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import ClassVar, Mapping

from revpilot.modules.identity.domain.permissions import Permission
from revpilot.shared.errors import ValidationError


_ROLE_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


@dataclass(frozen=True, slots=True)
class Role:
    """
    Immutable role value object containing a set of granted permissions.
    """
    name: str
    permissions: frozenset[Permission]
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError(f"Role name must be str, got {type(self.name).__name__}")

        name_clean = self.name.strip().lower()
        if not name_clean:
            raise ValidationError("Role name cannot be empty or whitespace-only")

        if not _ROLE_NAME_PATTERN.match(name_clean):
            raise ValidationError(
                f"Role name must be lowercase alphanumeric with underscores, got '{self.name}'"
            )

        if not isinstance(self.description, str):
            raise TypeError(
                f"Role description must be str, got {type(self.description).__name__}"
            )

        if not isinstance(self.permissions, frozenset):
            perms = frozenset(self.permissions)
        else:
            perms = self.permissions

        for p in perms:
            if not isinstance(p, Permission):
                raise TypeError(
                    f"All permissions must be Permission instances, got {type(p).__name__}"
                )

        object.__setattr__(self, "name", name_clean)
        object.__setattr__(self, "permissions", perms)
        object.__setattr__(self, "description", self.description.strip())

    def has_permission(self, permission: Permission | str) -> bool:
        """
        Check if any granted permission in this role matches the required permission.
        Evaluates deny-by-default.
        """
        if isinstance(permission, str):
            try:
                target = Permission.from_string(permission)
            except ValidationError:
                return False
        elif isinstance(permission, Permission):
            target = permission
        else:
            return False

        return any(p.matches(target) for p in self.permissions)


class StandardRoles:
    """
    Canonical standard roles factory and registry.
    Provides the 6 canonical roles defined in IAM-SPEC §3.4.
    """
    PLATFORM_ADMIN: ClassVar[Role] = Role(
        name="platform_admin",
        permissions=frozenset({
            Permission("*", "*"),
        }),
        description="Platform administrator with wildcard access, scoped by privileged boundary",
    )

    TENANT_ADMIN: ClassVar[Role] = Role(
        name="tenant_admin",
        permissions=frozenset({
            Permission("tenant", "manage"),
            Permission("user", "manage"),
            Permission("investigation", "*"),
            Permission("evidence", "*"),
            Permission("audit", "read"),
            Permission("policy", "read"),
        }),
        description="Tenant user management, settings, and full investigation management",
    )

    OPERATOR: ClassVar[Role] = Role(
        name="operator",
        permissions=frozenset({
            Permission("investigation", "create"),
            Permission("investigation", "read"),
            Permission("evidence", "read"),
            Permission("tool", "invoke"),
            Permission("approval", "request"),
        }),
        description="Initiate investigations, request tool actions, approve eligible low-risk proposals",
    )

    ANALYST: ClassVar[Role] = Role(
        name="analyst",
        permissions=frozenset({
            Permission("investigation", "read"),
            Permission("evidence", "read"),
            Permission("analytics", "read"),
            Permission("audit", "read"),
        }),
        description="Read investigations, execute analytical queries, view evidence and audit logs",
    )

    AUDITOR: ClassVar[Role] = Role(
        name="auditor",
        permissions=frozenset({
            Permission("audit", "read"),
            Permission("compliance", "read"),
            Permission("investigation", "read"),
            Permission("evidence", "read"),
        }),
        description="Read-only access to audit logs, compliance reports, and investigation evidence",
    )

    AGENT_DELEGATE: ClassVar[Role] = Role(
        name="agent_delegate",
        permissions=frozenset({
            Permission("investigation", "read"),
            Permission("evidence", "read"),
            Permission("tool", "invoke"),
        }),
        description="Scoped execution identity for AI agents running within an approved workflow",
    )

    _REGISTRY: ClassVar[Mapping[str, Role]] = {
        "platform_admin": PLATFORM_ADMIN,
        "tenant_admin": TENANT_ADMIN,
        "operator": OPERATOR,
        "analyst": ANALYST,
        "auditor": AUDITOR,
        "agent_delegate": AGENT_DELEGATE,
    }

    @classmethod
    def get_role(cls, name: str) -> Role:
        """
        Lookup standard role by lowercase name.
        Raises ValidationError if the role is unknown.
        """
        if not isinstance(name, str):
            raise ValidationError(
                f"Role name must be a string, got {type(name).__name__}"
            )

        key = name.strip().lower()
        if not key:
            raise ValidationError("Role name cannot be empty or whitespace-only")

        if key not in cls._REGISTRY:
            raise ValidationError(
                f"Unknown standard role: '{name}'. Canonical roles are: {', '.join(sorted(cls._REGISTRY.keys()))}"
            )

        return cls._REGISTRY[key]

    @classmethod
    def all_roles(cls) -> tuple[Role, ...]:
        """Return all canonical standard roles."""
        return tuple(cls._REGISTRY.values())
