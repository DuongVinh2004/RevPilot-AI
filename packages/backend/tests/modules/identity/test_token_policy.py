"""
Unit and negative security contract tests for Token and Session Policies (TASK-R03-002).
Enforces INV-IAM-001, INV-TEN-002, INV-TEN-003, and INV-REL-001.
"""

from datetime import timedelta
import inspect
from typing import Protocol, get_type_hints
import pytest

from revpilot.modules.identity.domain.models import (
    AuthTokenClaims,
    VerifiedClaimsToken,
)
from revpilot.modules.identity.domain.token_policy import (
    SessionPolicy,
    TokenValidationPolicy,
    VerifiedSessionEvidence,
)
from revpilot.modules.identity.ports.authentication import AuthenticationPort
from revpilot.shared.errors import (
    AuthenticationError,
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.temporal import UtcDateTime


def _make_verified_claims_token(
    *,
    sub: str = "usr_alice",
    iss: str = "revpilot-idp",
    aud: str = "revpilot-api",
    exp_offset_minutes: int = 15,
    nbf_offset_minutes: int | None = None,
    tenant_id: str | None = "tnt_acme_corp",
    roles: frozenset[str] = frozenset({"operator"}),
    as_of: UtcDateTime | None = None,
) -> tuple[VerifiedClaimsToken, UtcDateTime]:
    """Helper creating valid VerifiedClaimsToken with consistent timestamps."""
    now = as_of or UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=exp_offset_minutes))
    nbf = UtcDateTime(now.value + timedelta(minutes=nbf_offset_minutes)) if nbf_offset_minutes is not None else None
    claims = AuthTokenClaims(
        sub=sub,
        iss=iss,
        aud=aud,
        exp=exp,
        iat=now,
        nbf=nbf,
        tenant_id=tenant_id,
        roles=roles,
    )
    token = VerifiedClaimsToken.issue(
        claims=claims,
        verified_issuer=iss,
        verified_audience=aud,
        session_id="sess_valid_001",
        signature_fingerprint="sig_fp_12345",
        verified_at=now,
    )
    return token, now


# ---------------------------------------------------------------------------
# AC-R03-002-01: Issuer and Audience Validation
# ---------------------------------------------------------------------------

def test_token_policy_accepts_valid_issuer_and_audience():
    """AC-R03-002-01: TokenValidationPolicy accepts matching issuer and audience."""
    policy = TokenValidationPolicy(
        expected_issuer="revpilot-idp",
        expected_audience="revpilot-api",
        clock_skew_seconds=60,
    )
    token, now = _make_verified_claims_token(iss="revpilot-idp", aud="revpilot-api")
    policy.validate_verified_token(token, as_of=now)


def test_token_policy_rejects_issuer_mismatch():
    """AC-R03-002-01: Rejects mismatched issuer with AuthenticationError."""
    policy = TokenValidationPolicy(expected_issuer="revpilot-idp", expected_audience="revpilot-api")
    token, now = _make_verified_claims_token(iss="evil-idp", aud="revpilot-api")
    with pytest.raises(AuthenticationError, match="Invalid token issuer"):
        policy.validate_verified_token(token, as_of=now)


def test_token_policy_rejects_audience_mismatch():
    """AC-R03-002-01: Rejects mismatched audience with AuthenticationError."""
    policy = TokenValidationPolicy(expected_issuer="revpilot-idp", expected_audience="revpilot-api")
    token, now = _make_verified_claims_token(iss="revpilot-idp", aud="foreign-api")
    with pytest.raises(AuthenticationError, match="Invalid token audience"):
        policy.validate_verified_token(token, as_of=now)


# ---------------------------------------------------------------------------
# AC-R03-002-02: Clock Skew Configuration and Validation
# ---------------------------------------------------------------------------

def test_token_policy_clock_skew_parameter_bounds():
    """AC-R03-002-02: clock_skew_seconds must be between 0 and 60."""
    # Valid boundaries
    TokenValidationPolicy(clock_skew_seconds=0)
    TokenValidationPolicy(clock_skew_seconds=60)

    # Invalid negative
    with pytest.raises(ValidationError, match="between 0 and 60"):
        TokenValidationPolicy(clock_skew_seconds=-1)

    # Invalid greater than 60
    with pytest.raises(ValidationError, match="between 0 and 60"):
        TokenValidationPolicy(clock_skew_seconds=61)

    # Invalid type
    with pytest.raises(ValidationError, match="must be int"):
        TokenValidationPolicy(clock_skew_seconds="60")  # type: ignore[arg-type]


def test_token_policy_expiration_clock_skew_boundary():
    """AC-R03-002-02: Expiration check respects bounded 60s clock skew."""
    policy = TokenValidationPolicy(clock_skew_seconds=60)
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=10))
    claims = AuthTokenClaims(
        sub="usr_alice",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_acme_corp",
    )
    token = VerifiedClaimsToken.issue(
        claims=claims,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_1",
        signature_fingerprint="fp_1",
        verified_at=now,
    )

    # 59 seconds past expiration: within 60s skew, passes
    at_59s = UtcDateTime(exp.value + timedelta(seconds=59))
    policy.validate_verified_token(token, as_of=at_59s)

    # 60 seconds past expiration: at boundary, fails closed
    at_60s = UtcDateTime(exp.value + timedelta(seconds=60))
    with pytest.raises(AuthenticationError, match="Token has expired"):
        policy.validate_verified_token(token, as_of=at_60s)

    # 61 seconds past expiration: past boundary, fails closed
    at_61s = UtcDateTime(exp.value + timedelta(seconds=61))
    with pytest.raises(AuthenticationError, match="Token has expired"):
        policy.validate_verified_token(token, as_of=at_61s)


def test_token_policy_nbf_clock_skew_boundary():
    """AC-R03-002-02: Not-before (nbf) check respects bounded 60s clock skew."""
    policy = TokenValidationPolicy(clock_skew_seconds=60)
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
        tenant_id="tnt_acme_corp",
    )
    token = VerifiedClaimsToken.issue(
        claims=claims,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_1",
        signature_fingerprint="fp_1",
        verified_at=now,
    )

    # Exactly at nbf - 60s: within skew, passes
    at_skew = UtcDateTime(nbf.value - timedelta(seconds=60))
    policy.validate_verified_token(token, as_of=at_skew)

    # At nbf - 61s: outside skew tolerance, fails closed
    before_skew = UtcDateTime(nbf.value - timedelta(seconds=61))
    with pytest.raises(AuthenticationError, match="Token not yet active"):
        policy.validate_verified_token(token, as_of=before_skew)


def test_token_policy_enforces_tenant_association():
    """AC-R03-002-02 & INV-TEN-003: Rejects missing or malformed tenant association."""
    policy = TokenValidationPolicy()
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))

    # Missing tenant
    claims_no_tenant = AuthTokenClaims(
        sub="usr_alice",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id=None,
    )
    token_no_tenant = VerifiedClaimsToken.issue(
        claims=claims_no_tenant,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_1",
        signature_fingerprint="fp_1",
        verified_at=now,
    )
    with pytest.raises(TenancyViolationError, match="Principal lacks required tenant association"):
        policy.validate_verified_token(token_no_tenant, as_of=now)

    # Malformed tenant
    claims_bad_tenant = AuthTokenClaims(
        sub="usr_alice",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="malformed_without_prefix",
    )
    token_bad_tenant = VerifiedClaimsToken.issue(
        claims=claims_bad_tenant,
        verified_issuer="revpilot-idp",
        verified_audience="revpilot-api",
        session_id="sess_1",
        signature_fingerprint="fp_1",
        verified_at=now,
    )
    with pytest.raises(TenancyViolationError, match="Invalid tenant_id in verified token claims"):
        policy.validate_verified_token(token_bad_tenant, as_of=now)


def test_token_policy_rejects_unverified_claims():
    """TokenValidationPolicy requires VerifiedClaimsToken, rejecting raw AuthTokenClaims."""
    policy = TokenValidationPolicy()
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(minutes=15))
    raw_claims = AuthTokenClaims(
        sub="usr_alice",
        iss="revpilot-idp",
        aud="revpilot-api",
        exp=exp,
        iat=now,
        tenant_id="tnt_acme_corp",
    )
    with pytest.raises(TypeError, match="validate_verified_token requires VerifiedClaimsToken"):
        policy.validate_verified_token(raw_claims, as_of=now)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC-R03-002-03: VerifiedSessionEvidence Provenance
# ---------------------------------------------------------------------------

def test_verified_session_evidence_provenance_and_immutability():
    """AC-R03-002-03: VerifiedSessionEvidence requires valid provenance signature."""
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(hours=8))

    # Rejection of forged signature
    with pytest.raises(AuthenticationError, match="Invalid session evidence provenance signature"):
        VerifiedSessionEvidence(
            session_id="sess_001",
            is_active=True,
            is_revoked=False,
            issued_at=now,
            expires_at=exp,
            _provenance_signature="forged_sig",
        )

    # Valid issuance succeeds
    evidence = VerifiedSessionEvidence.issue(
        session_id="sess_001",
        is_active=True,
        is_revoked=False,
        issued_at=now,
        expires_at=exp,
    )
    assert evidence.session_id == "sess_001"
    assert evidence.is_active is True
    assert evidence.is_revoked is False
    assert evidence.is_valid(now) is True

    # Immutability
    with pytest.raises((AttributeError, TypeError)):
        evidence.is_revoked = True  # type: ignore[misc]


def test_verified_session_evidence_validation_rules():
    """VerifiedSessionEvidence rejects invalid time intervals and types."""
    now = UtcDateTime.now()
    past = UtcDateTime(now.value - timedelta(minutes=5))

    # expires_at <= issued_at
    with pytest.raises(ValidationError, match="expires_at must be strictly after issued_at"):
        VerifiedSessionEvidence.issue(
            session_id="sess_001",
            is_active=True,
            is_revoked=False,
            issued_at=now,
            expires_at=past,
        )

    # Empty session_id
    with pytest.raises(ValidationError, match="session_id must be non-empty"):
        VerifiedSessionEvidence.issue(
            session_id="   ",
            is_active=True,
            is_revoked=False,
            issued_at=now,
            expires_at=UtcDateTime(now.value + timedelta(hours=1)),
        )


# ---------------------------------------------------------------------------
# AC-R03-002-04: SessionPolicy Validation
# ---------------------------------------------------------------------------

def test_session_policy_accepts_active_unrevoked_session():
    """AC-R03-002-04: SessionPolicy accepts valid active unrevoked session evidence."""
    policy = SessionPolicy()
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(hours=4))
    evidence = VerifiedSessionEvidence.issue(
        session_id="sess_001",
        is_active=True,
        is_revoked=False,
        issued_at=now,
        expires_at=exp,
    )
    policy.validate_session_evidence(evidence, as_of=now)


def test_session_policy_rejects_revoked_session():
    """AC-R03-002-04: SessionPolicy rejects revoked session with AuthenticationError."""
    policy = SessionPolicy()
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(hours=4))
    evidence = VerifiedSessionEvidence.issue(
        session_id="sess_revoked",
        is_active=True,
        is_revoked=True,
        issued_at=now,
        expires_at=exp,
    )
    with pytest.raises(AuthenticationError, match="Token or session has been revoked"):
        policy.validate_session_evidence(evidence, as_of=now)


def test_session_policy_rejects_inactive_session():
    """AC-R03-002-04: SessionPolicy rejects inactive session with AuthenticationError."""
    policy = SessionPolicy()
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(hours=4))
    evidence = VerifiedSessionEvidence.issue(
        session_id="sess_inactive",
        is_active=False,
        is_revoked=False,
        issued_at=now,
        expires_at=exp,
    )
    with pytest.raises(AuthenticationError, match="Token or session has been revoked"):
        policy.validate_session_evidence(evidence, as_of=now)


def test_session_policy_rejects_expired_session():
    """AC-R03-002-04: SessionPolicy rejects expired session evidence."""
    policy = SessionPolicy()
    now = UtcDateTime.now()
    exp = UtcDateTime(now.value + timedelta(hours=1))
    evidence = VerifiedSessionEvidence.issue(
        session_id="sess_expired",
        is_active=True,
        is_revoked=False,
        issued_at=now,
        expires_at=exp,
    )
    future = UtcDateTime(exp.value + timedelta(seconds=1))
    with pytest.raises(AuthenticationError, match="Token or session has been revoked"):
        policy.validate_session_evidence(evidence, as_of=future)


def test_session_policy_rejects_non_evidence_and_no_old_boolean_api():
    """AC-R03-002-04: SessionPolicy does not expose or accept caller boolean API."""
    policy = SessionPolicy()
    assert not hasattr(policy, "validate_session")

    # Reject non-VerifiedSessionEvidence
    with pytest.raises(TypeError, match="validate_session_evidence requires VerifiedSessionEvidence"):
        policy.validate_session_evidence("sess_raw_string")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC-R03-002-05: AuthenticationPort Protocol Conformance
# ---------------------------------------------------------------------------

def test_authentication_port_protocol_conformance_and_signatures():
    """AC-R03-002-05: AuthenticationPort is typing Protocol with exact signatures."""
    assert issubclass(AuthenticationPort, Protocol)

    # Inspect verify_token signature and return annotation
    sig = inspect.signature(AuthenticationPort.verify_token)
    assert "token" in sig.parameters
    assert "expected_issuer" in sig.parameters
    assert "expected_audience" in sig.parameters
    assert "as_of" in sig.parameters
    hints = get_type_hints(AuthenticationPort.verify_token)
    assert hints["return"] is VerifiedClaimsToken  # Must return VerifiedClaimsToken, NOT Principal

    # Inspect get_session_evidence
    evidence_hints = get_type_hints(AuthenticationPort.get_session_evidence)
    assert evidence_hints["return"] is VerifiedSessionEvidence

    # Inspect revoke_session
    revoke_sig = inspect.signature(AuthenticationPort.revoke_session)
    assert "session_id" in revoke_sig.parameters


def test_mock_adapter_implements_authentication_port():
    """AC-R03-002-05: Minimal mock adapter conforms to runtime_checkable AuthenticationPort."""
    class MockAuthAdapter:
        def verify_token(
            self,
            token: str,
            *,
            expected_issuer: str = "revpilot-idp",
            expected_audience: str = "revpilot-api",
            as_of: UtcDateTime | None = None,
        ) -> VerifiedClaimsToken:
            if not token or not token.strip():
                raise AuthenticationError("Token cannot be empty or whitespace")
            token_obj, _ = _make_verified_claims_token(iss=expected_issuer, aud=expected_audience, as_of=as_of)
            return token_obj

        def revoke_session(self, session_id: str) -> None:
            pass

        def get_session_evidence(
            self,
            session_id: str,
            as_of: UtcDateTime | None = None,
        ) -> VerifiedSessionEvidence:
            now = as_of or UtcDateTime.now()
            return VerifiedSessionEvidence.issue(
                session_id=session_id,
                is_active=True,
                is_revoked=False,
                issued_at=now,
                expires_at=UtcDateTime(now.value + timedelta(hours=1)),
            )

    adapter = MockAuthAdapter()
    assert isinstance(adapter, AuthenticationPort)

    # Empty token rejected
    with pytest.raises(AuthenticationError, match="Token cannot be empty"):
        adapter.verify_token("   ")

    # Valid token verified
    result = adapter.verify_token("valid.token.jwt")
    assert isinstance(result, VerifiedClaimsToken)
