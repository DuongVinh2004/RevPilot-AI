"""
RevPilot AI — Identity Service and In-Memory Auth Adapter Tests (Rail 3)
Verifies AC-R03-003-01 through AC-R03-003-07.
Tests fail-closed authentication pipeline, verified boundaries, session lifecycle,
and tenant active state enforcement.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
import pytest

from revpilot.modules.identity.adapters.in_memory_auth_adapter import InMemoryAuthAdapter
from revpilot.modules.identity.domain.models import (
    AuthTokenClaims,
    Principal,
    PrincipalType,
    VerifiedClaimsToken,
)
from revpilot.modules.identity.domain.token_policy import (
    SessionPolicy,
    TokenValidationPolicy,
    VerifiedSessionEvidence,
)
from revpilot.modules.identity.ports.authentication import AuthenticationPort
from revpilot.modules.identity.service import IdentityService
from revpilot.modules.tenancy.domain.models import (
    Tenant,
    TenantStatus,
    SubscriptionTier,
    Entitlement,
)
from revpilot.modules.tenancy.ports.policy import TenantContextPolicy
from revpilot.modules.tenancy.ports.repository import TenantQueryPort
from revpilot.shared.errors import (
    AuthenticationError,
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.identifiers import (
    OrganizationId,
    PrincipalId,
    TenantId,
)
from revpilot.shared.temporal import UtcDateTime


class MockTenantQueryPort(TenantQueryPort):
    """Simple in-memory query port for testing tenant checks."""

    def __init__(self, tenants: dict[TenantId, Tenant] | None = None) -> None:
        self._tenants: dict[TenantId, Tenant] = tenants or {}

    def get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def get_by_organization(self, organization_id: OrganizationId) -> list[Tenant]:
        return [t for t in self._tenants.values() if t.organization_id == organization_id]

    def get_organization_by_id(self, organization_id: OrganizationId):
        return None

    def exists(self, tenant_id: TenantId) -> bool:
        return tenant_id in self._tenants


def _make_sample_tenant(
    tenant_id: TenantId,
    status: TenantStatus = TenantStatus.ACTIVE,
) -> Tenant:
    now = UtcDateTime.now()
    return Tenant(
        id=tenant_id,
        organization_id=OrganizationId("org_sample_corp"),
        name="Sample Corp",
        status=status,
        tier=SubscriptionTier.SHARED,
        entitlement=Entitlement(tier=SubscriptionTier.SHARED),
        created_at=now,
        updated_at=now,
    )


# --- AC-R03-003-01: Protocol conformance ---

def test_in_memory_auth_adapter_protocol_conformance() -> None:
    """AC-R03-003-01: InMemoryAuthAdapter implements all AuthenticationPort methods."""
    adapter = InMemoryAuthAdapter()
    assert isinstance(adapter, AuthenticationPort)


# --- AC-R03-003-02: verify_token returns VerifiedClaimsToken, rejects invalid tokens ---

def test_in_memory_adapter_verify_token_returns_verified_claims_token() -> None:
    """AC-R03-003-02: verify_token returns strictly VerifiedClaimsToken, never Principal."""
    adapter = InMemoryAuthAdapter()
    token_str = "header.payload.signature"
    vt, se = adapter.issue_test_token(token_str)

    res = adapter.verify_token(token_str)
    assert isinstance(res, VerifiedClaimsToken)
    assert not isinstance(res, Principal)
    assert res.claims.sub == "usr_test_user"


def test_in_memory_adapter_verify_token_rejects_unregistered_token() -> None:
    """AC-R03-003-02: Unknown token raises AuthenticationError."""
    adapter = InMemoryAuthAdapter()
    with pytest.raises(AuthenticationError, match="Invalid token signature or token unknown"):
        adapter.verify_token("unknown.token.string")


def test_in_memory_adapter_verify_token_rejects_empty_or_whitespace() -> None:
    adapter = InMemoryAuthAdapter()
    with pytest.raises(AuthenticationError, match="Token must be a non-empty string"):
        adapter.verify_token("")
    with pytest.raises(AuthenticationError, match="Token must be a non-empty string"):
        adapter.verify_token("   ")


def test_in_memory_adapter_verify_token_enforces_issuer_and_audience() -> None:
    """AC-R03-003-02: Mismatched issuer or audience raises AuthenticationError."""
    adapter = InMemoryAuthAdapter()
    token_str = "sample.token.jwt"
    adapter.issue_test_token(
        token_str,
        iss="revpilot-idp",
        aud="revpilot-api",
    )

    with pytest.raises(AuthenticationError, match="Issuer mismatch"):
        adapter.verify_token(token_str, expected_issuer="wrong-idp")

    with pytest.raises(AuthenticationError, match="Audience mismatch"):
        adapter.verify_token(token_str, expected_audience="wrong-api")


# --- AC-R03-003-03: Revocation behavior ---

def test_in_memory_adapter_revoke_session_fails_subsequent_verification() -> None:
    """AC-R03-003-03: Revoking session fails subsequent verification and evidence retrieval."""
    adapter = InMemoryAuthAdapter()
    token_str = "tok.123"
    vt, se = adapter.issue_test_token(token_str, session_id="sess_alpha")

    # Before revocation: succeeds
    assert adapter.verify_token(token_str).session_id == "sess_alpha"
    ev = adapter.get_session_evidence("sess_alpha")
    assert ev.is_revoked is False

    # Revoke session
    adapter.revoke_session("sess_alpha")

    # Subsequent verify_token raises AuthenticationError
    with pytest.raises(AuthenticationError, match="Token or session has been revoked"):
        adapter.verify_token(token_str)

    # Subsequent get_session_evidence returns revoked evidence
    ev_revoked = adapter.get_session_evidence("sess_alpha")
    assert ev_revoked.is_revoked is True


def test_in_memory_adapter_get_session_evidence_unknown_session() -> None:
    adapter = InMemoryAuthAdapter()
    with pytest.raises(AuthenticationError, match="not found or unverified"):
        adapter.get_session_evidence("unknown_sess")


# --- AC-R03-003-04: IdentityService pipeline ---

def test_identity_service_authenticate_token_happy_path() -> None:
    """AC-R03-003-04: Full pipeline validates and returns trusted Principal."""
    adapter = InMemoryAuthAdapter()
    tenant_id = TenantId("tnt_acme_corp")
    tenant = _make_sample_tenant(tenant_id, TenantStatus.ACTIVE)
    query_port = MockTenantQueryPort({tenant_id: tenant})

    service = IdentityService(
        auth_port=adapter,
        tenant_query_port=query_port,
        tenancy_policy=TenantContextPolicy,
    )

    token_str = "valid.auth.token"
    adapter.issue_test_token(
        token_str,
        sub="usr_alice",
        tenant_id=str(tenant_id),
        roles=["analyst", "viewer"],
        permissions=["read:reports"],
    )

    principal = service.authenticate_token(token_str)
    assert isinstance(principal, Principal)
    assert principal.id == PrincipalId("usr_alice")
    assert principal.type == PrincipalType.USER
    assert principal.tenant_id == tenant_id
    assert principal.has_role("analyst")
    assert principal.has_permission("read:reports")

    # PrincipalContext structurally enforces is_system=False
    ctx = principal.to_context()
    assert ctx.is_system is False
    assert ctx.tenant_id == tenant_id


def test_identity_service_rejects_empty_or_non_string_token() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    with pytest.raises(ValidationError, match="token must be a str"):
        service.authenticate_token(12345)  # type: ignore

    with pytest.raises(ValidationError, match="token cannot be empty or whitespace-only"):
        service.authenticate_token("")

    with pytest.raises(ValidationError, match="token cannot be empty or whitespace-only"):
        service.authenticate_token("   ")


def test_identity_service_rejects_expired_token() -> None:
    """AC-R03-003-04: Expired claims fail closed."""
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    token_str = "expired.jwt.token"
    past = UtcDateTime(datetime.now(timezone.utc) - timedelta(seconds=300))
    past_iat = UtcDateTime(datetime.now(timezone.utc) - timedelta(seconds=3600))
    adapter.issue_test_token(
        token_str,
        exp=past,
        iat=past_iat,
    )

    with pytest.raises(AuthenticationError, match="Token has expired"):
        service.authenticate_token(token_str)


def test_identity_service_rejects_not_yet_active_token() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    token_str = "future.jwt.token"
    future = UtcDateTime(datetime.now(timezone.utc) + timedelta(seconds=300))
    adapter.issue_test_token(
        token_str,
        nbf=future,
    )

    with pytest.raises(AuthenticationError, match="Token not yet active"):
        service.authenticate_token(token_str)


def test_identity_service_rejects_revoked_session() -> None:
    """AC-R03-003-04: Revoked session causes authenticate_token to fail closed."""
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    token_str = "sess.revoked.token"
    adapter.issue_test_token(
        token_str,
        session_id="sess_revoked_test",
    )
    service.revoke_session("sess_revoked_test")

    with pytest.raises(AuthenticationError, match="Token or session has been revoked"):
        service.authenticate_token(token_str)


# --- AC-R03-003-05: Tenancy validation and fail-closed enforcement ---

def test_identity_service_fails_on_missing_tenant_in_repository() -> None:
    """AC-R03-003-05: Non-existent tenant fails closed with TenancyViolationError."""
    adapter = InMemoryAuthAdapter()
    query_port = MockTenantQueryPort({})  # empty repo
    service = IdentityService(
        auth_port=adapter,
        tenant_query_port=query_port,
        tenancy_policy=TenantContextPolicy,
    )

    token_str = "missing.tenant.token"
    adapter.issue_test_token(
        token_str,
        tenant_id="tnt_nonexistent",
    )

    with pytest.raises(TenancyViolationError, match="does not exist"):
        service.authenticate_token(token_str)


def test_identity_service_fails_on_suspended_tenant() -> None:
    """AC-R03-003-05: Suspended tenant fails closed with TenancyViolationError."""
    adapter = InMemoryAuthAdapter()
    tenant_id = TenantId("tnt_suspended_corp")
    tenant = _make_sample_tenant(tenant_id, TenantStatus.SUSPENDED)
    query_port = MockTenantQueryPort({tenant_id: tenant})

    service = IdentityService(
        auth_port=adapter,
        tenant_query_port=query_port,
        tenancy_policy=TenantContextPolicy,
    )

    token_str = "suspended.tenant.token"
    adapter.issue_test_token(
        token_str,
        tenant_id=str(tenant_id),
    )

    with pytest.raises(TenancyViolationError, match="inactive or suspended"):
        service.authenticate_token(token_str)


def test_identity_service_fails_on_deactivated_tenant() -> None:
    """AC-R03-003-05: Deactivated tenant fails closed with TenancyViolationError."""
    adapter = InMemoryAuthAdapter()
    tenant_id = TenantId("tnt_deactivated_corp")
    tenant = _make_sample_tenant(tenant_id, TenantStatus.DEACTIVATED)
    query_port = MockTenantQueryPort({tenant_id: tenant})

    service = IdentityService(
        auth_port=adapter,
        tenant_query_port=query_port,
        tenancy_policy=TenantContextPolicy,
    )

    token_str = "deactivated.tenant.token"
    adapter.issue_test_token(
        token_str,
        tenant_id=str(tenant_id),
    )

    with pytest.raises(TenancyViolationError, match="inactive or suspended"):
        service.authenticate_token(token_str)


def test_identity_service_delegates_get_session_evidence() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)
    vt, se = adapter.issue_test_token("test.token", session_id="sess_del")

    retrieved = service.get_session_evidence("sess_del")
    assert retrieved.session_id == "sess_del"
    assert retrieved.is_active is True
