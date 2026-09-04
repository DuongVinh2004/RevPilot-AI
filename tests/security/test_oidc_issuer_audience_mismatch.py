"""
RevPilot AI — TC-P07-012: OIDC Issuer and Audience Mismatch Test
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §2.2
Conforms to INV-IAM-001 and INV-TEN-002.
"""

import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.iam.oidc import (
    JwksClient,
    OidcValidator,
    OidcTenantConfiguration,
    create_signed_jwt,
    IssuerMismatchError,
    InvalidSignatureError,
)


def test_oidc_issuer_and_audience_mismatch_fails_closed():
    """
    TC-P07-012: Inbound tokens with mismatched issuer ('iss') or audience ('aud')
    are strictly rejected with 401 ISSUER_MISMATCH. Insecure 'none' algorithm is also blocked.
    """
    kid = "key_binding_01"
    secret = "secret_for_issuer_audience_tests"

    jwks = JwksClient()
    jwks.register_key(kid=kid, secret=secret)
    validator = OidcValidator(jwks_client=jwks)

    tenant_id = TenantId.generate()
    legit_issuer = "https://auth.legit-enterprise.com"
    legit_client_id = "revpilot-registered-client-id"

    config = OidcTenantConfiguration(
        tenant_id=tenant_id,
        issuer_url=legit_issuer,
        client_id=legit_client_id,
    )

    now = UtcDateTime.now()
    now_ts = now.value.timestamp()

    # 1. Mismatched Issuer: Fail Closed (401 ISSUER_MISMATCH)
    forged_issuer_token = create_signed_jwt(
        payload={
            "iss": "https://auth.attacker-controlled.com",  # Forged!
            "aud": legit_client_id,
            "sub": "victim_user",
            "exp": now_ts + 3600,
            "nonce": "nonce_mismatch_1",
            "jti": "jti_bad_iss",
        },
        kid=kid,
        key_secret=secret,
    )

    with pytest.raises(IssuerMismatchError) as exc_info:
        validator.validate_id_token(
            forged_issuer_token,
            expected_nonce="nonce_mismatch_1",
            config=config,
            as_of_time=now,
        )
    assert exc_info.value.code == "ISSUER_MISMATCH"
    assert "Issuer mismatch" in exc_info.value.message

    # 2. Mismatched Audience: Fail Closed (401 ISSUER_MISMATCH)
    wrong_aud_token = create_signed_jwt(
        payload={
            "iss": legit_issuer,
            "aud": "some-other-target-app-client",  # Wrong client/audience!
            "sub": "victim_user",
            "exp": now_ts + 3600,
            "nonce": "nonce_mismatch_2",
            "jti": "jti_bad_aud",
        },
        kid=kid,
        key_secret=secret,
    )

    with pytest.raises(IssuerMismatchError) as exc_info:
        validator.validate_id_token(
            wrong_aud_token,
            expected_nonce="nonce_mismatch_2",
            config=config,
            as_of_time=now,
        )
    assert exc_info.value.code == "ISSUER_MISMATCH"
    assert "Audience mismatch" in exc_info.value.message

    # 3. Insecure 'none' Algorithm Attempt: Fail Closed (401 INVALID_SIGNATURE)
    insecure_none_token = create_signed_jwt(
        payload={
            "iss": legit_issuer,
            "aud": legit_client_id,
            "sub": "attacker_none_alg",
            "exp": now_ts + 3600,
            "nonce": "nonce_mismatch_3",
            "jti": "jti_none_alg",
        },
        kid=kid,
        key_secret=secret,
        alg="none",
    )

    with pytest.raises(InvalidSignatureError) as exc_info:
        validator.validate_id_token(
            insecure_none_token,
            expected_nonce="nonce_mismatch_3",
            config=config,
            as_of_time=now,
        )
    assert exc_info.value.code == "INVALID_SIGNATURE"
    assert "none" in exc_info.value.message.lower()
