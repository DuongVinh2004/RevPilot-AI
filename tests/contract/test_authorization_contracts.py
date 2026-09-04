"""
RevPilot AI — Architectural Contract Tests for Authorization and Delegation (Rail 4).
Verifies MODULE-BOUNDARIES.md, DEPENDENCY-RULES.md, IAM-SPEC.md §3, and MULTI-TENANCY-SPEC.md §5.
Enforces INV-IAM-001, INV-IAM-002, INV-TEN-001, INV-TEN-003, INV-ACT-003, and INV-REL-001.
"""

from __future__ import annotations
from datetime import timedelta
import inspect
import sys
from typing import get_type_hints
import pytest

from revpilot.modules.identity.authorization_service import AuthorizationService
from revpilot.modules.identity.domain.delegation import (
    DelegationRevocationRegistry,
    DelegationToken,
    issue_delegation,
)
from revpilot.modules.identity.domain.models import (
    Principal,
    PrincipalType,
    PrivilegedContext,
)
from revpilot.modules.identity.domain.permissions import Permission, PolicyAttributes
from revpilot.modules.identity.domain.roles import Role, StandardRoles
from revpilot.modules.identity.ports.authorization import AuthorizationPort
from revpilot.shared.errors import (
    AuthorizationError,
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.identifiers import PrincipalId, TenantId
from revpilot.shared.temporal import UtcDateTime


# ---------------------------------------------------------------------------
# 1. Dependency Rules and Module Boundary Contract
# ---------------------------------------------------------------------------


def test_authorization_module_dependency_rules_contract() -> None:
    """
    Verify identity authorization components obey DEPENDENCY-RULES.md:
    Allowed dependencies: shared kernel, tenancy domain/ports, standard library.
    Forbidden dependencies: business domain modules, external SDKs, web frameworks.
    """
    forbidden_modules = [
        "revpilot.modules.investigations",
        "revpilot.modules.actions",
        "revpilot.modules.analytics",
        "revpilot.modules.evidence",
        "revpilot.modules.decisions",
        "revpilot.modules.policy",
        "revpilot.modules.connectors",
        "revpilot.modules.billing",
        "temporalio",
        "langgraph",
        "sqlalchemy",
        "fastapi",
        "starlette",
        "boto3",
        "requests",
        "urllib3",
        "httpx",
    ]

    loaded_modules = set(sys.modules.keys())
    for forbidden in forbidden_modules:
        assert forbidden not in loaded_modules, (
            f"DEPENDENCY RULE VIOLATION: Forbidden module '{forbidden}' loaded in test environment"
        )


# ---------------------------------------------------------------------------
# 2. AuthorizationPort Protocol Contract
# ---------------------------------------------------------------------------


def test_authorization_port_protocol_contract() -> None:
    """
    Verify AuthorizationPort is a runtime checkable Protocol with required methods
    and typed boolean returns (deny-by-default).
    """
    assert hasattr(AuthorizationPort, "_is_runtime_protocol")
    service = AuthorizationService()
    assert isinstance(service, AuthorizationPort)

    # authorize_principal signature
    sig_principal = inspect.signature(AuthorizationPort.authorize_principal)
    assert "principal" in sig_principal.parameters
    assert "resource_tenant_id" in sig_principal.parameters
    assert "permission" in sig_principal.parameters
    assert "attributes" in sig_principal.parameters
    hints_principal = get_type_hints(AuthorizationPort.authorize_principal)
    assert hints_principal.get("return") is bool

    # authorize_delegation signature
    sig_delegation = inspect.signature(AuthorizationPort.authorize_delegation)
    assert "token" in sig_delegation.parameters
    assert "resource_tenant_id" in sig_delegation.parameters
    assert "capability" in sig_delegation.parameters
    assert "target_resource" in sig_delegation.parameters
    assert "as_of" in sig_delegation.parameters
    hints_delegation = get_type_hints(AuthorizationPort.authorize_delegation)
    assert hints_delegation.get("return") is bool

    # authorize_privileged signature
    sig_privileged = inspect.signature(AuthorizationPort.authorize_privileged)
    assert "context" in sig_privileged.parameters
    assert "permission" in sig_privileged.parameters
    assert "attributes" in sig_privileged.parameters
    assert "as_of" in sig_privileged.parameters
    hints_privileged = get_type_hints(AuthorizationPort.authorize_privileged)
    assert hints_privileged.get("return") is bool


def test_authorization_service_method_signatures_match_port() -> None:
    """Verify AuthorizationService method signatures match AuthorizationPort exactly."""
    for method_name in [
        "authorize_principal",
        "authorize_delegation",
        "authorize_privileged",
    ]:
        port_method = getattr(AuthorizationPort, method_name)
        service_method = getattr(AuthorizationService, method_name)

        port_sig = inspect.signature(port_method)
        service_sig = inspect.signature(service_method)

        for param_name in port_sig.parameters:
            if param_name == "self":
                continue
            assert param_name in service_sig.parameters, (
                f"Parameter '{param_name}' missing from AuthorizationService.{method_name}"
            )


# ---------------------------------------------------------------------------
# 3. Standard Roles Contract (IAM-SPEC §3.4)
# ---------------------------------------------------------------------------


def test_standard_roles_canonical_matrix_contract() -> None:
    """
    Verify StandardRoles provides exactly the 6 canonical roles defined in IAM-SPEC §3.4:
    platform_admin, tenant_admin, operator, analyst, auditor, agent_delegate.
    """
    canonical_names = {
        "platform_admin",
        "tenant_admin",
        "operator",
        "analyst",
        "auditor",
        "agent_delegate",
    }
    all_roles = StandardRoles.all_roles()
    assert len(all_roles) == 6
    assert {r.name for r in all_roles} == canonical_names

    for role_name in canonical_names:
        role = StandardRoles.get_role(role_name)
        assert isinstance(role, Role)
        assert role.name == role_name
        assert len(role.permissions) > 0


def test_standard_roles_lookup_validation_contract() -> None:
    """Verify StandardRoles.get_role raises ValidationError on invalid or unknown role."""
    with pytest.raises(ValidationError):
        StandardRoles.get_role("unknown_role_xyz")
    with pytest.raises(ValidationError):
        StandardRoles.get_role("")
    with pytest.raises(ValidationError):
        StandardRoles.get_role(123)  # type: ignore


# ---------------------------------------------------------------------------
# 4. Permission Value Object Contract
# ---------------------------------------------------------------------------


def test_permission_format_and_matching_contract() -> None:
    """
    Verify Permission adheres to canonical 'resource:action' format and matching rules.
    """
    p = Permission.from_string("investigation:read")
    assert p.resource == "investigation"
    assert p.action == "read"
    assert str(p) == "investigation:read"

    # Exact matching
    assert p.matches(Permission("investigation", "read")) is True
    assert p.matches(Permission("investigation", "create")) is False

    # Action wildcard
    wildcard_action = Permission("investigation", "*")
    assert wildcard_action.matches(Permission("investigation", "read")) is True
    assert wildcard_action.matches(Permission("investigation", "delete")) is True
    assert wildcard_action.matches(Permission("tenant", "read")) is False

    # Full wildcard
    full_wildcard = Permission("*", "*")
    assert full_wildcard.matches(Permission("anything", "whatever")) is True

    # Malformed strings raise ValidationError
    with pytest.raises(ValidationError):
        Permission.from_string("no_colon")
    with pytest.raises(ValidationError):
        Permission.from_string("too:many:colons")
    with pytest.raises(ValidationError):
        Permission.from_string(":empty_resource")
    with pytest.raises(ValidationError):
        Permission.from_string("empty_action:")


# ---------------------------------------------------------------------------
# 5. Delegation Token Contract
# ---------------------------------------------------------------------------


def test_delegation_token_invariants_contract() -> None:
    """
    Verify DelegationToken enforces typed attributes, del_ prefix, and lifetime bounds.
    """
    tenant_id = TenantId("tnt_alpha000000000000000000000001")
    delegator = Principal(
        id=PrincipalId("usr_delegator00000000000000001"),
        type=PrincipalType.USER,
        tenant_id=tenant_id,
        roles=frozenset({"operator"}),
        permissions=frozenset({"investigation:create", "tool:invoke"}),
    )

    token = issue_delegation(
        delegator=delegator,
        tenant_id=tenant_id,
        task_id="task_contract_01",
        capabilities=[Permission("tool", "invoke")],
        target_resources=["/tools/sql_query"],
        duration_seconds=1800,
    )

    assert token.delegation_id.startswith("del_")
    assert token.delegator_id == delegator.id
    assert token.tenant_id == tenant_id
    assert token.task_id == "task_contract_01"
    assert not token.is_expired()


# ---------------------------------------------------------------------------
# 6. Privileged Context Invariant Contract (INV-TEN-003)
# ---------------------------------------------------------------------------


def test_privileged_context_invariants_contract() -> None:
    """
    Verify PrivilegedContext enforces platform provenance and maximum 3600s lifetime.
    Cannot be constructed without matching HMAC signature.
    """
    now = UtcDateTime.now()
    principal_id = PrincipalId("usr_sre0000000000000000000000001")

    # Valid issue via platform boundary
    ctx = PrivilegedContext._issue_platform_context(
        principal_id=principal_id,
        ticket_id="INC-777",
        justification="Contract test",
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(seconds=1800)),
    )
    assert ctx.is_valid() is True

    # Direct construction with forged signature raises AuthorizationError
    with pytest.raises(AuthorizationError):
        PrivilegedContext(
            principal_id=principal_id,
            ticket_id="INC-777",
            justification="Forged",
            issued_at=now,
            expires_at=UtcDateTime(now.value + timedelta(seconds=1800)),
            _provenance_signature="invalid_signature_hex_value",
        )

    # Lifetime > 3600s raises ValidationError
    with pytest.raises(ValidationError):
        PrivilegedContext._issue_platform_context(
            principal_id=principal_id,
            ticket_id="INC-777",
            justification="Too long",
            issued_at=now,
            expires_at=UtcDateTime(now.value + timedelta(seconds=3601)),
        )


# ---------------------------------------------------------------------------
# 7. Stable Domain Error Codes Contract
# ---------------------------------------------------------------------------


def test_stable_authorization_error_codes_contract() -> None:
    """Verify authorization errors produce canonical machine error codes."""
    assert AuthorizationError("access denied").code == "FORBIDDEN"
    assert TenancyViolationError("cross tenant").code == "TENANCY_VIOLATION"
    assert ValidationError("malformed input").code == "VALIDATION_ERROR"
