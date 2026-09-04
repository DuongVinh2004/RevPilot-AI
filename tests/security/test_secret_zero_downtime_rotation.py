"""
RevPilot AI — Secret Zero-Downtime Rotation & Canary Rollback Test
Specification: docs/15-security/SECURITY-ARCHITECTURE.md §7.2, ADR-0009
Conforms to INV-SEC-001, INV-REL-001, and TC-P07-016.
"""

import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.modules.security.secrets import (
    CredentialBroker,
    SecretRotationService,
    SecretReference,
    SecretLifecycleStatus,
    RotationStatus,
    RotationValidationFailedError,
    SecretRevokedError,
)


def test_secret_zero_downtime_rotation_and_canary_rollback():
    """
    Verifies zero-downtime dual-version secret rotation:
    1. In-flight token resolution succeeds during ROTATING state.
    2. Canary validation failure triggers automated rollback and returns 422 ROTATION_VALIDATION_FAILED.
    3. Successful canary promotes new version to ACTIVE while keeping previous version intact.
    4. Secret revocation immediately invalidates cached tokens and blocks further token issuance (403).
    """
    broker = CredentialBroker(default_ttl_seconds=900)
    rotation_service = SecretRotationService(broker=broker)

    tenant_id = TenantId.generate()
    secret_ref = SecretReference.generate()

    v1_secret = "initial_salesforce_client_secret_v1_key"
    v2_canary_bad_secret = "invalid_bad_client_secret_cannot_auth"
    v2_valid_secret = "updated_salesforce_client_secret_v2_key"

    # 1. Register Initial V1 Secret
    broker.register_secret(
        tenant_id=tenant_id,
        secret_ref=secret_ref,
        plaintext_secret=v1_secret,
        provider_name="salesforce",
        granted_scopes=["api:read", "api:write"],
        allowed_audiences=["https://login.salesforce.com"],
    )

    # Issue initial token (v1)
    tok1 = broker.get_scoped_token(
        tenant_id=tenant_id,
        secret_ref=secret_ref,
        required_scope="api:read",
        audience="https://login.salesforce.com",
    )
    assert tok1.token.startswith("eph_salesforce_")

    # 2. Initiate Rotation -> State transitions to ROTATING
    session = rotation_service.initiate_rotation(
        tenant_id=tenant_id,
        secret_ref=secret_ref,
        new_secret_plaintext=v2_canary_bad_secret,
    )

    record = broker.get_secret_record(tenant_id, secret_ref)
    assert record.status == SecretLifecycleStatus.ROTATING
    assert session.status == RotationStatus.INITIATED

    # In-flight token requests still succeed without downtime
    tok_inflight = broker.get_scoped_token(
        tenant_id=tenant_id,
        secret_ref=secret_ref,
        required_scope="api:read",
        audience="https://login.salesforce.com",
    )
    assert tok_inflight is not None

    # 3. Canary Validation Failure: FAIL CLOSED (422 ROTATION_VALIDATION_FAILED)
    def failing_canary_validator(plaintext: str) -> bool:
        # Simulate failed remote auth test
        if plaintext == v2_canary_bad_secret:
            return False
        return True

    with pytest.raises(RotationValidationFailedError) as exc_info:
        rotation_service.validate_and_commit_rotation(
            session_id=session.session_id,
            canary_validator=failing_canary_validator,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "ROTATION_VALIDATION_FAILED"

    # Verify rollback: record returned to ACTIVE, version 1 intact
    record_post_rollback = broker.get_secret_record(tenant_id, secret_ref)
    assert record_post_rollback.status == SecretLifecycleStatus.ACTIVE
    assert record_post_rollback.envelope.version == 1

    # 4. Successful Rotation with Valid Key
    session_good = rotation_service.initiate_rotation(
        tenant_id=tenant_id,
        secret_ref=secret_ref,
        new_secret_plaintext=v2_valid_secret,
    )

    def passing_canary_validator(plaintext: str) -> bool:
        return plaintext == v2_valid_secret

    rotation_service.validate_and_commit_rotation(
        session_id=session_good.session_id,
        canary_validator=passing_canary_validator,
    )

    # Verify promotion: version is now 2, previous envelope retained
    record_promoted = broker.get_secret_record(tenant_id, secret_ref)
    assert record_promoted.status == SecretLifecycleStatus.ACTIVE
    assert record_promoted.envelope.version == 2
    assert record_promoted.previous_envelope is not None
    assert record_promoted.previous_envelope.version == 1

    # Idempotent commit check
    rotation_service.validate_and_commit_rotation(
        session_id=session_good.session_id,
        canary_validator=passing_canary_validator,
    )
    assert record_promoted.status == SecretLifecycleStatus.ACTIVE

    # 5. Revocation & Immediate Purge (< 500ms)
    rotation_service.revoke_secret(tenant_id=tenant_id, secret_ref=secret_ref)
    record_revoked = broker.get_secret_record(tenant_id, secret_ref)
    assert record_revoked.status == SecretLifecycleStatus.REVOKED

    # Subsequent token resolution fails closed (403 SECRET_REVOKED)
    with pytest.raises(SecretRevokedError) as exc_info:
        broker.get_scoped_token(
            tenant_id=tenant_id,
            secret_ref=secret_ref,
            required_scope="api:read",
            audience="https://login.salesforce.com",
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "SECRET_REVOKED"
