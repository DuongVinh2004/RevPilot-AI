"""
RevPilot AI — Authorization and Role-Based Access Control Middleware
Enforces INV-IAM-001 (Deny-by-default RBAC), INV-ACT-003 (Zero Agent Self-Approval).
Conforms to docs/26-api/API-STANDARDS.md §1.
"""

from __future__ import annotations

from collections.abc import Callable
from fastapi import Depends
from revpilot.shared.context import PrincipalContext
from revpilot.shared.errors import AuthorizationError
from apps.api.middleware.authentication import get_current_principal


def require_roles(*allowed_roles: str) -> Callable[[PrincipalContext], PrincipalContext]:
    """Dependency factory verifying principal possesses at least one required role."""

    def _role_checker(principal: PrincipalContext = Depends(get_current_principal)) -> PrincipalContext:
        if principal.is_system or "SYSTEM_ADMIN" in principal.roles or "platform_admin" in principal.roles:
            return principal

        normalized_allowed = {r.upper() for r in allowed_roles}
        user_roles = {r.upper() for r in principal.roles}

        if not user_roles.intersection(normalized_allowed):
            raise AuthorizationError(
                f"Principal '{principal.principal_id}' lacks required role ({', '.join(allowed_roles)}).",
                details={"roles": list(principal.roles), "required": list(allowed_roles)},
            )
        return principal

    return _role_checker


def require_system_admin() -> Callable[[PrincipalContext], PrincipalContext]:
    """Dependency verifying caller is platform system administrator (is_system=True)."""

    def _system_checker(principal: PrincipalContext = Depends(get_current_principal)) -> PrincipalContext:
        if not principal.is_system and "SYSTEM_ADMIN" not in principal.roles and "platform_admin" not in principal.roles:
            raise AuthorizationError(
                "This administrative endpoint requires platform system privileges (INV-TEN-003).",
                details={"principal_id": str(principal.principal_id)},
            )
        return principal

    return _system_checker


def require_human_approval_authority(tier: str) -> Callable[[PrincipalContext], PrincipalContext]:
    """Dependency ensuring caller is an authenticated human operator with specified approval tier."""

    def _approval_checker(principal: PrincipalContext = Depends(get_current_principal)) -> PrincipalContext:
        # Zero Agent Self-Approval Invariant (INV-ACT-003)
        if str(principal.principal_id).startswith("agt_") or str(principal.principal_id).startswith("agent_"):
            raise AuthorizationError(
                "Autonomous AI agents are strictly forbidden from approving actions (INV-ACT-003).",
                details={"principal_id": str(principal.principal_id)},
            )

        tier_upper = tier.upper()
        if tier_upper == "TIER_1":
            allowed = {"TIER_1", "TIER_2", "TIER_3", "SYSTEM_ADMIN", "OPERATOR"}
        elif tier_upper == "TIER_2":
            allowed = {"TIER_2", "TIER_3", "SYSTEM_ADMIN"}
        else:
            allowed = {"TIER_3", "SYSTEM_ADMIN"}

        user_roles = {r.upper() for r in principal.roles}
        if not user_roles.intersection(allowed) and not principal.is_system:
            raise AuthorizationError(
                f"Principal '{principal.principal_id}' lacks {tier_upper} human approval authority.",
                details={"roles": list(principal.roles), "required_tier": tier_upper},
            )
        return principal

    return _approval_checker
