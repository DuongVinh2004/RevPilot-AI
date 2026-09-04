"""
RevPilot AI — TC-P07-011: OIDC Dynamic JWKS Key Rotation Test
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §2.2
Conforms to NFR-SEC-001 and INV-IAM-001.
"""

import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.iam.oidc import (
    JwksClient,
    OidcValidator,
    OidcTenantConfiguration,
    create_signed_jwt,
    InvalidSignatureError,
)


def test_oidc_dynamic_jwks_key_rotation():
    """
    TC-P07-011: When an external IdP rotates keys and issues an ID token with an unknown 'kid',
    the JwksClient dynamically refreshes its key cache from the IdP without system downtime.
    Validation succeeds for the rotated key, and fails closed for non-existent keys.
    """
    # 1. Simulate Remote IdP JWKS endpoint state
    remote_keys = {
        "key_v1": {"kid": "key_v1", "secret": "secret_v1_primary", "alg": "RS256"},
    }

    def remote_jwks_provider():
        return list(remote_keys.values())

    jwks = JwksClient(remote_provider=remote_jwks_provider)
    # Warm initial cache
    jwks.refresh_keys()
    assert jwks.fetch_count == 1
    assert "key_v1" in jwks._cache
    assert "key_v2_rotated" not in jwks._cache

    validator = OidcValidator(jwks_client=jwks)
    tenant_id = TenantId.generate()
    config = OidcTenantConfiguration(
        tenant_id=tenant_id,
        issuer_url="https://idp.okta.enterprise.com",
        client_id="revpilot-pilot-client",
    )

    now = UtcDateTime.now()
    now_ts = now.value.timestamp()

    # 2. Token signed with active key_v1: PASS
    token_v1 = create_signed_jwt(
        payload={
            "iss": config.issuer_url,
            "aud": config.client_id,
            "sub": "usr_v1",
            "exp": now_ts + 3600,
            "nonce": "n_1",
            "jti": "jti_v1",
        },
        kid="key_v1",
        key_secret="secret_v1_primary",
    )
    claims_v1 = validator.validate_id_token(token_v1, expected_nonce="n_1", config=config, as_of_time=now)
    assert claims_v1.sub == "usr_v1"
    assert jwks.fetch_count == 1  # No rotation needed

    # 3. IdP rotates key: registers key_v2_rotated on remote server
    remote_keys["key_v2_rotated"] = {
        "kid": "key_v2_rotated",
        "secret": "secret_v2_new_generation",
        "alg": "RS256",
    }

    # Inbound token with new kid 'key_v2_rotated'
    token_v2 = create_signed_jwt(
        payload={
            "iss": config.issuer_url,
            "aud": config.client_id,
            "sub": "usr_v2_after_rotation",
            "exp": now_ts + 3600,
            "nonce": "n_2",
            "jti": "jti_v2",
        },
        kid="key_v2_rotated",
        key_secret="secret_v2_new_generation",
    )

    # Dynamic rotation test: Validator queries jwks for unknown kid, triggering refresh
    claims_v2 = validator.validate_id_token(token_v2, expected_nonce="n_2", config=config, as_of_time=now)
    assert claims_v2.sub == "usr_v2_after_rotation"
    assert jwks.fetch_count == 2  # Dynamic fetch executed automatically without downtime!
    assert "key_v2_rotated" in jwks._cache

    # 4. Unknown kid that does NOT exist on remote IdP: FAILS CLOSED
    bogus_token = create_signed_jwt(
        payload={
            "iss": config.issuer_url,
            "aud": config.client_id,
            "sub": "usr_hacker",
            "exp": now_ts + 3600,
            "nonce": "n_3",
            "jti": "jti_v3",
        },
        kid="key_completely_unknown",
        key_secret="secret_random",
    )

    with pytest.raises(InvalidSignatureError) as exc_info:
        validator.validate_id_token(bogus_token, expected_nonce="n_3", config=config, as_of_time=now)

    assert exc_info.value.code == "INVALID_SIGNATURE"
    assert "Unknown JWKS key ID" in exc_info.value.message
