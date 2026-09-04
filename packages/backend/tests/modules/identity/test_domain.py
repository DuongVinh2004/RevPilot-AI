"""
Unit and negative security contract tests for Identity domain models (TASK-R03-001).
Enforces INV-IAM-001, INV-TEN-002, INV-TEN-003, and INV-REL-001.
"""

from datetime import datetime, timedelta, timezone
import pytest

from revpilot.modules.identity.domain.models import (
    AuthTokenClaims,
    InMemoryTokenVerifier,
    Principal,
    PrincipalType,
    PrivilegedContext,
    ServiceAccountId,
    TokenVerificationPort,
    VerifiedClaimsToken,
    create_principal_from_verified_claims,
)
from revpilot.shared.context import PrincipalContext
from revpilot.shared.errors import (
    AuthenticationError,
    AuthorizationError,
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.identifiers import PrincipalId, TenantId
from revpilot.shared.temporal import UtcDateTime


def test_principal_type_members_and_values():
    """AC-R03-001-01: PrincipalType enum defines exact types."""
    assert PrincipalType.USER.value == "user"
    assert PrincipalType.SERVICE_ACCOUNT.value == "service_account"
    assert PrincipalType.AGENT.value == "agent"
    assert PrincipalType.SYSTEM.value == "system"
    assert len(PrincipalType) == 4


def test_auth_token_claims_valid_construction():
    """AC-R03-001-02: AuthTokenClaims construction with valid fields."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))
    claims = AuthTokenClaims(
        sub="usr_test123",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        nbf=now,
        tenant_id="tnt_customer_01",
        roles=frozenset({"analyst"}),
        permissions=frozenset({"investigation:read"}),
        email="analyst@example.com",
        jti="jti_unique_nonce_1",
    )
    assert claims.sub == "usr_test123"
    assert claims.iss == "revpilot-idp"
    assert claims.aud == "revpilot-api"
    assert claims.tenant_id == "tnt_customer_01"
    assert "analyst" in claims.roles
    assert "investigation:read" in claims.permissions
    assert not hasattr(claims, "is_system")


def test_auth_token_claims_rejects_is_system_injection():
    """AC-R03-001-02: is_system attribute is strictly prohibited."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))
    with pytest.raises(TypeError, match="unexpected keyword argument 'is_system'"):
        AuthTokenClaims(  # type: ignore[call-arg]
            sub="usr_test123",
            iss="revpilot-idp",
            aud="revpilot-api",
            exp=exp,
            iat=now,
            is_system=True,
        )


def test_auth_token_claims_rejects_naive_datetime():
    """AC-R03-001-02: AuthTokenClaims rejects naive datetime objects."""
    naive_now = datetime.now()
    with pytest.raises(TypeError, match="exp must be UtcDateTime"):
        AuthTokenClaims(
            sub="usr_test123",
            iss="revpilot-idp",
            aud="revpilot-api",
            exp=naive_now,  # type: ignore[arg-type]
            iat=UtcDateTime.now(),
        )


def test_auth_token_claims_validates_required_fields():
    """AC-R03-001-02: AuthTokenClaims validates non-empty sub, iss, aud."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))

    with pytest.raises(ValidationError, match="sub cannot be empty"):
        AuthTokenClaims(sub="   ", iss="revpilot-idp", aud="revpilot-api", exp=exp, iat=now)

    with pytest.raises(ValidationError, match="iss cannot be empty"):
        AuthTokenClaims(sub="usr_123", iss="", aud="revpilot-api", exp=exp, iat=now)

    with pytest.raises(ValidationError, match="aud cannot be empty"):
        AuthTokenClaims(sub="usr_123", iss="revpilot-idp", aud="", exp=exp, iat=now)

    with pytest.raises(ValidationError, match="sub must start with 'usr_' or 'svc_'"):
        AuthTokenClaims(sub="admin_root", iss="revpilot-idp", aud="revpilot-api", exp=exp, iat=now)


def test_verified_claims_token_requires_provenance():
    """AC-R03-001-03: VerifiedClaimsToken rejects raw payload construction without provenance."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))
    claims = AuthTokenClaims(
        sub="usr_test123",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_customer_01",
    )

    # Direct constructor call with forged/empty provenance fails closed
    with pytest.raises(AuthenticationError, match="Invalid claims token provenance proof"):
        VerifiedClaimsToken(
            claims=claims,
            verified_issuer="revpilot-idp",
            verified_audience="revpilot-api",
            session_id="sess_1",
            verified_at=now,
            signature_fingerprint="fp_123",
            _provenance_token="forged_token",
        )

    # Issuance via authorized boundary factory succeeds
    verified = VerifiedClaimsToken.issue(
        claims=claims,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_1",
        signature_fingerprint="fp_123",
        verified_at=now,
    )
    assert verified.claims == claims
    assert verified.session_id == "sess_1"


def test_privileged_context_no_public_construction_and_provenance_enforced():
    """AC-R03-001-04: PrivilegedContext requires valid platform authority signature."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=30))
    svc_id = ServiceAccountId("svc_platform_worker")

    # Direct instantiation with fake signature fails closed
    with pytest.raises(AuthorizationError, match="invalid platform provenance signature"):
        PrivilegedContext(
            principal_id=svc_id,
            ticket_id="INC-9999",
            justification="Emergency schema migration",
            issued_at=now,
            expires_at=exp,
            _provenance_signature="forged_signature",
        )

    # Valid issuance through platform boundary succeeds
    priv_ctx = PrivilegedContext._issue_platform_context(
        principal_id=svc_id,
        ticket_id="INC-9999",
        justification="Emergency schema migration",
        issued_at=now,
        expires_at=exp,
    )
    assert priv_ctx.is_valid(now) is True
    assert priv_ctx.principal_id == svc_id
    assert priv_ctx.ticket_id == "INC-9999"

    # Context expires after window
    future_time = UtcDateTime(exp.value + timedelta(seconds=1))
    assert priv_ctx.is_valid(future_time) is False


def test_privileged_context_maximum_lifetime_60_minutes():
    """AC-R03-001-04: PrivilegedContext enforces 60-minute maximum lifetime."""
    now = UtcDateTime.now()
    exp_61m = UtcDateTime(now.value + timedelta(minutes=61))
    svc_id = ServiceAccountId("svc_platform_worker")

    with pytest.raises(ValidationError, match="maximum lifetime is 60 minutes"):
        PrivilegedContext._issue_platform_context(
            principal_id=svc_id,
            ticket_id="INC-9999",
            justification="Long maintenance",
            issued_at=now,
            expires_at=exp_61m,
        )


def test_create_principal_from_verified_claims_rejects_unverified_claims():
    """AC-R03-001-05: create_principal_from_verified_claims rejects raw AuthTokenClaims."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))
    raw_claims = AuthTokenClaims(
        sub="usr_test123",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_customer_01",
    )

    with pytest.raises(TypeError, match="requires VerifiedClaimsToken"):
        create_principal_from_verified_claims(raw_claims)  # type: ignore[arg-type]


def test_create_principal_from_verified_claims_success():
    """AC-R03-001-05: Successful principal derivation from VerifiedClaimsToken."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))
    claims = AuthTokenClaims(
        sub="usr_alice",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_customer_01",
        roles=frozenset({"operator"}),
        permissions=frozenset({"investigation:create"}),
    )
    verified = VerifiedClaimsToken.issue(
        claims=claims,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_123",
        signature_fingerprint="sig_abc",
        verified_at=now,
    )

    principal = create_principal_from_verified_claims(verified, as_of=now)
    assert principal.id == PrincipalId("usr_alice")
    assert principal.type == PrincipalType.USER
    assert principal.tenant_id == TenantId("tnt_customer_01")
    assert principal.has_role("operator")
    assert principal.has_role("OPERATOR")  # case-insensitive
    assert principal.has_permission("investigation:create")


def test_create_principal_service_account():
    """Service account prefix svc_ produces PrincipalType.SERVICE_ACCOUNT."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))
    claims = AuthTokenClaims(
        sub="svc_connector_sync",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_customer_01",
    )
    verified = VerifiedClaimsToken.issue(
        claims=claims,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_456",
        signature_fingerprint="sig_def",
        verified_at=now,
    )

    principal = create_principal_from_verified_claims(verified, as_of=now)
    assert principal.type == PrincipalType.SERVICE_ACCOUNT
    assert isinstance(principal.id, ServiceAccountId)
    assert isinstance(principal.id, PrincipalId)


def test_create_principal_clock_skew_expiration_boundary():
    """AC-R03-001-06: 60-second clock skew tolerance on token expiration."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=10))
    claims = AuthTokenClaims(
        sub="usr_alice",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_customer_01",
    )
    verified = VerifiedClaimsToken.issue(
        claims=claims,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_1",
        signature_fingerprint="sig_1",
        verified_at=now,
    )

    # Exactly at exp + 59s: still within 60s tolerance, passes
    within_skew = UtcDateTime(exp.value + timedelta(seconds=59))
    p = create_principal_from_verified_claims(verified, as_of=within_skew)
    assert p.id == PrincipalId("usr_alice")

    # Exactly at exp + 60s: boundary fails closed
    at_boundary = UtcDateTime(exp.value + timedelta(seconds=60))
    with pytest.raises(AuthenticationError, match="Token has expired"):
        create_principal_from_verified_claims(verified, as_of=at_boundary)

    # Beyond boundary (exp + 61s): fails closed
    past_boundary = UtcDateTime(exp.value + timedelta(seconds=61))
    with pytest.raises(AuthenticationError, match="Token has expired"):
        create_principal_from_verified_claims(verified, as_of=past_boundary)


def test_create_principal_clock_skew_nbf_boundary():
    """AC-R03-001-06: 60-second clock skew tolerance on not-before (nbf) check."""
    now = UtcDateTime.now()
    nbf = UtcDateTime(now.value + timedelta(minutes=5))
    exp = UtcDateTime(now.value + timedelta(minutes=15))
    claims = AuthTokenClaims(
        sub="usr_alice",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        nbf=nbf,
        tenant_id="tnt_customer_01",
    )
    verified = VerifiedClaimsToken.issue(
        claims=claims,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_1",
        signature_fingerprint="sig_1",
        verified_at=now,
    )

    # Exactly at nbf - 60s: within skew tolerance, passes
    at_skew = UtcDateTime(nbf.value - timedelta(seconds=60))
    p = create_principal_from_verified_claims(verified, as_of=at_skew)
    assert p.id == PrincipalId("usr_alice")

    # At nbf - 61s: outside skew tolerance, fails closed
    before_skew = UtcDateTime(nbf.value - timedelta(seconds=61))
    with pytest.raises(AuthenticationError, match="Token not yet active"):
        create_principal_from_verified_claims(verified, as_of=before_skew)


def test_create_principal_rejects_missing_tenant():
    """AC-R03-001-07: create_principal_from_verified_claims strictly rejects missing tenant."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))
    claims = AuthTokenClaims(
        sub="usr_alice",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id=None,
    )
    verified = VerifiedClaimsToken.issue(
        claims=claims,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_1",
        signature_fingerprint="sig_1",
        verified_at=now,
    )

    with pytest.raises(TenancyViolationError, match="Principal lacks required tenant association"):
        create_principal_from_verified_claims(verified, as_of=now)


def test_principal_to_context_cannot_manufacture_system_privilege():
    """AC-R03-001-08: Principal.to_context() produces immutable context with is_system=False."""
    principal = Principal(
        id=PrincipalId("usr_alice"),
        type=PrincipalType.USER,
        tenant_id=TenantId("tnt_customer_01"),
        roles=frozenset({"operator"}),
        permissions=frozenset({"investigation:create"}),
    )

    ctx = principal.to_context()
    assert isinstance(ctx, PrincipalContext)
    assert ctx.is_system is False
    assert ctx.principal_id == principal.id
    assert ctx.tenant_id == principal.tenant_id

    # Verify Principal has no public is_system attribute
    assert not hasattr(principal, "is_system")


def test_token_verification_port_protocol_and_in_memory_verifier():
    """AC-R03-001-09: TokenVerificationPort protocol conformance and fail-closed checks."""
    verifier = InMemoryTokenVerifier(
        secret_key=b"test-secret-key-12345",
        active_sessions={"sess_active_01"},
        active_tenants={"tnt_acme_corp"},
    )
    assert isinstance(verifier, TokenVerificationPort)

    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=10))
    claims = AuthTokenClaims(
        sub="usr_bob",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_acme_corp",
        roles=frozenset({"analyst"}),
        jti="jti_unique_nonce_01",
    )

    token_str = verifier.sign_token(claims, session_id="sess_active_01")
    verified = verifier.verify_token(token_str, as_of=now)
    assert verified.claims.sub == "usr_bob"
    assert verified.session_id == "sess_active_01"


def test_token_verifier_signature_tamper_fails_closed():
    """Signature tampering raises AuthenticationError."""
    verifier = InMemoryTokenVerifier(
        secret_key=b"test-secret-key-12345",
        active_sessions={"sess_active_01"},
        active_tenants={"tnt_acme_corp"},
    )
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=10))
    claims = AuthTokenClaims(
        sub="usr_bob",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_acme_corp",
    )
    token_str = verifier.sign_token(claims, session_id="sess_active_01")
    tampered_token = token_str[:-4] + "dead"

    with pytest.raises(AuthenticationError, match="Invalid token signature"):
        verifier.verify_token(tampered_token, as_of=now)


def test_token_verifier_issuer_audience_mismatch():
    """Issuer or audience mismatch raises AuthenticationError."""
    verifier = InMemoryTokenVerifier(
        secret_key=b"test-secret-key-12345",
        active_sessions={"sess_active_01"},
        active_tenants={"tnt_acme_corp"},
    )
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=10))
    claims = AuthTokenClaims(
        sub="usr_bob",
        iss="evil-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_acme_corp",
    )
    token_str = verifier.sign_token(claims, session_id="sess_active_01")

    with pytest.raises(AuthenticationError, match="Issuer mismatch"):
        verifier.verify_token(token_str, expected_issuer="revpilot-idp", as_of=now)


def test_token_verifier_inactive_and_revoked_session():
    """Inactive or revoked session fails closed."""
    verifier = InMemoryTokenVerifier(
        secret_key=b"test-secret-key-12345",
        active_sessions={"sess_01"},
        revoked_sessions={"sess_revoked"},
        active_tenants={"tnt_acme_corp"},
    )
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=10))
    claims = AuthTokenClaims(
        sub="usr_bob",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_acme_corp",
    )

    # Inactive session
    token_inactive = verifier.sign_token(claims, session_id="sess_unregistered")
    with pytest.raises(AuthenticationError, match="Session is not active"):
        verifier.verify_token(token_inactive, as_of=now)

    # Revoked session
    verifier.add_active_session("sess_revoked")
    token_revoked = verifier.sign_token(claims, session_id="sess_revoked")
    with pytest.raises(AuthenticationError, match="Session has been revoked"):
        verifier.verify_token(token_revoked, as_of=now)


def test_token_verifier_anti_replay_jti():
    """Replay of token with same JTI fails closed."""
    verifier = InMemoryTokenVerifier(
        secret_key=b"test-secret-key-12345",
        active_sessions={"sess_01"},
        active_tenants={"tnt_acme_corp"},
    )
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=10))
    claims = AuthTokenClaims(
        sub="usr_bob",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_acme_corp",
        jti="replay_nonce_999",
    )
    token_str = verifier.sign_token(claims, session_id="sess_01")

    # First verification succeeds
    v1 = verifier.verify_token(token_str, as_of=now)
    assert v1.claims.jti == "replay_nonce_999"

    # Second verification fails closed on replay
    with pytest.raises(AuthenticationError, match="Token replay detected"):
        verifier.verify_token(token_str, as_of=now)


def test_token_verifier_inactive_tenant():
    """Inactive or suspended tenant raises TenancyViolationError."""
    verifier = InMemoryTokenVerifier(
        secret_key=b"test-secret-key-12345",
        active_sessions={"sess_01"},
        active_tenants={"tnt_active_only"},
    )
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=10))
    claims = AuthTokenClaims(
        sub="usr_bob",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_suspended_tenant",
    )
    token_str = verifier.sign_token(claims, session_id="sess_01")

    with pytest.raises(TenancyViolationError, match="deactivated or suspended"):
        verifier.verify_token(token_str, as_of=now)
