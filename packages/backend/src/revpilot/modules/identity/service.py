"""
RevPilot AI — Identity Application Service (Rail 3)
Orchestrates inbound token verification, session lifecycle, and tenant status checks.
Enforces INV-IAM-001, INV-TEN-002, INV-TEN-003, INV-SEC-001, and INV-REL-001.
"""

from __future__ import annotations

from revpilot.modules.identity.domain.models import (
    Principal,
    create_principal_from_verified_claims,
)
from revpilot.modules.identity.domain.token_policy import (
    SessionPolicy,
    TokenValidationPolicy,
    VerifiedSessionEvidence,
)
from revpilot.modules.identity.ports.authentication import AuthenticationPort
from revpilot.modules.tenancy.ports.policy import TenantContextPolicy
from revpilot.modules.tenancy.ports.repository import TenantQueryPort
from revpilot.shared.errors import (
    TenancyViolationError,
    ValidationError,
)
from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


class IdentityService:
    """
    Application service orchestrating authentication verification, session validation,
    and tenant binding checks. Fails closed on all policy uncertainty.
    """

    def __init__(
        self,
        auth_port: AuthenticationPort,
        *,
        token_policy: TokenValidationPolicy | None = None,
        session_policy: SessionPolicy | None = None,
        tenant_query_port: TenantQueryPort | None = None,
        tenancy_policy: type[TenantContextPolicy] | None = None,
    ) -> None:
        if not isinstance(auth_port, AuthenticationPort):
            raise TypeError(
                f"auth_port must implement AuthenticationPort, got {type(auth_port).__name__}"
            )
        self._auth_port = auth_port
        self._token_policy = token_policy or TokenValidationPolicy()
        self._session_policy = session_policy or SessionPolicy()
        self._tenant_query_port = tenant_query_port
        self._tenancy_policy = tenancy_policy

    @property
    def auth_port(self) -> AuthenticationPort:
        """The bound authentication port."""
        return self._auth_port

    @property
    def token_policy(self) -> TokenValidationPolicy:
        """The configured token validation policy."""
        return self._token_policy

    @property
    def session_policy(self) -> SessionPolicy:
        """The configured session policy."""
        return self._session_policy

    def authenticate_token(
        self,
        token: str,
        as_of: UtcDateTime | None = None,
    ) -> Principal:
        """
        Authenticate an incoming token through the full fail-closed verification pipeline:
        1. Validate token string structure.
        2. Cryptographically verify raw token at AuthenticationPort boundary -> VerifiedClaimsToken.
        3. Validate claims via TokenValidationPolicy (issuer, audience, skew, tenant).
        4. Retrieve and validate VerifiedSessionEvidence via SessionPolicy.
        5. Verify tenant active status via TenantQueryPort / TenantContextPolicy.
        6. Construct authenticated Principal aggregate via create_principal_from_verified_claims.
        """
        if not isinstance(token, str):
            raise ValidationError(f"token must be a str, got {type(token).__name__}")
        if not token.strip():
            raise ValidationError("token cannot be empty or whitespace-only")

        check_time = as_of or UtcDateTime.now()

        # Step 2: Authentication boundary verification
        verified_token = self._auth_port.verify_token(
            token.strip(),
            expected_issuer=self._token_policy.expected_issuer,
            expected_audience=self._token_policy.expected_audience,
            as_of=check_time,
        )

        # Step 3: Domain token policy validation
        self._token_policy.validate_verified_token(verified_token, as_of=check_time)

        # Step 4: Session lifecycle validation
        session_evidence = self._auth_port.get_session_evidence(
            verified_token.session_id,
            as_of=check_time,
        )
        self._session_policy.validate_session_evidence(
            session_evidence,
            as_of=check_time,
        )

        # Step 5: Tenant status verification
        tenant_id_str = verified_token.claims.tenant_id
        if not tenant_id_str:
            raise TenancyViolationError("Principal lacks required tenant association")

        try:
            tenant_id = TenantId(tenant_id_str)
        except (TypeError, ValueError) as e:
            raise TenancyViolationError(
                f"Invalid tenant_id in verified token: {tenant_id_str}"
            ) from e

        if self._tenant_query_port is not None:
            tenant = self._tenant_query_port.get_by_id(tenant_id)
            if tenant is None:
                raise TenancyViolationError(
                    f"Tenant '{tenant_id}' does not exist",
                    details={"tenant_id": str(tenant_id)},
                )
            if not tenant.is_active():
                raise TenancyViolationError(
                    f"Tenant '{tenant_id}' is in inactive or suspended status '{tenant.status.value}'",
                    details={"tenant_id": str(tenant_id), "status": tenant.status.value},
                )
            if self._tenancy_policy is not None:
                self._tenancy_policy.validate_context(tenant.to_context())

        # Step 6: Create trusted domain entity
        principal = create_principal_from_verified_claims(
            verified_token,
            as_of=check_time,
        )

        return principal

    def revoke_session(self, session_id: str) -> None:
        """Mark session as revoked across authentication subsystem."""
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValidationError("session_id must be a non-empty string")
        self._auth_port.revoke_session(session_id.strip())

    def get_session_evidence(
        self,
        session_id: str,
        as_of: UtcDateTime | None = None,
    ) -> VerifiedSessionEvidence:
        """Retrieve verified session evidence via underlying authentication port."""
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValidationError("session_id must be a non-empty string")
        return self._auth_port.get_session_evidence(session_id.strip(), as_of=as_of)
