"""
RevPilot AI — TC-P07-010: OIDC Token Expiration and Clock Skew Test
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §2.2
Conforms to INV-IAM-001 and NFR-SEC-001.
"""

from datetime import timedelta
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.iam.oidc import (
    JwksClient,
    OidcValidator,
    OidcTenantConfiguration,
    create_signed_jwt,
    TokenExpiredError,
)


def test_oidc_token_expiration_and_clock_skew_tolerance():
    """
    TC-P07-010: Token expiration is strictly evaluated against UTC reference time.
    Tokens expired beyond the 60-second clock skew tolerance fail closed with 401 TOKEN_EXPIRED.
    Tokens within the 60-second skew window or unexpired pass verification.
    """
    kid = "key_test_01"
    secret = "secret_key_rotation_32bytes_value"

    jwks = JwksClient()
    jwks.register_key(kid=kid, secret=secret)
    validator = OidcValidator(jwks_client=jwks)

    tenant_id = TenantId.generate()
    issuer = "https://idp.enterprise.com"
    client_id = "revpilot-app-client"

    config = OidcTenantConfiguration(
        tenant_id=tenant_id,
        issuer_url=issuer,
        client_id=client_id,
        allowed_clock_skew_seconds=60,
    )

    now = UtcDateTime.now()
    now_ts = now.value.timestamp()

    # 1. Unexpired Token: Valid
    valid_payload = {
        "iss": issuer,
        "aud": client_id,
        "sub": "usr_12345",
        "email": "user@enterprise.com",
        "exp": now_ts + 300,  # 5 minutes in future
        "iat": now_ts - 60,
        "nonce": "nonce_abc_1",
        "jti": "jti_unexpired",
        "groups": ["Revenue_Analysts"],
    }
    valid_token = create_signed_jwt(valid_payload, kid=kid, key_secret=secret)
    claims = validator.validate_id_token(valid_token, expected_nonce="nonce_abc_1", config=config, as_of_time=now)
    assert claims.sub == "usr_12345"
    assert "analyst" in claims.roles

    # 2. Borderline Expired within Clock Skew (expired 30s ago, skew is 60s): PASS
    skew_payload = {
        "iss": issuer,
        "aud": client_id,
        "sub": "usr_12345",
        "email": "user@enterprise.com",
        "exp": now_ts - 30,  # Expired 30 seconds ago (< 60s skew)
        "iat": now_ts - 300,
        "nonce": "nonce_abc_2",
        "jti": "jti_within_skew",
        "groups": ["General_Users"],
    }
    skew_token = create_signed_jwt(skew_payload, kid=kid, key_secret=secret)
    skew_claims = validator.validate_id_token(skew_token, expected_nonce="nonce_abc_2", config=config, as_of_time=now)
    assert skew_claims.sub == "usr_12345"
    assert "operator" in skew_claims.roles

    # 3. Expired beyond Clock Skew (expired 90s ago, exceeds 60s skew): FAIL CLOSED (401)
    expired_payload = {
        "iss": issuer,
        "aud": client_id,
        "sub": "usr_12345",
        "email": "user@enterprise.com",
        "exp": now_ts - 90,  # Expired 90s ago (> 60s skew)
        "iat": now_ts - 600,
        "nonce": "nonce_abc_3",
        "jti": "jti_expired",
        "groups": ["General_Users"],
    }
    expired_token = create_signed_jwt(expired_payload, kid=kid, key_secret=secret)

    with pytest.raises(TokenExpiredError) as exc_info:
        validator.validate_id_token(expired_token, expected_nonce="nonce_abc_3", config=config, as_of_time=now)

    assert exc_info.value.code == "TOKEN_EXPIRED"
    assert "expired" in exc_info.value.message.lower()
