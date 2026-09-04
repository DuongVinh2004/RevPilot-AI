"""
RevPilot AI — Central Authorization Service (Rail 4).
Implements AuthorizationPort protocol, enforcing centralized deny-by-default authorization,
strict tenant isolation, delegated capability containment, and platform break-glass policy.
Conforms to INV-IAM-001, INV-TEN-001, INV-TEN-003, INV-ACT-003, and INV-REL-001.
"""

from __future__ import annotations
import logging
from typing import Any

from revpilot.modules.identity.domain.delegation import (
    DelegationRevocationRegistry,
    DelegationToken,
)
from revpilot.modules.identity.domain.models import Principal, PrivilegedContext
from revpilot.modules.identity.domain.permissions import Permission, PolicyAttributes
from revpilot.modules.identity.domain.roles import StandardRoles
from revpilot.modules.identity.ports.authorization import AuthorizationPort
from revpilot.shared.errors import AuthorizationError, ValidationError
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


class AuthorizationService(AuthorizationPort):
    """
    Central authorization service implementing AuthorizationPort.
    Evaluates ordinary principal requests, delegated token executions, and platform privileged break-glass.
    Evaluates deny-by-default and fails closed on all errors, uncertainties, and boundary breaches.
    """

    def __init__(
        self,
        revocation_registry: DelegationRevocationRegistry | None = None,
    ) -> None:
        self._revocation_registry = (
            revocation_registry
            if revocation_registry is not None
            else DelegationRevocationRegistry()
        )

    @property
    def revocation_registry(self) -> DelegationRevocationRegistry:
        """Access the underlying delegation revocation registry."""
        return self._revocation_registry

    def authorize_principal(
        self,
        principal: Principal,
        resource_tenant_id: TenantId,
        permission: Permission,
        attributes: PolicyAttributes | None = None,
    ) -> bool:
        """
        Authorize ordinary principal action against tenant resource.
        Enforces:
        - Input parameter integrity and principal active status.
        - Strict tenant isolation: principal.tenant_id == resource_tenant_id (INV-TEN-001).
        - Permission possession via direct granted permissions or assigned standard roles (INV-IAM-001).
        - PolicyAttributes alignment if provided.
        - Fails closed on any discrepancy or missing context (INV-REL-001).
        """
        try:
            # 1. Parameter and type validation
            if not isinstance(principal, Principal):
                return False
            if not isinstance(resource_tenant_id, TenantId):
                return False
            if not isinstance(permission, Permission):
                return False

            # 2. Inactive principal check
            if not principal.is_active:
                return False

            # 3. Strict tenant matching (INV-TEN-001, INV-TEN-002)
            if principal.tenant_id is None or principal.tenant_id != resource_tenant_id:
                return False

            # 4. Contextual attributes validation if present
            if attributes is not None:
                if not isinstance(attributes, PolicyAttributes):
                    return False
                if attributes.tenant_id != principal.tenant_id:
                    return False
                if (
                    attributes.resource_tenant_id is not None
                    and attributes.resource_tenant_id != resource_tenant_id
                ):
                    return False

            # 5. Permission check: direct permissions
            for p_item in principal.permissions:
                if isinstance(p_item, Permission):
                    if p_item.matches(permission):
                        return True
                elif isinstance(p_item, str):
                    try:
                        p_obj = Permission.from_string(p_item)
                        if p_obj.matches(permission):
                            return True
                    except (ValidationError, Exception):
                        continue

            # 6. Permission check: assigned standard roles
            for role_name in principal.roles:
                if not isinstance(role_name, str):
                    continue
                try:
                    role = StandardRoles.get_role(role_name)
                    if role.has_permission(permission):
                        return True
                except (ValidationError, Exception):
                    continue

            # Default deny
            return False

        except Exception as exc:
            logger.warning("Fail-closed denial during authorize_principal: %s", exc)
            return False

    def authorize_delegation(
        self,
        token: DelegationToken,
        resource_tenant_id: TenantId,
        capability: Permission,
        target_resource: str,
        as_of: UtcDateTime | None = None,
    ) -> bool:
        """
        Authorize delegated agent action under an approved DelegationToken.
        Enforces:
        - Token tenant strictly matches resource_tenant_id (INV-TEN-001).
        - Token is not expired as of evaluated time (INV-IAM-002).
        - Token has not been revoked in the registry (INV-IAM-002).
        - Requested capability is granted by token (INV-SEC-003).
        - Target resource matches allowed targets with safe segment boundary rules (INV-IAM-002).
        - Fails closed on any uncertainty (INV-REL-001).
        """
        try:
            # 1. Parameter and type validation
            if not isinstance(token, DelegationToken):
                return False
            if not isinstance(resource_tenant_id, TenantId):
                return False
            if not isinstance(capability, Permission):
                return False
            if not isinstance(target_resource, str) or not target_resource.strip():
                return False

            # 2. Strict tenant alignment (INV-TEN-001)
            if token.tenant_id != resource_tenant_id:
                return False

            # 3. Expiration check (INV-IAM-002)
            if token.is_expired(as_of):
                return False

            # 4. Revocation check (INV-IAM-002)
            if self._revocation_registry.is_revoked(token.delegation_id):
                return False

            # 5. Capability check (INV-SEC-003)
            if not token.allows_capability(capability):
                return False

            # 6. Target resource boundary check (INV-IAM-002)
            if not token.allows_target(target_resource):
                return False

            return True

        except Exception as exc:
            logger.warning("Fail-closed denial during authorize_delegation: %s", exc)
            return False

    def authorize_privileged(
        self,
        context: PrivilegedContext,
        permission: Permission,
        attributes: PolicyAttributes | None = None,
        as_of: UtcDateTime | None = None,
    ) -> bool:
        """
        Authorize emergency platform break-glass operation (INV-TEN-003).
        Enforces:
        - Context is canonical PrivilegedContext instance.
        - Cryptographic platform provenance signature and active time window (INV-TEN-003).
        - Autonomous agents are strictly denied privileged access (INV-ACT-003).
        - Fails closed on any invalidity, tampering, or expiration (INV-REL-001).
        """
        try:
            # 1. Parameter and type validation
            if not isinstance(context, PrivilegedContext):
                return False
            if not isinstance(permission, Permission):
                return False

            # 2. Agent exclusion: autonomous agents cannot assume PrivilegedContext (INV-ACT-003)
            principal_id_str = str(context.principal_id)
            if principal_id_str.startswith("agn_"):
                return False

            # 3. Context provenance and lifetime verification (INV-TEN-003)
            if not context.is_valid(as_of):
                return False

            # 4. Contextual attributes validation if present
            if attributes is not None and not isinstance(attributes, PolicyAttributes):
                return False

            return True

        except Exception as exc:
            logger.warning("Fail-closed denial during authorize_privileged: %s", exc)
            return False

    def assert_authorized(
        self,
        principal: Principal,
        resource_tenant_id: TenantId,
        permission: Permission,
        attributes: PolicyAttributes | None = None,
    ) -> None:
        """
        Assert that ordinary principal is authorized for action, raising AuthorizationError on denial.
        """
        if not self.authorize_principal(principal, resource_tenant_id, permission, attributes):
            principal_id = getattr(principal, "id", "unknown")
            raise AuthorizationError(
                f"Principal '{principal_id}' denied permission '{permission}' on tenant '{resource_tenant_id}'"
            )

    def assert_delegation_authorized(
        self,
        token: DelegationToken,
        resource_tenant_id: TenantId,
        capability: Permission,
        target_resource: str,
        as_of: UtcDateTime | None = None,
    ) -> None:
        """
        Assert that delegation token is authorized for action, raising AuthorizationError on denial.
        """
        if not self.authorize_delegation(token, resource_tenant_id, capability, target_resource, as_of):
            del_id = getattr(token, "delegation_id", "unknown")
            raise AuthorizationError(
                f"Delegation '{del_id}' denied capability '{capability}' on resource '{target_resource}' (tenant '{resource_tenant_id}')"
            )

    def assert_privileged_authorized(
        self,
        context: PrivilegedContext,
        permission: Permission,
        attributes: PolicyAttributes | None = None,
        as_of: UtcDateTime | None = None,
    ) -> None:
        """
        Assert that privileged context is authorized for break-glass action, raising AuthorizationError on denial.
        """
        if not self.authorize_privileged(context, permission, attributes, as_of):
            ticket = getattr(context, "ticket_id", "unknown")
            raise AuthorizationError(
                f"Privileged break-glass authorization denied for ticket '{ticket}' on permission '{permission}'"
            )
