"""
RevPilot AI — OIDC Token Signature, Expiry, and Replay Validator
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §2.2
Conforms to INV-IAM-001, INV-IAM-002, and NFR-SEC-001.
"""

from __future__ import annotations
from datetime import datetime, timezone
import json
from typing import Any, TYPE_CHECKING

from revpilot.shared.errors import DomainError
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.identity.domain.models import AuthTokenClaims
from revpilot.modules.iam.oidc.jwks import JwksClient, _b64url_decode

if TYPE_CHECKING:
    from revpilot.modules.iam.oidc.adapter import OidcTenantConfiguration


class OidcValidationError(DomainError):
    """Base exception for all OIDC validation failures."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code=code, message=message, details=details, retryable=False)


class TokenExpiredError(OidcValidationError):
    """Token expiration evaluated past allowed clock skew (401)."""

    def __init__(self, message: str = "Token has expired", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="TOKEN_EXPIRED", message=message, details=details)


class InvalidSignatureError(OidcValidationError):
    """Cryptographic signature invalid or insecure algorithm attempted (401)."""

    def __init__(self, message: str = "Invalid token signature", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="INVALID_SIGNATURE", message=message, details=details)


class IssuerMismatchError(OidcValidationError):
    """Issuer or audience claim does not match tenant configuration (401)."""

    def __init__(self, message: str = "Invalid token issuer or audience", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="ISSUER_MISMATCH", message=message, details=details)


class TokenReplayError(OidcValidationError):
    """Duplicate JTI detected within token lifetime (401)."""

    def __init__(self, message: str = "Token replay rejected", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="TOKEN_REPLAY", message=message, details=details)


class OidcValidator:
    """
    Authoritative OIDC ID Token validator enforcing signature verification,
    clock skew tolerance (60s), issuer/audience binding, and JTI anti-replay protection.
    """

    def __init__(
        self,
        jwks_client: JwksClient | None = None,
        anti_replay_store: dict[str, float] | None = None,
    ) -> None:
        self.jwks_client = jwks_client or JwksClient()
        self._anti_replay_store: dict[str, float] = (
            anti_replay_store if anti_replay_store is not None else {}
        )

    def validate_id_token(
        self,
        id_token_raw: str,
        expected_nonce: str | None,
        config: OidcTenantConfiguration,
        as_of_time: UtcDateTime | None = None,
    ) -> AuthTokenClaims:
        """
        Execute strict cryptographic and claim validation on inbound OIDC id_token.
        Fails closed on any discrepancy (INV-IAM-001).
        """
        # 1. Parse JWT Structure
        if not isinstance(id_token_raw, str) or id_token_raw.count(".") != 2:
            raise InvalidSignatureError("Malformed token structure: expected header.payload.signature")

        parts = id_token_raw.split(".")
        header_b64, payload_b64, sig_b64 = parts

        try:
            header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
            payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        except Exception as err:
            raise InvalidSignatureError(f"Malformed token JSON: {err}") from err

        # 2. Insecure Algorithm 'none' Prohibited
        alg = str(header.get("alg", "")).upper()
        if alg == "NONE" or not alg:
            raise InvalidSignatureError("Insecure algorithm 'none' is strictly prohibited")

        # 3. Signature & Key Verification via JWKS
        kid = header.get("kid")
        if not kid:
            raise InvalidSignatureError("Missing 'kid' header parameter in JWT")

        key = self.jwks_client.get_key(kid)
        if key is None:
            raise InvalidSignatureError(f"Unknown JWKS key ID: '{kid}' after rotation")

        if not self.jwks_client.verify_signature(header_b64, payload_b64, sig_b64, key):
            raise InvalidSignatureError("Invalid cryptographic token signature")

        # 4. Issuer Verification
        token_iss = payload.get("iss")
        if token_iss != config.issuer_url:
            raise IssuerMismatchError(
                f"Issuer mismatch: expected '{config.issuer_url}', got '{token_iss}'",
                details={"expected": config.issuer_url, "actual": token_iss},
            )

        # 5. Audience Verification
        token_aud = payload.get("aud")
        aud_list = token_aud if isinstance(token_aud, list) else [token_aud]
        if config.client_id not in aud_list:
            raise IssuerMismatchError(
                f"Audience mismatch: expected '{config.client_id}', got '{token_aud}'",
                details={"expected": config.client_id, "actual": token_aud},
            )

        # 6. Timestamp & Clock Skew Evaluation (Max 60s)
        now_dt = as_of_time or UtcDateTime.now()
        now_ts = now_dt.value.timestamp()
        allowed_skew = config.allowed_clock_skew_seconds

        exp = payload.get("exp")
        if exp is not None:
            # Token is expired only if now exceeds (exp + allowed_skew)
            if now_ts >= (float(exp) + allowed_skew):
                raise TokenExpiredError(
                    f"Token has expired: exp={exp}, now={now_ts}, skew={allowed_skew}s",
                    details={"exp": exp, "now": now_ts, "allowed_skew": allowed_skew},
                )

        nbf = payload.get("nbf")
        if nbf is not None:
            if now_ts < (float(nbf) - allowed_skew):
                raise TokenExpiredError(
                    f"Token is not yet valid: nbf={nbf}, now={now_ts}, skew={allowed_skew}s",
                    details={"nbf": nbf, "now": now_ts, "allowed_skew": allowed_skew},
                )

        # 7. Nonce Binding
        if expected_nonce is not None:
            token_nonce = payload.get("nonce")
            if token_nonce != expected_nonce:
                raise InvalidSignatureError(
                    f"Nonce mismatch: expected '{expected_nonce}', got '{token_nonce}'",
                    details={"expected": expected_nonce, "actual": token_nonce},
                )

        # 8. JTI Replay Prevention (INV-IAM-002)
        jti = payload.get("jti")
        if jti:
            if jti in self._anti_replay_store:
                raise TokenReplayError(
                    f"Token replay rejected: JTI '{jti}' was already presented",
                    details={"jti": jti},
                )
            # Store in replay cache
            self._anti_replay_store[jti] = float(exp) if exp else (now_ts + 3600.0)

        # 9. Role Mapping from IdP Claims
        groups = payload.get("groups", []) or payload.get("roles", [])
        if isinstance(groups, str):
            groups = [groups]
        mapped_roles = config.claim_mapping.map_groups(groups)

        sub = str(payload.get("sub", ""))
        if not (sub.startswith("usr_") or sub.startswith("svc_")):
            sub = f"usr_{sub}"
        iat = payload.get("iat", now_ts)
        exp_val = exp if exp is not None else (now_ts + 3600.0)

        exp_dt = datetime.fromtimestamp(float(exp_val), tz=timezone.utc)
        iat_dt = datetime.fromtimestamp(float(iat), tz=timezone.utc)

        return AuthTokenClaims(
            sub=sub,
            iss=token_iss,
            aud=config.client_id,
            exp=UtcDateTime(exp_dt),
            iat=UtcDateTime(iat_dt),
            tenant_id=str(config.tenant_id),
            roles=mapped_roles,
            permissions=set(),
            email=payload.get("email"),
            jti=jti,
        )
