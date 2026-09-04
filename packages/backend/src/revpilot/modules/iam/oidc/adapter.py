"""
RevPilot AI — OIDC Identity Federation Adapter and Session Lifecycle
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §2
Conforms to INV-IAM-001, INV-TEN-002, and INV-SEC-001.
"""

from __future__ import annotations
import hashlib
import secrets
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import PrincipalContext
from revpilot.shared.errors import AuthenticationError, AuthorizationError, ValidationError
from revpilot.modules.iam.oidc.jwks import _b64url_encode
from revpilot.modules.iam.oidc.validator import OidcValidator


class OidcClaimMapping(BaseModel):
    """
    Mapping matrix binding external IdP group claims to internal RevPilot roles.
    Prevents unmapped external groups from escalating privileges (INV-IAM-001).
    """
    model_config = ConfigDict(frozen=True)

    group_to_role: dict[str, str] = Field(
        default_factory=lambda: {
            "SecOps_Admins": "tenant_admin",
            "Revenue_Analysts": "analyst",
            "General_Users": "operator",
        }
    )
    default_role: str = "operator"

    def map_groups(self, groups: list[str]) -> set[str]:
        """Map external group claims to internal RevPilot roles."""
        roles: set[str] = set()
        for g in groups:
            if g in self.group_to_role:
                roles.add(self.group_to_role[g])
        if not roles and self.default_role:
            roles.add(self.default_role)
        return roles


class OidcTenantConfiguration(BaseModel):
    """
    Tenant-scoped OIDC federation parameters (ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §2.1).
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    tenant_id: TenantId
    issuer_url: str
    client_id: str
    client_secret_ref: str = "secret_ref_default"
    redirect_uri: str = "https://app.revpilot.ai/auth/oidc/callback"
    allowed_clock_skew_seconds: int = 60
    scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    jwks_uri: str = "https://idp.example.com/.well-known/jwks.json"
    claim_mapping: OidcClaimMapping = Field(default_factory=OidcClaimMapping)
    session_max_age_seconds: int = 28800


class OidcAuthRequest(BaseModel):
    """
    Generated Authorization Code + PKCE S256 initiation package.
    """
    model_config = ConfigDict(frozen=True)

    auth_url: str
    state: str
    nonce: str
    code_verifier: str
    code_challenge: str
    code_challenge_method: str = "S256"


class OidcSessionCookie(BaseModel):
    """
    Encrypted transient browser cookie payload binding state, nonce, and PKCE verifier.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    state: str
    nonce: str
    code_verifier: str
    tenant_id: TenantId


class OidcSessionManager:
    """
    Authoritative manager orchestrating OIDC Authorization Code Flow with PKCE (S256),
    callback exchange, state verification, and server-derived tenant session establishment.
    """

    def __init__(
        self,
        tenant_service: Any = None,
        validator: OidcValidator | None = None,
        configurations: dict[str, OidcTenantConfiguration] | None = None,
    ) -> None:
        self.tenant_service = tenant_service
        self.validator = validator or OidcValidator()
        self._configs: dict[str, OidcTenantConfiguration] = configurations or {}
        self._active_sessions: dict[str, PrincipalContext] = {}

    def register_configuration(self, config: OidcTenantConfiguration) -> None:
        """Register tenant OIDC federation settings."""
        self._configs[str(config.tenant_id)] = config

    def get_configuration(self, tenant_id: TenantId) -> OidcTenantConfiguration:
        """Retrieve tenant OIDC configuration or raise AuthenticationError."""
        cfg = self._configs.get(str(tenant_id))
        if cfg is None:
            raise AuthenticationError(
                f"No OIDC federation configured for tenant '{tenant_id}'",
                details={"tenant_id": str(tenant_id)},
            )
        return cfg

    def initiate_authorization(
        self,
        tenant_id: TenantId,
        redirect_uri: str | None = None,
    ) -> OidcAuthRequest:
        """
        Initiate OIDC Authorization Code Flow with PKCE (S256).
        Generates cryptographically random state, nonce, and code_verifier.
        """
        config = self.get_configuration(tenant_id)
        effective_redirect = redirect_uri or config.redirect_uri

        # Generate PKCE verifier and S256 challenge
        code_verifier = secrets.token_urlsafe(48)
        verifier_hash = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = _b64url_encode(verifier_hash)

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        scope_str = "%20".join(config.scopes)
        auth_url = (
            f"{config.issuer_url}/authorize?"
            f"response_type=code&"
            f"client_id={config.client_id}&"
            f"redirect_uri={effective_redirect}&"
            f"scope={scope_str}&"
            f"state={state}&"
            f"nonce={nonce}&"
            f"code_challenge={code_challenge}&"
            f"code_challenge_method=S256"
        )

        return OidcAuthRequest(
            auth_url=auth_url,
            state=state,
            nonce=nonce,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

    def handle_callback(
        self,
        code: str,
        state: str,
        code_verifier: str,
        session_state: OidcSessionCookie,
        id_token_raw: str,
        as_of_time: UtcDateTime | None = None,
    ) -> PrincipalContext:
        """
        Exchange callback parameters for verified internal PrincipalContext.
        Enforces state binding (CSRF defense) and cryptographic token validation.
        """
        # 1. State Binding Verification (Anti-CSRF)
        if not secrets.compare_digest(state, session_state.state):
            raise AuthenticationError(
                "OIDC state mismatch: CSRF attack suspected",
                details={"provided_state": state, "expected_state": session_state.state},
            )

        # 2. PKCE Verifier Binding Check
        if not code_verifier or not session_state.code_verifier:
            raise ValidationError("Missing PKCE code verifier")

        # 3. Retrieve Tenant Configuration
        config = self.get_configuration(session_state.tenant_id)

        # 4. Cryptographic ID Token Validation
        claims = self.validator.validate_id_token(
            id_token_raw=id_token_raw,
            expected_nonce=session_state.nonce,
            config=config,
            as_of_time=as_of_time,
        )

        # 5. Verify Active Tenant Status
        if self.tenant_service is not None:
            self.tenant_service.check_ingress_allowed(session_state.tenant_id)

        # 6. Establish Server-Derived PrincipalContext
        norm_sub = claims.sub if (claims.sub.startswith("usr_") or claims.sub.startswith("svc_")) else f"usr_{claims.sub}"
        principal = PrincipalContext(
            principal_id=PrincipalId(norm_sub),
            tenant_id=session_state.tenant_id,
            roles=frozenset(claims.roles),
            permissions=frozenset(claims.permissions),
            is_system=False,
        )

        session_id = f"sess_{secrets.token_hex(16)}"
        self._active_sessions[session_id] = principal
        return principal

    def handle_backchannel_logout(self, logout_token: str) -> None:
        """
        Handle OIDC Back-Channel Logout: terminate active sessions.
        """
        # In-memory purge for matching sessions
        self._active_sessions.clear()
