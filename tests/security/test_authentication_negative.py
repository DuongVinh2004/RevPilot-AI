"""
RevPilot AI — Authentication Negative Test Matrix (Rail 3 Exit Gate)
Exhaustive machine verification of fail-closed behavior across all boundary surfaces.
Enforces INV-IAM-001, INV-TEN-002, INV-TEN-003, INV-SEC-001, and INV-REL-001.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
import pytest

from revpilot.modules.identity.adapters.in_memory_auth_adapter import InMemoryAuthAdapter
from revpilot.modules.identity.domain.models import (
    AuthTokenClaims,
    InMemoryTokenVerifier,
    Principal,
    PrincipalType,
    PrivilegedContext,
    VerifiedClaimsToken,
    create_principal_from_verified_claims,
)
from revpilot.modules.identity.domain.token_policy import (
    SessionPolicy,
    TokenValidationPolicy,
    VerifiedSessionEvidence,
)
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
    AuthorizationError,
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


def _build_tenant(tenant_id_str: str, status: TenantStatus) -> Tenant:
    now = UtcDateTime.now()
    tid = TenantId(tenant_id_str)
    return Tenant(
        id=tid,
        organization_id=OrganizationId("org_test_boundary"),
        name="Test Boundary Corp",
        status=status,
        tier=SubscriptionTier.ENTERPRISE,
        entitlement=Entitlement(tier=SubscriptionTier.ENTERPRISE),
        created_at=now,
        updated_at=now,
    )


# ==============================================================================
# 1. Missing, Empty, and Whitespace Tokens (INV-IAM-001)
# ==============================================================================

def test_missing_and_empty_token_fails_closed_service_boundary() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    # None / non-string raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        service.authenticate_token(None)  # type: ignore
    assert exc_info.value.code == "VALIDATION_ERROR"

    with pytest.raises(ValidationError) as exc_info:
        service.authenticate_token(12345)  # type: ignore
    assert exc_info.value.code == "VALIDATION_ERROR"

    # Empty string raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        service.authenticate_token("")
    assert exc_info.value.code == "VALIDATION_ERROR"

    # Whitespace-only string raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        service.authenticate_token("   \t\n  ")
    assert exc_info.value.code == "VALIDATION_ERROR"


def test_missing_and_empty_token_fails_closed_adapter_boundary() -> None:
    adapter = InMemoryAuthAdapter()

    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token("")
    assert exc_info.value.code == "UNAUTHORIZED"

    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token("   ")
    assert exc_info.value.code == "UNAUTHORIZED"


# ==============================================================================
# 2. Forged and Unregistered Tokens (INV-IAM-001)
# ==============================================================================

def test_forged_or_unregistered_token_rejected_at_adapter() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token("forged.raw.token.signature")
    assert exc_info.value.code == "UNAUTHORIZED"

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_token("unregistered.token.jwt")
    assert exc_info.value.code == "UNAUTHORIZED"


# ==============================================================================
# 3. Cryptographic Signature Verification Failure (InMemoryTokenVerifier)
# ==============================================================================

def test_cryptographic_signature_tampering_fails_closed() -> None:
    verifier = InMemoryTokenVerifier()
    claims = AuthTokenClaims(
        sub="usr_victim",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=UtcDateTime(datetime.now(timezone.utc) + timedelta(hours=1)),
        iat=UtcDateTime.now(),
        tenant_id="tnt_safe",
    )
    verifier.add_active_session("sess_valid")
    signed_token = verifier.sign_token(claims, session_id="sess_valid")

    # Valid token verifies
    vt = verifier.verify_token(signed_token)
    assert vt.claims.sub == "usr_victim"

    # Tampered signature
    tampered_sig = signed_token[:-4] + "dead"
    with pytest.raises(AuthenticationError) as exc_info:
        verifier.verify_token(tampered_sig)
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "Invalid token signature" in str(exc_info.value)

    # Tampered payload
    parts = signed_token.split(".")
    tampered_payload = "eyJzdWIiOiAidXNyX2F0dGFja2VyIn0." + parts[1]
    with pytest.raises(AuthenticationError) as exc_info:
        verifier.verify_token(tampered_payload)
    assert exc_info.value.code == "UNAUTHORIZED"


# ==============================================================================
# 4. Issuer & Audience Mismatch (INV-IAM-001)
# ==============================================================================

def test_issuer_mismatch_fails_closed() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(
        auth_port=adapter,
        token_policy=TokenValidationPolicy(expected_issuer="revpilot-idp"),
    )

    adapter.issue_test_token("tok.bad_iss", iss="rogue-idp")

    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token("tok.bad_iss", expected_issuer="revpilot-idp")
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "Issuer mismatch" in str(exc_info.value)

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_token("tok.bad_iss")
    assert exc_info.value.code == "UNAUTHORIZED"


def test_audience_mismatch_fails_closed() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(
        auth_port=adapter,
        token_policy=TokenValidationPolicy(expected_audience="revpilot-api"),
    )

    adapter.issue_test_token("tok.bad_aud", aud="rogue-service")

    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token("tok.bad_aud", expected_audience="revpilot-api")
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "Audience mismatch" in str(exc_info.value)

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_token("tok.bad_aud")
    assert exc_info.value.code == "UNAUTHORIZED"


# ==============================================================================
# 5. Token Expiry and 60-Second Clock Skew Boundary
# ==============================================================================

def test_expired_token_beyond_clock_skew_fails_closed() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    now_dt = datetime.now(timezone.utc)
    # Expired 61 seconds ago -> outside 60s skew -> rejected
    exp_61s_ago = UtcDateTime(now_dt - timedelta(seconds=61))
    adapter.issue_test_token(
        "tok.exp61",
        exp=exp_61s_ago,
        iat=UtcDateTime(now_dt - timedelta(hours=1)),
        session_expires_at=UtcDateTime(now_dt + timedelta(hours=24)),
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_token("tok.exp61", as_of=UtcDateTime(now_dt))
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "Token has expired" in str(exc_info.value)


def test_expired_token_exactly_at_clock_skew_boundary_fails_closed() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    now_dt = datetime.now(timezone.utc)
    # Exactly at 60s skew boundary: check_time >= exp + skew (fail closed)
    exp_60s_ago = UtcDateTime(now_dt - timedelta(seconds=60))
    adapter.issue_test_token(
        "tok.exp60",
        exp=exp_60s_ago,
        iat=UtcDateTime(now_dt - timedelta(hours=1)),
        session_expires_at=UtcDateTime(now_dt + timedelta(hours=24)),
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_token("tok.exp60", as_of=UtcDateTime(now_dt))
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "Token has expired" in str(exc_info.value)


def test_token_within_clock_skew_boundary_accepted() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    now_dt = datetime.now(timezone.utc)
    # Expired 59s ago -> within 60s skew tolerance -> accepted
    exp_59s_ago = UtcDateTime(now_dt - timedelta(seconds=59))
    adapter.issue_test_token(
        "tok.exp59",
        exp=exp_59s_ago,
        iat=UtcDateTime(now_dt - timedelta(hours=1)),
        session_expires_at=UtcDateTime(now_dt + timedelta(hours=24)),
    )

    principal = service.authenticate_token("tok.exp59", as_of=UtcDateTime(now_dt))
    assert principal.id == PrincipalId("usr_test_user")


# ==============================================================================
# 6. Future Not-Before (nbf) Timestamp and Clock Skew
# ==============================================================================

def test_future_nbf_beyond_clock_skew_fails_closed() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    now_dt = datetime.now(timezone.utc)
    # Active 61s in future -> outside 60s tolerance -> rejected
    nbf_61s_future = UtcDateTime(now_dt + timedelta(seconds=61))
    adapter.issue_test_token(
        "tok.nbf61",
        nbf=nbf_61s_future,
        iat=UtcDateTime(now_dt - timedelta(minutes=5)),
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_token("tok.nbf61", as_of=UtcDateTime(now_dt))
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "Token not yet active" in str(exc_info.value)


def test_future_nbf_within_clock_skew_boundary_accepted() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    now_dt = datetime.now(timezone.utc)
    # Active 59s in future -> within 60s tolerance -> accepted
    nbf_59s_future = UtcDateTime(now_dt + timedelta(seconds=59))
    adapter.issue_test_token(
        "tok.nbf59",
        nbf=nbf_59s_future,
        iat=UtcDateTime(now_dt - timedelta(minutes=5)),
    )

    principal = service.authenticate_token("tok.nbf59", as_of=UtcDateTime(now_dt))
    assert principal.id == PrincipalId("usr_test_user")


# ==============================================================================
# 7. Session Revocation (INV-IAM-001, INV-REL-001)
# ==============================================================================

def test_revoked_session_fails_closed_immediately() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    token_str = "tok.session.revocation"
    adapter.issue_test_token(token_str, session_id="sess_target_revocation")

    # Revoke session
    service.revoke_session("sess_target_revocation")

    # Subsequent verification must fail
    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_token(token_str)
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "Token or session has been revoked" in str(exc_info.value)

    # Adapter direct call also fails
    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token(token_str)
    assert exc_info.value.code == "UNAUTHORIZED"


def test_inactive_and_expired_session_evidence_fails_closed() -> None:
    policy = SessionPolicy()
    now_dt = datetime.now(timezone.utc)

    # Inactive session evidence
    ev_inactive = VerifiedSessionEvidence.issue(
        session_id="sess_inactive",
        is_active=False,
        is_revoked=False,
        issued_at=UtcDateTime(now_dt - timedelta(hours=2)),
        expires_at=UtcDateTime(now_dt + timedelta(hours=1)),
    )
    with pytest.raises(AuthenticationError) as exc_info:
        policy.validate_session_evidence(ev_inactive)
    assert exc_info.value.code == "UNAUTHORIZED"

    # Expired session evidence
    ev_expired = VerifiedSessionEvidence.issue(
        session_id="sess_exp",
        is_active=True,
        is_revoked=False,
        issued_at=UtcDateTime(now_dt - timedelta(hours=2)),
        expires_at=UtcDateTime(now_dt - timedelta(seconds=10)),
    )
    with pytest.raises(AuthenticationError) as exc_info:
        policy.validate_session_evidence(ev_expired, as_of=UtcDateTime(now_dt))
    assert exc_info.value.code == "UNAUTHORIZED"


# ==============================================================================
# 8. Missing, Inactive, Suspended, or Deactivated Tenants (INV-TEN-003, INV-TEN-002)
# ==============================================================================

def test_token_lacking_tenant_association_fails_closed() -> None:
    # Attempting to construct AuthTokenClaims without tenant_id raises error downstream in factory
    with pytest.raises(TenancyViolationError) as exc_info:
        claims = AuthTokenClaims(
            sub="usr_no_tenant",
            iss="revpilot-idp",
            aud="revpilot-api",
            exp=UtcDateTime(datetime.now(timezone.utc) + timedelta(hours=1)),
            iat=UtcDateTime.now(),
            tenant_id=None,
        )
        vt = VerifiedClaimsToken.issue(
            claims=claims,
            verified_issuer="revpilot-idp",
            verified_audience="revpilot-api",
            session_id="sess_noten",
            signature_fingerprint="fp1234",
        )
        create_principal_from_verified_claims(vt)
    assert exc_info.value.code == "TENANCY_VIOLATION"


def test_nonexistent_tenant_fails_closed() -> None:
    adapter = InMemoryAuthAdapter()
    query_port = MockTenantQueryPort({})
    service = IdentityService(
        auth_port=adapter,
        tenant_query_port=query_port,
        tenancy_policy=TenantContextPolicy,
    )

    adapter.issue_test_token("tok.ghost_tenant", tenant_id="tnt_does_not_exist")

    with pytest.raises(TenancyViolationError) as exc_info:
        service.authenticate_token("tok.ghost_tenant")
    assert exc_info.value.code == "TENANCY_VIOLATION"
    assert "does not exist" in str(exc_info.value)


@pytest.mark.parametrize(
    "bad_status",
    [
        TenantStatus.SUSPENDED,
        TenantStatus.DEACTIVATED,
        TenantStatus.PROVISIONING,
    ],
)
def test_inactive_suspended_deactivated_tenant_fails_closed(bad_status: TenantStatus) -> None:
    tid_str = f"tnt_{bad_status.value}_corp"
    tenant = _build_tenant(tid_str, bad_status)
    adapter = InMemoryAuthAdapter()
    query_port = MockTenantQueryPort({TenantId(tid_str): tenant})
    service = IdentityService(
        auth_port=adapter,
        tenant_query_port=query_port,
        tenancy_policy=TenantContextPolicy,
    )

    adapter.issue_test_token("tok.tenant_status_check", tenant_id=tid_str)

    with pytest.raises(TenancyViolationError) as exc_info:
        service.authenticate_token("tok.tenant_status_check")
    assert exc_info.value.code == "TENANCY_VIOLATION"


# ==============================================================================
# 9. Attempted is_system Injection and Privilege Escalation (INV-TEN-003, INV-IAM-001)
# ==============================================================================

def test_attempted_is_system_injection_structurally_blocked() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    # Token-authenticated actor is always USER or SERVICE_ACCOUNT, never SYSTEM
    adapter.issue_test_token("tok.alice", sub="usr_alice", tenant_id="tnt_corp")
    principal = service.authenticate_token("tok.alice")
    assert principal.type != PrincipalType.SYSTEM
    assert principal.type == PrincipalType.USER

    # to_context() hardcodes is_system=False
    ctx = principal.to_context()
    assert ctx.is_system is False

    # Structural check: Principal aggregates authenticated from tokens cannot manufacture is_system=True
    assert "is_system" not in AuthTokenClaims.__dataclass_fields__


def test_forged_privileged_context_fails_closed() -> None:
    """PrivilegedContext rejects forged platform signatures."""
    now_dt = datetime.now(timezone.utc)
    with pytest.raises(AuthorizationError) as exc_info:
        PrivilegedContext(
            principal_id=PrincipalId("usr_hacker"),
            ticket_id="INC-9999",
            justification="Need root access",
            issued_at=UtcDateTime(now_dt),
            expires_at=UtcDateTime(now_dt + timedelta(minutes=15)),
            _provenance_signature="forged_signature_hex",
        )
    assert exc_info.value.code == "FORBIDDEN"
    assert "invalid platform provenance signature" in str(exc_info.value)


# ==============================================================================
# 10. Raw / Unverified Claims Bypass Protection (Verified Boundary)
# ==============================================================================

def test_raw_claims_cannot_bypass_verified_boundary() -> None:
    claims = AuthTokenClaims(
        sub="usr_unverified",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=UtcDateTime(datetime.now(timezone.utc) + timedelta(hours=1)),
        iat=UtcDateTime.now(),
        tenant_id="tnt_test",
    )

    # Domain factory strictly demands VerifiedClaimsToken
    with pytest.raises(TypeError, match="requires VerifiedClaimsToken"):
        create_principal_from_verified_claims(claims)  # type: ignore

    # Token policy strictly demands VerifiedClaimsToken
    policy = TokenValidationPolicy()
    with pytest.raises(TypeError, match="requires VerifiedClaimsToken"):
        policy.validate_verified_token(claims)  # type: ignore

    # Session policy strictly demands VerifiedSessionEvidence
    spolicy = SessionPolicy()
    with pytest.raises(TypeError, match="requires VerifiedSessionEvidence"):
        spolicy.validate_session_evidence(claims)  # type: ignore


def test_tampered_verified_token_provenance_rejected() -> None:
    """VerifiedClaimsToken constructor verifies cryptographic HMAC provenance."""
    claims = AuthTokenClaims(
        sub="usr_tampered",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=UtcDateTime(datetime.now(timezone.utc) + timedelta(hours=1)),
        iat=UtcDateTime.now(),
        tenant_id="tnt_test",
    )

    with pytest.raises(AuthenticationError) as exc_info:
        VerifiedClaimsToken(
            claims=claims,
            verified_issuer="revpilot-idp",
            verified_audience="revpilot-api",
            session_id="sess_tampered",
            verified_at=UtcDateTime.now(),
            signature_fingerprint="fp1234",
            _provenance_token="invalid_hmac_proof",
        )
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "Invalid claims token provenance proof" in str(exc_info.value)


# ==============================================================================
# 11. Zero Secret and Password Exposure (INV-SEC-001)
# ==============================================================================

def test_zero_raw_secrets_exposed_on_identity_entities() -> None:
    adapter = InMemoryAuthAdapter()
    service = IdentityService(auth_port=adapter)

    adapter.issue_test_token("tok.audit_leak_check", sub="usr_auditor", tenant_id="tnt_audit")
    principal = service.authenticate_token("tok.audit_leak_check")
    ctx = principal.to_context()

    # Verify no secret-bearing attributes exist
    forbidden_attrs = ["password", "secret", "private_key", "token", "hash", "cred"]
    for obj in [principal, ctx]:
        for attr in dir(obj):
            if attr.startswith("_"):
                continue
            assert not any(bad in attr.lower() for bad in forbidden_attrs), (
                f"Attribute '{attr}' on {type(obj).__name__} potentially exposes sensitive data"
            )

    # String representation does not leak secrets
    rep = repr(principal)
    assert "password" not in rep.lower()
    assert "secret" not in rep.lower()
