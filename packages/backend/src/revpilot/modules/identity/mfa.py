"""
RevPilot AI — Multi-Factor Authentication (MFA) Engine
Specification: docs/14-iam/IAM-SPEC.md §8, ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md, CTL-AUTH-01
Conforms to RFC 6238 (TOTP), RFC 4226 (HOTP), W3C WebAuthn Level 2, and INV-IAM-001.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from revpilot.shared.errors import DomainError


class MfaError(DomainError):
    """Domain error during MFA processing."""

    def __init__(self, code: str, message: str, http_status: int = 400, details: dict[str, Any] | None = None) -> None:
        super().__init__(code=code, message=message, details=details)
        self.http_status = http_status


@dataclass(slots=True)
class WebAuthnCredential:
    credential_id: str
    public_key_pem: str
    sign_count: int
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class PrincipalMfaState:
    principal_id: str
    totp_secret: str | None = None
    totp_enabled: bool = False
    hashed_recovery_codes: set[str] = field(default_factory=set)
    webauthn_credentials: dict[str, WebAuthnCredential] = field(default_factory=dict)
    last_verified_step: int | None = None
    pending_challenges: dict[str, float] = field(default_factory=dict)


class TotpManager:
    """
    RFC 6238 Time-Based One-Time Password implementation.
    Standard: 30-second time step, 6-digit output, HMAC-SHA1 / HMAC-SHA256.
    """

    TIME_STEP: int = 30
    DIGITS: int = 6

    @classmethod
    def generate_secret(cls, length_bytes: int = 20) -> str:
        """Generate a random Base32 secret string."""
        raw_bytes = os.urandom(length_bytes)
        return base64.b32encode(raw_bytes).decode("ascii").rstrip("=")

    @classmethod
    def generate_code(cls, secret: str, for_time: float | None = None, algorithm: str = "sha1") -> str:
        """Compute the 6-digit TOTP code for a given timestamp."""
        ts = int(time.time() if for_time is None else for_time)
        counter = ts // cls.TIME_STEP
        return cls._generate_hotp(secret, counter, algorithm=algorithm)

    @classmethod
    def verify_code(
        cls,
        secret: str,
        code: str,
        *,
        for_time: float | None = None,
        drift_steps: int = 1,
        algorithm: str = "sha1",
        last_verified_step: int | None = None,
    ) -> tuple[bool, int | None]:
        """
        Verify TOTP code with time drift window tolerance.
        Enforces replay protection: rejects if step <= last_verified_step.
        Returns (is_valid, successful_step).
        """
        if not code or len(code.strip()) != cls.DIGITS:
            return False, None

        ts = int(time.time() if for_time is None else for_time)
        current_step = ts // cls.TIME_STEP

        for delta in range(-drift_steps, drift_steps + 1):
            step = current_step + delta
            if last_verified_step is not None and step <= last_verified_step:
                continue
            expected_code = cls._generate_hotp(secret, step, algorithm=algorithm)
            if hmac.compare_digest(expected_code, code.strip()):
                return True, step

        return False, None

    @classmethod
    def generate_provisioning_uri(
        cls,
        secret: str,
        account_name: str,
        issuer: str = "RevPilot AI",
        algorithm: str = "SHA1",
    ) -> str:
        """Generate otpauth:// URI for authenticator app configuration."""
        clean_account = quote(account_name)
        clean_issuer = quote(issuer)
        return (
            f"otpauth://totp/{clean_issuer}:{clean_account}?"
            f"secret={secret}&issuer={clean_issuer}&algorithm={algorithm}&digits={cls.DIGITS}&period={cls.TIME_STEP}"
        )

    @classmethod
    def _generate_hotp(cls, secret: str, counter: int, algorithm: str = "sha1") -> str:
        padding = (8 - (len(secret) % 8)) % 8
        padded_secret = secret + ("=" * padding)
        key = base64.b32decode(padded_secret.upper(), casefold=True)

        msg = struct.pack(">Q", counter)
        digestmod = hashlib.sha256 if algorithm.lower() == "sha256" else hashlib.sha1
        h = hmac.new(key, msg, digestmod).digest()

        offset = h[-1] & 0x0F
        code_int = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
        mod = 10**cls.DIGITS
        return str(code_int % mod).zfill(cls.DIGITS)


class RecoveryCodeManager:
    """Manages single-use recovery codes for MFA fallback."""

    CODE_COUNT: int = 8

    @classmethod
    def generate_recovery_codes(cls, count: int = CODE_COUNT) -> tuple[list[str], set[str]]:
        raw_codes = []
        hashed_codes = set()
        for _ in range(count):
            token = os.urandom(6).hex()
            raw = f"{token[:4]}-{token[4:8]}-{token[8:]}"
            raw_codes.append(raw)
            h = cls.hash_code(raw)
            hashed_codes.add(h)
        return raw_codes, hashed_codes

    @classmethod
    def hash_code(cls, raw_code: str) -> str:
        normalized = raw_code.strip().lower().replace("-", "")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def consume_recovery_code(cls, raw_code: str, hashed_codes: set[str]) -> bool:
        target_hash = cls.hash_code(raw_code)
        if target_hash in hashed_codes:
            hashed_codes.remove(target_hash)
            return True
        return False


class WebAuthnManager:
    """Manages WebAuthn / FIDO2 challenge generation and credential verification."""

    CHALLENGE_TIMEOUT_SECONDS: float = 300.0

    @classmethod
    def generate_challenge(cls) -> str:
        return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")

    @classmethod
    def verify_challenge(cls, challenge: str, pending_challenges: dict[str, float]) -> bool:
        now = time.time()
        expiry = pending_challenges.pop(challenge, None)
        if expiry is None:
            return False
        return now <= expiry


class MfaManager:
    """In-memory coordinator for tenant/principal MFA lifecycle."""

    def __init__(self) -> None:
        self._states: dict[str, PrincipalMfaState] = {}

    def get_or_create_state(self, principal_id: str) -> PrincipalMfaState:
        if principal_id not in self._states:
            self._states[principal_id] = PrincipalMfaState(principal_id=principal_id)
        return self._states[principal_id]

    def initiate_totp_setup(self, principal_id: str, account_name: str) -> dict[str, str]:
        state = self.get_or_create_state(principal_id)
        secret = TotpManager.generate_secret()
        state.totp_secret = secret
        uri = TotpManager.generate_provisioning_uri(secret, account_name)
        return {"secret": secret, "provisioning_uri": uri}

    def activate_totp(self, principal_id: str, code: str, for_time: float | None = None) -> list[str]:
        """Verify code against pending secret, enable TOTP, and issue recovery codes."""
        state = self.get_or_create_state(principal_id)
        if not state.totp_secret:
            raise MfaError(code="MFA_NOT_INITIALIZED", message="TOTP setup has not been initiated", http_status=400)

        valid, step = TotpManager.verify_code(state.totp_secret, code, for_time=for_time)
        if not valid:
            raise MfaError(code="INVALID_MFA_CODE", message="Invalid TOTP activation code", http_status=401)

        state.totp_enabled = True
        state.last_verified_step = step
        raw_codes, hashed_codes = RecoveryCodeManager.generate_recovery_codes()
        state.hashed_recovery_codes = hashed_codes
        return raw_codes

    def verify_totp(self, principal_id: str, code: str, for_time: float | None = None) -> bool:
        state = self._states.get(principal_id)
        if not state or not state.totp_enabled or not state.totp_secret:
            raise MfaError(code="MFA_NOT_ENROLLED", message="Principal does not have MFA enabled", http_status=400)

        valid, step = TotpManager.verify_code(
            state.totp_secret,
            code,
            for_time=for_time,
            last_verified_step=state.last_verified_step,
        )
        if not valid:
            raise MfaError(code="INVALID_MFA_CODE", message="Invalid or replayed TOTP verification code", http_status=401)

        state.last_verified_step = step
        return True

    def consume_recovery_code(self, principal_id: str, code: str) -> bool:
        state = self._states.get(principal_id)
        if not state or not state.totp_enabled:
            raise MfaError(code="MFA_NOT_ENROLLED", message="Principal does not have MFA enabled", http_status=400)

        consumed = RecoveryCodeManager.consume_recovery_code(code, state.hashed_recovery_codes)
        if not consumed:
            raise MfaError(code="INVALID_RECOVERY_CODE", message="Recovery code is invalid or already used", http_status=401)
        return True

    def is_mfa_enabled(self, principal_id: str) -> bool:
        state = self._states.get(principal_id)
        return bool(state and state.totp_enabled)
