"""
RevPilot AI — Authorization & Delegation Negative Test Matrix (Rail 4 Exit Gate).
Exhaustive machine verification of fail-closed authorization, cross-tenant denial,
delegation boundaries, agent approval prohibitions, and break-glass misuse.
Enforces INV-IAM-001, INV-IAM-002, INV-TEN-001, INV-TEN-003, INV-ACT-003, and INV-REL-001.
"""

from __future__ import annotations
from datetime import timedelta
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
from revpilot.modules.identity.domain.roles import StandardRoles
from revpilot.shared.errors import (
    AuthorizationError,
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.identifiers import PrincipalId, TenantId
from revpilot.shared.temporal import UtcDateTime


@pytest.fixture
def auth_service() -> AuthorizationService:
    return AuthorizationService()


@pytest.fixture
def tenant_alpha() -> TenantId:
    return TenantId("tnt_alpha000000000000000000000001")


@pytest.fixture
def tenant_beta() -> TenantId:
    return TenantId("tnt_beta0000000000000000000000002")


@pytest.fixture
def analyst_principal(tenant_alpha: TenantId) -> Principal:
    """Human analyst possessing scoped read permissions."""
    return Principal(
        id=PrincipalId("usr_analyst00000000000000000001"),
        type=PrincipalType.USER,
        tenant_id=tenant_alpha,
        roles=frozenset({"analyst"}),
        permissions=frozenset({"investigation:read", "evidence:read"}),
        is_active=True,
    )


@pytest.fixture
def operator_principal(tenant_alpha: TenantId) -> Principal:
    """Human operator possessing tool invocation permissions."""
    return Principal(
        id=PrincipalId("usr_operator00000000000000000001"),
        type=PrincipalType.USER,
        tenant_id=tenant_alpha,
        roles=frozenset({"operator"}),
        permissions=frozenset({"tool:invoke", "investigation:create", "investigation:read"}),
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Section 1: INV-IAM-001 Deny-by-Default and Missing Permissions (AC-R04-004-02)
# ---------------------------------------------------------------------------


def test_deny_by_default_missing_permission(
    auth_service: AuthorizationService,
    analyst_principal: Principal,
    tenant_alpha: TenantId,
):
    """Principal lacking explicit permission or role permission is denied access (INV-IAM-001)."""
    perm = Permission("billing", "modify")
    assert auth_service.authorize_principal(analyst_principal, tenant_alpha, perm) is False

    with pytest.raises(AuthorizationError):
        auth_service.assert_authorized(analyst_principal, tenant_alpha, perm)


def test_deny_by_default_empty_permissions_principal(
    auth_service: AuthorizationService,
    tenant_alpha: TenantId,
):
    """Principal with empty roles and empty permissions is denied all actions."""
    empty_principal = Principal(
        id=PrincipalId("usr_empty0000000000000000000001"),
        type=PrincipalType.USER,
        tenant_id=tenant_alpha,
        roles=frozenset(),
        permissions=frozenset(),
        is_active=True,
    )
    perm = Permission("investigation", "read")
    assert auth_service.authorize_principal(empty_principal, tenant_alpha, perm) is False


def test_deny_by_default_inactive_principal(
    auth_service: AuthorizationService,
    tenant_alpha: TenantId,
):
    """Deactivated principal is denied authorization regardless of held roles."""
    inactive_principal = Principal(
        id=PrincipalId("usr_inactive0000000000000000001"),
        type=PrincipalType.USER,
        tenant_id=tenant_alpha,
        roles=frozenset({"tenant_admin"}),
        permissions=frozenset({"tenant:manage"}),
        is_active=False,
    )
    perm = Permission("tenant", "manage")
    assert auth_service.authorize_principal(inactive_principal, tenant_alpha, perm) is False


# ---------------------------------------------------------------------------
# Section 2: INV-TEN-001 Cross-Tenant Isolation (AC-R04-004-01)
# ---------------------------------------------------------------------------


def test_cross_tenant_access_denied_principal(
    auth_service: AuthorizationService,
    operator_principal: Principal,
    tenant_beta: TenantId,
):
    """Principal of Tenant Alpha attempting to access Tenant Beta is strictly denied."""
    perm = Permission("tool", "invoke")
    assert auth_service.authorize_principal(operator_principal, tenant_beta, perm) is False

    with pytest.raises(AuthorizationError):
        auth_service.assert_authorized(operator_principal, tenant_beta, perm)


def test_cross_tenant_access_denied_even_for_admin(
    auth_service: AuthorizationService,
    tenant_alpha: TenantId,
    tenant_beta: TenantId,
):
    """Tenant admin cannot cross tenant boundary via ordinary authorization."""
    admin_alpha = Principal(
        id=PrincipalId("usr_admin000000000000000000001"),
        type=PrincipalType.USER,
        tenant_id=tenant_alpha,
        roles=frozenset({"tenant_admin"}),
        permissions=frozenset({"tenant:manage"}),
        is_active=True,
    )
    perm = Permission("tenant", "manage")
    assert auth_service.authorize_principal(admin_alpha, tenant_beta, perm) is False


def test_cross_tenant_delegation_token_denied(
    auth_service: AuthorizationService,
    operator_principal: Principal,
    tenant_alpha: TenantId,
    tenant_beta: TenantId,
):
    """Delegation token issued for Tenant Alpha cannot be used against Tenant Beta."""
    token = issue_delegation(
        delegator=operator_principal,
        tenant_id=tenant_alpha,
        task_id="task_negative_01",
        capabilities=[Permission("tool", "invoke")],
        target_resources=["/tools/sql_query"],
    )
    perm = Permission("tool", "invoke")
    assert auth_service.authorize_delegation(
        token, tenant_beta, perm, "/tools/sql_query"
    ) is False

    with pytest.raises(AuthorizationError):
        auth_service.assert_delegation_authorized(
            token, tenant_beta, perm, "/tools/sql_query"
        )


# ---------------------------------------------------------------------------
# Section 3: INV-IAM-002 Privilege Escalation Prevention (AC-R04-004-03)
# ---------------------------------------------------------------------------


def test_privilege_escalation_delegation_exceeding_delegator_denied(
    analyst_principal: Principal,
    tenant_alpha: TenantId,
):
    """Delegator with ANALYST permissions cannot delegate OPERATOR capabilities."""
    with pytest.raises(AuthorizationError) as exc_info:
        issue_delegation(
            delegator=analyst_principal,
            tenant_id=tenant_alpha,
            task_id="task_escalation_01",
            capabilities=[Permission("tool", "invoke")],  # analyst does not have tool:invoke
            target_resources=["/tools/run"],
        )
    assert "exceeds delegator permissions" in str(exc_info.value)


def test_privilege_escalation_wildcard_delegation_denied(
    operator_principal: Principal,
    tenant_alpha: TenantId,
):
    """Delegator possessing scoped permissions cannot delegate broader resource wildcard capabilities."""
    with pytest.raises(AuthorizationError) as exc_info:
        issue_delegation(
            delegator=operator_principal,
            tenant_id=tenant_alpha,
            task_id="task_escalation_02",
            capabilities=[Permission("investigation", "*")],
            target_resources=["/investigations/*"],
        )
    assert "exceeds delegator permissions" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Section 4: INV-ACT-003 Agent Approval Prohibition (AC-R04-004-04)
# ---------------------------------------------------------------------------


def test_agent_approval_delegation_grant_denied(
    operator_principal: Principal,
    tenant_alpha: TenantId,
):
    """Delegated agents cannot receive approval:grant authority under any circumstances."""
    with pytest.raises(AuthorizationError) as exc_info:
        issue_delegation(
            delegator=operator_principal,
            tenant_id=tenant_alpha,
            task_id="task_approval_01",
            capabilities=[Permission("approval", "grant")],
            target_resources=["/approvals/*"],
        )
    assert "approval authority" in str(exc_info.value)


def test_agent_approval_wildcard_denied(
    operator_principal: Principal,
    tenant_alpha: TenantId,
):
    """Delegated agents cannot receive approval:* authority."""
    with pytest.raises(AuthorizationError) as exc_info:
        issue_delegation(
            delegator=operator_principal,
            tenant_id=tenant_alpha,
            task_id="task_approval_02",
            capabilities=[Permission("approval", "*")],
            target_resources=["/approvals/*"],
        )
    assert "approval authority" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Section 5: INV-IAM-002 Delegation Expiry & Revocation (AC-R04-004-05)
# ---------------------------------------------------------------------------


def test_expired_delegation_token_rejected(
    auth_service: AuthorizationService,
    operator_principal: Principal,
    tenant_alpha: TenantId,
):
    """Expired delegation token is denied at authorization time."""
    start_time = UtcDateTime.now()
    token = issue_delegation(
        delegator=operator_principal,
        tenant_id=tenant_alpha,
        task_id="task_expire_01",
        capabilities=[Permission("tool", "invoke")],
        target_resources=["/tools/sql_query"],
        duration_seconds=60,
        as_of=start_time,
    )
    future_time = UtcDateTime(start_time.value + timedelta(seconds=61))
    perm = Permission("tool", "invoke")

    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/tools/sql_query", as_of=future_time
    ) is False


def test_revoked_delegation_token_rejected(
    auth_service: AuthorizationService,
    operator_principal: Principal,
    tenant_alpha: TenantId,
):
    """Revoked delegation token is denied at authorization check."""
    token = issue_delegation(
        delegator=operator_principal,
        tenant_id=tenant_alpha,
        task_id="task_revoke_01",
        capabilities=[Permission("tool", "invoke")],
        target_resources=["/tools/sql_query"],
    )
    perm = Permission("tool", "invoke")
    # Initially active
    assert auth_service.authorize_delegation(token, tenant_alpha, perm, "/tools/sql_query") is True

    # Revoke in registry
    auth_service.revocation_registry.revoke(token.delegation_id, reason="Security compromise")
    assert auth_service.authorize_delegation(token, tenant_alpha, perm, "/tools/sql_query") is False


# ---------------------------------------------------------------------------
# Section 6: INV-SEC-003 Scope and Target Boundaries (AC-R04-004-06)
# ---------------------------------------------------------------------------


def test_out_of_scope_target_resource_denied(
    auth_service: AuthorizationService,
    operator_principal: Principal,
    tenant_alpha: TenantId,
):
    """Delegation token attempting out-of-scope target resource is denied."""
    token = issue_delegation(
        delegator=operator_principal,
        tenant_id=tenant_alpha,
        task_id="task_target_01",
        capabilities=[Permission("tool", "invoke")],
        target_resources=["/tools/read_metrics"],
    )
    perm = Permission("tool", "invoke")
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/tools/write_database"
    ) is False


def test_target_boundary_delimiter_traversal_attack_denied(
    auth_service: AuthorizationService,
    operator_principal: Principal,
    tenant_alpha: TenantId,
):
    """
    Prevent prefix collision attack:
    Token granted '/tenant/alpha' MUST NOT match '/tenant/alpha_secret' without delimiter.
    """
    token = issue_delegation(
        delegator=operator_principal,
        tenant_id=tenant_alpha,
        task_id="task_target_02",
        capabilities=[Permission("tool", "invoke")],
        target_resources=["/tenant/alpha"],
    )
    perm = Permission("tool", "invoke")

    # Delimited child matches
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/tenant/alpha/resource"
    ) is True
    # Non-delimited suffix extension is denied
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/tenant/alpha_secret"
    ) is False


# ---------------------------------------------------------------------------
# Section 7: Sub-Delegation Prohibition (AC-R04-004-04)
# ---------------------------------------------------------------------------


def test_agent_sub_delegation_prohibited(tenant_alpha: TenantId):
    """Agent identity attempting to act as delegator is strictly rejected."""
    agent_principal = Principal(
        id=PrincipalId("usr_agent0000000000000000000001"),
        type=PrincipalType.AGENT,
        tenant_id=tenant_alpha,
        roles=frozenset({"agent_delegate"}),
        permissions=frozenset({"tool:invoke"}),
        is_active=True,
    )
    with pytest.raises(AuthorizationError) as exc_info:
        issue_delegation(
            delegator=agent_principal,
            tenant_id=tenant_alpha,
            task_id="task_subdel_01",
            capabilities=[Permission("tool", "invoke")],
            target_resources=["/tools/sql_query"],
        )
    assert "cannot sub-delegate" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Section 8: INV-TEN-003 Break-Glass Misuse Prevention (AC-R04-004-07)
# ---------------------------------------------------------------------------


def test_agent_cannot_assume_break_glass_privileged_context(
    auth_service: AuthorizationService,
):
    """Autonomous agent principal cannot be authorized under break-glass PrivilegedContext."""
    class FakeAgentId(PrincipalId, prefix="agn_"):
        pass

    now = UtcDateTime.now()
    agent_id = FakeAgentId("agn_rogueagent0000000000000001")
    ctx = PrivilegedContext._issue_platform_context(
        principal_id=agent_id,
        ticket_id="INC-999",
        justification="Agent escalation attempt",
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(seconds=300)),
    )
    assert auth_service.authorize_privileged(ctx, Permission("*", "*")) is False


def test_tampered_privileged_context_denied():
    """PrivilegedContext with tampered signature raises AuthorizationError on construction."""
    now = UtcDateTime.now()
    with pytest.raises(AuthorizationError):
        PrivilegedContext(
            principal_id=PrincipalId("usr_sre0000000000000000000000001"),
            ticket_id="INC-999",
            justification="Tampered context",
            issued_at=now,
            expires_at=UtcDateTime(now.value + timedelta(seconds=300)),
            _provenance_signature="bad_signature_value_1234567890abcdef",
        )


def test_expired_privileged_context_denied(auth_service: AuthorizationService):
    """Expired PrivilegedContext is denied authorization."""
    now = UtcDateTime.now()
    ctx = PrivilegedContext._issue_platform_context(
        principal_id=PrincipalId("usr_sre0000000000000000000000001"),
        ticket_id="INC-999",
        justification="Expired test",
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(seconds=60)),
    )
    future = UtcDateTime(now.value + timedelta(seconds=120))
    assert auth_service.authorize_privileged(ctx, Permission("*", "*"), as_of=future) is False


# ---------------------------------------------------------------------------
# Section 9: INV-REL-001 Policy Uncertainty and Fail-Closed (AC-R04-004-08)
# ---------------------------------------------------------------------------


def test_policy_uncertainty_fails_closed(auth_service: AuthorizationService):
    """Invalid types or missing parameters fail closed by returning False."""
    assert auth_service.authorize_principal(None, None, None) is False  # type: ignore
    assert auth_service.authorize_delegation(None, None, None, None) is False  # type: ignore
    assert auth_service.authorize_privileged(None, None) is False  # type: ignore
