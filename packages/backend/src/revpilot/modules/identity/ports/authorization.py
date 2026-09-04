"""
RevPilot AI — Inbound Authorization Port Protocol (Rail 4).
Defines the boundary contract for principal authorization, delegated token evaluation,
and cryptographic platform privileged operations.
Enforces INV-IAM-001, INV-TEN-001, INV-TEN-003, and INV-REL-001.
"""

from __future__ import annotations
from typing import Protocol, runtime_checkable

from revpilot.modules.identity.domain.delegation import DelegationToken
from revpilot.modules.identity.domain.models import Principal, PrivilegedContext
from revpilot.modules.identity.domain.permissions import Permission, PolicyAttributes
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


@runtime_checkable
class AuthorizationPort(Protocol):
    """
    Inbound port protocol for authorization and delegation checking.
    Enforces deny-by-default and strict tenant isolation.
    """

    def authorize_principal(
        self,
        principal: Principal,
        resource_tenant_id: TenantId,
        permission: Permission,
        attributes: PolicyAttributes | None = None,
    ) -> bool:
        """
        Authorize ordinary principal action against tenant resource.
        Strictly enforces principal.tenant_id == resource_tenant_id (INV-TEN-001).
        Ordinary principals cannot bypass tenant boundary.
        """
        ...

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
        Enforces tenant alignment, expiry, revocation, capability match, and
        safe segment boundary target matching (INV-IAM-002, INV-SEC-003).
        """
        ...

    def authorize_privileged(
        self,
        context: PrivilegedContext,
        permission: Permission,
        attributes: PolicyAttributes | None = None,
        as_of: UtcDateTime | None = None,
    ) -> bool:
        """
        Authorize emergency platform break-glass operation (INV-TEN-003).
        Requires canonical PrivilegedContext with verified cryptographic provenance signature.
        Denies autonomous agents and expired or forged contexts.
        """
        ...
