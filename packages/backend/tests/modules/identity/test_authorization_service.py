"""
RevPilot AI — Authorization Service Unit Tests (Rail 4).
Comprehensive verification of AuthorizationService, AuthorizationPort protocol,
ordinary principal isolation, delegated token enforcement, and platform break-glass boundary.
Enforces INV-IAM-001, INV-IAM-002, INV-TEN-001, INV-TEN-003, INV-ACT-003, and INV-REL-001.
"""

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
from revpilot.modules.identity.ports.authorization import AuthorizationPort
from revpilot.shared.errors import AuthorizationError
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
def user_id() -> PrincipalId:
    return PrincipalId("usr_01j9b4c6e8f01a2b3c4d5e6f7a")


@pytest.fixture
def principal_alpha(user_id: PrincipalId, tenant_alpha: TenantId) -> Principal:
    return Principal(
        id=user_id,
        type=PrincipalType.USER,
        tenant_id=tenant_alpha,
        roles=frozenset({"analyst"}),
        permissions=frozenset({"investigation:create", "investigation:read"}),
        is_active=True,
    )


# ---------------------------------------------------------------------------
# 1. Protocol Conformance
# ---------------------------------------------------------------------------


def test_authorization_service_implements_protocol():
    """Verify AuthorizationService satisfies AuthorizationPort protocol runtime check."""
    service = AuthorizationService()
    assert isinstance(service, AuthorizationPort)


# ---------------------------------------------------------------------------
# 2. Ordinary Principal Authorization (INV-TEN-001, INV-IAM-001)
# ---------------------------------------------------------------------------


def test_authorize_principal_direct_permission_success(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
):
    """Direct explicit permission grants access within same tenant."""
    perm = Permission("investigation", "create")
    assert auth_service.authorize_principal(principal_alpha, tenant_alpha, perm) is True


def test_authorize_principal_role_permission_success(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
):
    """Permission granted via assigned standard role (analyst -> evidence:read)."""
    perm = Permission("evidence", "read")
    assert auth_service.authorize_principal(principal_alpha, tenant_alpha, perm) is True


def test_authorize_principal_missing_permission_denied(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
):
    """Deny access when principal lacks requested permission (INV-IAM-001)."""
    perm = Permission("tenant", "delete")
    assert auth_service.authorize_principal(principal_alpha, tenant_alpha, perm) is False


def test_authorize_principal_cross_tenant_denied(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_beta: TenantId,
):
    """Cross-tenant access strictly denied even if principal has permission (INV-TEN-001)."""
    perm = Permission("investigation", "create")
    assert auth_service.authorize_principal(principal_alpha, tenant_beta, perm) is False


def test_authorize_principal_wildcard_role_cross_tenant_denied(
    auth_service: AuthorizationService,
    user_id: PrincipalId,
    tenant_alpha: TenantId,
    tenant_beta: TenantId,
):
    """Even platform_admin role cannot cross tenant boundary via ordinary authorize_principal."""
    admin = Principal(
        id=user_id,
        type=PrincipalType.USER,
        tenant_id=tenant_alpha,
        roles=frozenset({"platform_admin"}),
        permissions=frozenset(),
        is_active=True,
    )
    perm = Permission("investigation", "read")
    # Same tenant passes
    assert auth_service.authorize_principal(admin, tenant_alpha, perm) is True
    # Cross tenant fails closed
    assert auth_service.authorize_principal(admin, tenant_beta, perm) is False


def test_authorize_principal_inactive_denied(
    auth_service: AuthorizationService,
    user_id: PrincipalId,
    tenant_alpha: TenantId,
):
    """Inactive principal is denied all access."""
    inactive = Principal(
        id=user_id,
        type=PrincipalType.USER,
        tenant_id=tenant_alpha,
        roles=frozenset({"analyst"}),
        permissions=frozenset({"investigation:read"}),
        is_active=False,
    )
    perm = Permission("investigation", "read")
    assert auth_service.authorize_principal(inactive, tenant_alpha, perm) is False


def test_authorize_principal_null_tenant_denied(
    auth_service: AuthorizationService,
    user_id: PrincipalId,
    tenant_alpha: TenantId,
):
    """Principal with null tenant cannot access tenant-owned resource."""
    null_tenant_principal = Principal(
        id=user_id,
        type=PrincipalType.SYSTEM,
        tenant_id=None,
        roles=frozenset({"analyst"}),
        permissions=frozenset({"investigation:read"}),
        is_active=True,
    )
    perm = Permission("investigation", "read")
    assert auth_service.authorize_principal(null_tenant_principal, tenant_alpha, perm) is False


def test_authorize_principal_attributes_alignment(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
    tenant_beta: TenantId,
):
    """PolicyAttributes tenant mismatch causes authorization denial."""
    perm = Permission("investigation", "create")
    valid_attrs = PolicyAttributes(tenant_id=tenant_alpha, resource_tenant_id=tenant_alpha)
    assert auth_service.authorize_principal(principal_alpha, tenant_alpha, perm, valid_attrs) is True

    mismatched_attrs = PolicyAttributes(tenant_id=tenant_beta)
    assert auth_service.authorize_principal(principal_alpha, tenant_alpha, perm, mismatched_attrs) is False


def test_assert_authorized_raises_error_on_denial(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_beta: TenantId,
):
    """assert_authorized raises AuthorizationError on denied authorization."""
    perm = Permission("investigation", "create")
    with pytest.raises(AuthorizationError) as exc_info:
        auth_service.assert_authorized(principal_alpha, tenant_beta, perm)
    assert "denied permission" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Delegated Token Authorization (INV-IAM-002, INV-SEC-003)
# ---------------------------------------------------------------------------


def test_authorize_delegation_success(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
):
    """Valid delegation token authorizes agent action within allowed scope."""
    token = issue_delegation(
        delegator=principal_alpha,
        tenant_id=tenant_alpha,
        task_id="task_123",
        capabilities=[Permission("investigation", "read")],
        target_resources=["/investigations/inv_01"],
        duration_seconds=300,
    )
    perm = Permission("investigation", "read")
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/investigations/inv_01"
    ) is True


def test_authorize_delegation_cross_tenant_denied(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
    tenant_beta: TenantId,
):
    """Delegation token cannot be used across tenant boundaries (INV-TEN-001)."""
    token = issue_delegation(
        delegator=principal_alpha,
        tenant_id=tenant_alpha,
        task_id="task_123",
        capabilities=[Permission("investigation", "read")],
        target_resources=["/investigations/inv_01"],
    )
    perm = Permission("investigation", "read")
    assert auth_service.authorize_delegation(
        token, tenant_beta, perm, "/investigations/inv_01"
    ) is False


def test_authorize_delegation_expired_denied(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
):
    """Expired delegation token is denied access (INV-IAM-002)."""
    now = UtcDateTime.now()
    token = issue_delegation(
        delegator=principal_alpha,
        tenant_id=tenant_alpha,
        task_id="task_123",
        capabilities=[Permission("investigation", "read")],
        target_resources=["/investigations/inv_01"],
        duration_seconds=60,
        as_of=now,
    )
    future = UtcDateTime(now.value + timedelta(seconds=120))
    perm = Permission("investigation", "read")
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/investigations/inv_01", as_of=future
    ) is False


def test_authorize_delegation_revoked_denied(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
):
    """Revoked delegation token is denied access immediately."""
    token = issue_delegation(
        delegator=principal_alpha,
        tenant_id=tenant_alpha,
        task_id="task_123",
        capabilities=[Permission("investigation", "read")],
        target_resources=["/investigations/inv_01"],
    )
    perm = Permission("investigation", "read")
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/investigations/inv_01"
    ) is True

    # Revoke token
    auth_service.revocation_registry.revoke(token.delegation_id, reason="Admin canceled")
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/investigations/inv_01"
    ) is False


def test_authorize_delegation_capability_mismatch_denied(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
):
    """Token without requested capability is denied access."""
    token = issue_delegation(
        delegator=principal_alpha,
        tenant_id=tenant_alpha,
        task_id="task_123",
        capabilities=[Permission("investigation", "read")],
        target_resources=["/investigations/inv_01"],
    )
    unauthorized_perm = Permission("investigation", "delete")
    assert auth_service.authorize_delegation(
        token, tenant_alpha, unauthorized_perm, "/investigations/inv_01"
    ) is False


def test_authorize_delegation_target_resource_boundary_denied(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
):
    """Token cannot access target resources outside its scope or without segment delimiter."""
    token = issue_delegation(
        delegator=principal_alpha,
        tenant_id=tenant_alpha,
        task_id="task_123",
        capabilities=[Permission("investigation", "read")],
        target_resources=["/investigations/inv_01"],
    )
    perm = Permission("investigation", "read")
    # Exact child resource with delimiter matches
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/investigations/inv_01/evidence"
    ) is True
    # Resource with suffix match but without delimiter strictly denied
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/investigations/inv_01_extra"
    ) is False
    # Unrelated resource denied
    assert auth_service.authorize_delegation(
        token, tenant_alpha, perm, "/investigations/inv_99"
    ) is False


def test_assert_delegation_authorized_raises_on_denial(
    auth_service: AuthorizationService,
    principal_alpha: Principal,
    tenant_alpha: TenantId,
):
    """assert_delegation_authorized raises AuthorizationError when delegation check fails."""
    token = issue_delegation(
        delegator=principal_alpha,
        tenant_id=tenant_alpha,
        task_id="task_123",
        capabilities=[Permission("investigation", "read")],
        target_resources=["/investigations/inv_01"],
    )
    with pytest.raises(AuthorizationError):
        auth_service.assert_delegation_authorized(
            token, tenant_alpha, Permission("investigation", "write"), "/investigations/inv_01"
        )


# ---------------------------------------------------------------------------
# 4. Platform Privileged Break-Glass (INV-TEN-003, AC-R04-003-04, AC-R04-003-05)
# ---------------------------------------------------------------------------


def test_authorize_privileged_valid_platform_context(
    auth_service: AuthorizationService,
):
    """Canonical PrivilegedContext with valid platform provenance passes authorization."""
    now = UtcDateTime.now()
    ctx = PrivilegedContext._issue_platform_context(
        principal_id=PrincipalId("usr_sre0000000000000000000000001"),
        ticket_id="INC-9999",
        justification="Database emergency failover",
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(seconds=1800)),
    )
    perm = Permission("*", "*")
    assert auth_service.authorize_privileged(ctx, perm) is True


def test_authorize_privileged_expired_context_denied(
    auth_service: AuthorizationService,
):
    """Expired PrivilegedContext is denied authorization."""
    now = UtcDateTime.now()
    ctx = PrivilegedContext._issue_platform_context(
        principal_id=PrincipalId("usr_sre0000000000000000000000001"),
        ticket_id="INC-9999",
        justification="Database emergency failover",
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(seconds=60)),
    )
    future = UtcDateTime(now.value + timedelta(seconds=120))
    perm = Permission("*", "*")
    assert auth_service.authorize_privileged(ctx, perm, as_of=future) is False


def test_privileged_context_forgery_prevented(user_id: PrincipalId):
    """Callers cannot self-elevate or construct PrivilegedContext with forged signatures (AC-R04-003-05)."""
    now = UtcDateTime.now()
    with pytest.raises(AuthorizationError) as exc_info:
        PrivilegedContext(
            principal_id=user_id,
            ticket_id="TICKET-1",
            justification="Self-elevation attempt",
            issued_at=now,
            expires_at=UtcDateTime(now.value + timedelta(seconds=300)),
            _provenance_signature="forged_signature_000000000000000000000000",
        )
    assert "invalid platform provenance signature" in str(exc_info.value)


def test_authorize_privileged_agent_principal_denied(
    auth_service: AuthorizationService,
):
    """Autonomous agent principal cannot assume PrivilegedContext (INV-ACT-003)."""
    # Create fake context where principal_id starts with agn_
    # Even if forged through internal method, service must reject agn_ actors
    class FakeAgentPrincipalId(PrincipalId, prefix="agn_"):
        pass

    now = UtcDateTime.now()
    agent_id = FakeAgentPrincipalId("agn_agent00000000000000000000001")
    ctx = PrivilegedContext._issue_platform_context(
        principal_id=agent_id,
        ticket_id="INC-1111",
        justification="Agent breakglass attempt",
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(seconds=300)),
    )
    assert auth_service.authorize_privileged(ctx, Permission("*", "*")) is False


def test_assert_privileged_authorized_raises_on_denial(
    auth_service: AuthorizationService,
):
    """assert_privileged_authorized raises AuthorizationError when context is invalid."""
    now = UtcDateTime.now()
    ctx = PrivilegedContext._issue_platform_context(
        principal_id=PrincipalId("usr_sre0000000000000000000000001"),
        ticket_id="INC-9999",
        justification="Database emergency failover",
        issued_at=now,
        expires_at=UtcDateTime(now.value + timedelta(seconds=60)),
    )
    future = UtcDateTime(now.value + timedelta(seconds=120))
    with pytest.raises(AuthorizationError):
        auth_service.assert_privileged_authorized(
            ctx, Permission("*", "*"), as_of=future
        )


# ---------------------------------------------------------------------------
# 5. Fail-Closed Resilience (INV-REL-001)
# ---------------------------------------------------------------------------


def test_fail_closed_on_invalid_types(auth_service: AuthorizationService):
    """Service returns False on invalid argument types without unhandled crash."""
    assert auth_service.authorize_principal(None, None, None) is False  # type: ignore
    assert auth_service.authorize_delegation(None, None, None, None) is False  # type: ignore
    assert auth_service.authorize_privileged(None, None) is False  # type: ignore
