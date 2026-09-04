"""
RevPilot AI — OIDC Dynamic JWKS Client and Key Rotation
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §2.2
Conforms to NFR-SEC-001 and INV-IAM-001.
"""

from __future__ import annotations
import base64
import hashlib
import hmac
import json
from typing import Any, Callable


def _b64url_encode(data: bytes) -> str:
    """Encode bytes to Base64URL without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(encoded: str) -> bytes:
    """Decode Base64URL string with auto-padding."""
    rem = len(encoded) % 4
    if rem > 0:
        encoded += "=" * (4 - rem)
    return base64.urlsafe_b64decode(encoded.encode("utf-8"))


def create_signed_jwt(
    payload: dict[str, Any],
    kid: str,
    key_secret: str,
    alg: str = "RS256",
) -> str:
    """
    Utility creating standard 3-part signed JWT for OIDC testing and IdP simulation.
    """
    header = {"alg": alg, "typ": "JWT", "kid": kid}
    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    header_b64 = _b64url_encode(header_json)
    payload_b64 = _b64url_encode(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    if alg.lower() == "none":
        sig_b64 = ""
    else:
        raw_sig = hmac.new(key_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(raw_sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


class JwksClient:
    """
    OIDC JSON Web Key Set (JWKS) client with caching and dynamic key rotation.
    If a token presents an unknown kid, triggers dynamic refresh from the IdP (TC-P07-011).
    """

    def __init__(
        self,
        jwks_uri: str = "https://idp.example.com/.well-known/jwks.json",
        remote_provider: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:
        self.jwks_uri = jwks_uri
        self._remote_provider = remote_provider
        self._cache: dict[str, dict[str, Any]] = {}
        self.fetch_count: int = 0

    def register_key(
        self,
        kid: str,
        secret: str,
        alg: str = "RS256",
        kty: str = "RSA",
    ) -> None:
        """Register a key directly into cache (for fixtures and local mock)."""
        self._cache[kid] = {
            "kid": kid,
            "secret": secret,
            "alg": alg,
            "kty": kty,
            "use": "sig",
        }

    def set_remote_provider(self, provider: Callable[[], list[dict[str, Any]]]) -> None:
        """Assign dynamic remote provider function."""
        self._remote_provider = provider

    def refresh_keys(self) -> None:
        """Fetch updated key set from remote provider."""
        self.fetch_count += 1
        if self._remote_provider is not None:
            remote_keys = self._remote_provider()
            for k in remote_keys:
                kid = k.get("kid")
                if kid:
                    self._cache[kid] = k

    def get_key(self, kid: str) -> dict[str, Any] | None:
        """
        Retrieve key by kid.
        If unknown, triggers dynamic key rotation refresh once (TC-P07-011).
        """
        if kid in self._cache:
            return self._cache[kid]

        # Dynamic Key Rotation Trigger
        self.refresh_keys()
        return self._cache.get(kid)

    def verify_signature(
        self,
        header_b64: str,
        payload_b64: str,
        sig_b64: str,
        key: dict[str, Any],
    ) -> bool:
        """Verify token signature against cached key secret."""
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        secret = key.get("secret", "")
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        expected_sig_b64 = _b64url_encode(expected_sig)
        return hmac.compare_digest(sig_b64, expected_sig_b64)
