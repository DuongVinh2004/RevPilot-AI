"""
RevPilot AI — Unit Tests for MFA Domain Module (RFC 6238 / WebAuthn)
Conforms to DEPENDENCY-RULES.md: no web framework dependencies.
"""

import time
import pytest

from revpilot.modules.identity.mfa import (
    MfaError,
    MfaManager,
    RecoveryCodeManager,
    TotpManager,
    WebAuthnManager,
)


def test_totp_generation_and_verification():
    secret = TotpManager.generate_secret()
    assert len(secret) >= 16

    now = time.time()
    code = TotpManager.generate_code(secret, for_time=now)
    assert len(code) == 6
    assert code.isdigit()

    # Exact time verification
    valid, step = TotpManager.verify_code(secret, code, for_time=now)
    assert valid is True
    assert step is not None

    # Drift +1 step (30s later)
    valid_drift, _ = TotpManager.verify_code(secret, code, for_time=now + 28, drift_steps=1)
    assert valid_drift is True

    # Bad code
    bad_code = "000000" if code != "000000" else "999999"
    invalid, _ = TotpManager.verify_code(secret, bad_code, for_time=now)
    assert invalid is False

    # Malformed code
    invalid_short, _ = TotpManager.verify_code(secret, "123", for_time=now)
    assert invalid_short is False


def test_totp_replay_protection():
    secret = TotpManager.generate_secret()
    now = time.time()
    code = TotpManager.generate_code(secret, for_time=now)

    valid, step = TotpManager.verify_code(secret, code, for_time=now)
    assert valid is True

    # Replaying same code in same step must fail
    replay_valid, _ = TotpManager.verify_code(
        secret,
        code,
        for_time=now,
        last_verified_step=step,
    )
    assert replay_valid is False


def test_totp_provisioning_uri():
    secret = TotpManager.generate_secret()
    uri = TotpManager.generate_provisioning_uri(secret, "analyst@revpilot.dev", issuer="RevPilot AI")
    assert uri.startswith("otpauth://totp/RevPilot%20AI:analyst%40revpilot.dev?")
    assert f"secret={secret}" in uri
    assert "digits=6" in uri


def test_recovery_code_manager():
    raw_codes, hashed_codes = RecoveryCodeManager.generate_recovery_codes(8)
    assert len(raw_codes) == 8
    assert len(hashed_codes) == 8

    test_code = raw_codes[0]
    # First consume succeeds
    assert RecoveryCodeManager.consume_recovery_code(test_code, hashed_codes) is True
    assert len(hashed_codes) == 7

    # Second consume of same code fails
    assert RecoveryCodeManager.consume_recovery_code(test_code, hashed_codes) is False

    # Invalid code fails
    assert RecoveryCodeManager.consume_recovery_code("fake-fake-fake", hashed_codes) is False


def test_webauthn_challenge():
    challenge = WebAuthnManager.generate_challenge()
    assert len(challenge) > 20

    pending = {challenge: time.time() + 60.0}
    assert WebAuthnManager.verify_challenge(challenge, pending) is True
    # Once consumed, challenge removed
    assert challenge not in pending
    assert WebAuthnManager.verify_challenge(challenge, pending) is False

    # Expired challenge
    expired_challenge = "expired_c"
    pending_expired = {expired_challenge: time.time() - 10.0}
    assert WebAuthnManager.verify_challenge(expired_challenge, pending_expired) is False


def test_mfa_manager_lifecycle():
    manager = MfaManager()
    principal_id = "usr_analyst_99"

    assert manager.is_mfa_enabled(principal_id) is False

    # 1. Setup
    setup_info = manager.initiate_totp_setup(principal_id, "usr_analyst_99@corp.io")
    secret = setup_info["secret"]

    # 2. Activate
    current_code = TotpManager.generate_code(secret)
    recovery_codes = manager.activate_totp(principal_id, current_code)
    assert len(recovery_codes) == 8
    assert manager.is_mfa_enabled(principal_id) is True

    # 3. Verify in step
    future_time = time.time() + 35.0
    future_code = TotpManager.generate_code(secret, for_time=future_time)
    assert manager.verify_totp(principal_id, future_code, for_time=future_time) is True

    # 4. Consume recovery code
    recovery_to_use = recovery_codes[0]
    assert manager.consume_recovery_code(principal_id, recovery_to_use) is True

    # Reusing same recovery code fails
    with pytest.raises(MfaError) as exc:
        manager.consume_recovery_code(principal_id, recovery_to_use)
    assert exc.value.code == "INVALID_RECOVERY_CODE"
