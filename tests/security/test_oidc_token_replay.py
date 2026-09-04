"""
RevPilot AI — TC-P07-013: OIDC Token Replay Protection & Session Callback Test
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §2.2
Conforms to INV-IAM-002, INV-TEN-002, and NFR-SEC-001.
"""

import pytest

from revpilot.shared.identifiers import TenantId, OrganizationId, UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import AuthenticationError
from revpilot.modules.tenancy import (
    InMemoryTenantRepository,
    TenantService,
    TenantProvisioningRequest,
    SubscriptionTier,
)
from revpilot.modules.iam.oidc import (
    JwksClient,
    OidcValidator,
    OidcSessionManager,
    OidcTenantConfiguration,
    OidcSessionCookie,
    create_signed_jwt,
    TokenReplayError,
)


def test_oidc_token_replay_rejected_and_session_callback_flow():
    """
    TC-P07-013: Replaying an ID token with duplicate JTI within token lifetime
    is rejected with 401 TOKEN_REPLAY. PKCE Authorization Code flow establishes
    server-derived PrincipalContext for active tenants.
    """
    kid = "key_replay_01"
    secret = "secret_replay_prevention_key_64"

    jwks = JwksClient()
    jwks.register_key(kid=kid, secret=secret)
    validator = OidcValidator(jwks_client=jwks)

    # Initialize Tenancy Service
    tenant_repo = InMemoryTenantRepository()
    tenant_svc = TenantService(query_port=tenant_repo, command_port=tenant_repo)
    org = tenant_svc.create_organization("Replay Safe Corp")
    tenant_id = TenantId.generate()

    prov_req = TenantProvisioningRequest(
        request_id=UUIDv7.generate(),
        organization_id=org.id,
        name="Replay Safe Tenant",
        admin_email="admin@replaysafe.com",
        tier=SubscriptionTier.SHARED,
        tenant_id=tenant_id,
    )
    tenant_svc.provision_tenant_idempotent(prov_req)
    tenant_svc.activate_tenant(tenant_id)

    issuer = "https://sso.replaysafe.com"
    client_id = "revpilot-replay-client"

    config = OidcTenantConfiguration(
        tenant_id=tenant_id,
        issuer_url=issuer,
        client_id=client_id,
    )

    session_mgr = OidcSessionManager(tenant_service=tenant_svc, validator=validator)
    session_mgr.register_configuration(config)

    now = UtcDateTime.now()
    now_ts = now.value.timestamp()

    # 1. Initiate PKCE Authorization Request
    auth_req = session_mgr.initiate_authorization(tenant_id=tenant_id)
    assert "code_challenge=" in auth_req.auth_url
    assert "code_challenge_method=S256" in auth_req.auth_url
    assert auth_req.state
    assert auth_req.nonce
    assert auth_req.code_verifier

    # Package simulated browser session cookie
    session_cookie = OidcSessionCookie(
        state=auth_req.state,
        nonce=auth_req.nonce,
        code_verifier=auth_req.code_verifier,
        tenant_id=tenant_id,
    )

    reused_jti = f"jti_{UUIDv7.generate()}"
    id_token = create_signed_jwt(
        payload={
            "iss": issuer,
            "aud": client_id,
            "sub": "usr_replaysafe_1",
            "email": "auditor@replaysafe.com",
            "exp": now_ts + 1800,
            "nonce": auth_req.nonce,
            "jti": reused_jti,
            "groups": ["SecOps_Admins"],
        },
        kid=kid,
        key_secret=secret,
    )

    # 2. First callback exchange: SUCCESS
    principal_ctx = session_mgr.handle_callback(
        code="auth_code_sample_123",
        state=auth_req.state,
        code_verifier=auth_req.code_verifier,
        session_state=session_cookie,
        id_token_raw=id_token,
        as_of_time=now,
    )

    assert principal_ctx.tenant_id == tenant_id
    assert str(principal_ctx.principal_id) == "usr_replaysafe_1"
    assert "tenant_admin" in principal_ctx.roles

    # 3. Second presentation of identical token with duplicate JTI: FAIL CLOSED (TOKEN_REPLAY / 401)
    with pytest.raises(TokenReplayError) as exc_info:
        validator.validate_id_token(
            id_token_raw=id_token,
            expected_nonce=auth_req.nonce,
            config=config,
            as_of_time=now,
        )

    assert exc_info.value.code == "TOKEN_REPLAY"
    assert "replay rejected" in exc_info.value.message.lower()

    # 4. Anti-CSRF: State Mismatch Rejection
    with pytest.raises(AuthenticationError) as csrf_err:
        session_mgr.handle_callback(
            code="code_another",
            state="forged_state_value",  # Mismatched!
            code_verifier=auth_req.code_verifier,
            session_state=session_cookie,
            id_token_raw=id_token,
            as_of_time=now,
        )
    assert "state mismatch" in csrf_err.value.message.lower()
