"""
RevPilot AI — SAML 2.0 Enterprise Federation Service
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §3
Conforms to INV-IAM-001, INV-TEN-002, and NFR-SEC-001.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import PrincipalContext
from revpilot.shared.errors import AuthenticationError
from revpilot.modules.iam.saml.validator import (
    SamlAcsValidator,
    SamlSignatureInvalidError,
    SamlAssertionClaims,
)


class SamlTenantConfiguration(BaseModel):
    """
    Tenant-scoped SAML 2.0 federation parameters.
    Supports dual active certificates for zero-downtime rotation.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    tenant_id: TenantId
    idp_entity_id: str
    sp_entity_id: str
    acs_url: str
    primary_cert_pem: str
    secondary_cert_pem: str | None = None
    group_to_role: dict[str, str] = Field(
        default_factory=lambda: {
            "Enterprise_Admins": "tenant_admin",
            "Financial_Analysts": "analyst",
            "Staff": "operator",
        }
    )
    default_role: str = "operator"


class SamlService:
    """
    Enterprise SAML service orchestrating ACS handling, dual certificate rotation,
    and server-derived principal session establishment.
    """

    def __init__(
        self,
        tenant_service: Any = None,
        validator: SamlAcsValidator | None = None,
        configurations: dict[str, SamlTenantConfiguration] | None = None,
    ) -> None:
        self.tenant_service = tenant_service
        self.validator = validator or SamlAcsValidator()
        self._configs: dict[str, SamlTenantConfiguration] = configurations or {}

    def register_configuration(self, config: SamlTenantConfiguration) -> None:
        """Register tenant SAML configuration."""
        self._configs[str(config.tenant_id)] = config

    def get_configuration(self, tenant_id: TenantId) -> SamlTenantConfiguration:
        """Retrieve tenant SAML configuration or raise AuthenticationError."""
        cfg = self._configs.get(str(tenant_id))
        if cfg is None:
            raise AuthenticationError(
                f"No SAML federation configured for tenant '{tenant_id}'",
                details={"tenant_id": str(tenant_id)},
            )
        return cfg

    def process_acs_response(
        self,
        tenant_id: TenantId,
        saml_response_b64: str,
        as_of_time: UtcDateTime | None = None,
    ) -> PrincipalContext:
        """
        Process inbound SAMLResponse at the ACS endpoint.
        Attempts primary certificate first; falls back to secondary cert for zero-downtime rotation (TC-P07-014).
        """
        config = self.get_configuration(tenant_id)
        claims: SamlAssertionClaims | None = None

        # 1. Validate against primary certificate
        try:
            claims = self.validator.validate_saml_response(
                saml_response_b64=saml_response_b64,
                expected_recipient=config.acs_url,
                expected_audience=config.sp_entity_id,
                idp_cert_pem=config.primary_cert_pem,
                as_of_time=as_of_time,
            )
        except SamlSignatureInvalidError as primary_err:
            # 2. Dual-Certificate Rotation fallback
            if config.secondary_cert_pem is not None:
                try:
                    claims = self.validator.validate_saml_response(
                        saml_response_b64=saml_response_b64,
                        expected_recipient=config.acs_url,
                        expected_audience=config.sp_entity_id,
                        idp_cert_pem=config.secondary_cert_pem,
                        as_of_time=as_of_time,
                    )
                except SamlSignatureInvalidError:
                    raise primary_err
            else:
                raise primary_err

        # 3. Check Tenant Status (Fail-closed on inactive tenant)
        if self.tenant_service is not None:
            self.tenant_service.check_ingress_allowed(tenant_id)

        # 4. Map Attributes to Roles
        raw_roles = claims.attributes.get("Role", []) or claims.attributes.get("groups", [])
        mapped_roles: set[str] = set()
        for r in raw_roles:
            if r in config.group_to_role:
                mapped_roles.add(config.group_to_role[r])
        if not mapped_roles and config.default_role:
            mapped_roles.add(config.default_role)

        # 5. Normalize NameID
        norm_name_id = claims.name_id if claims.name_id.startswith("usr_") else f"usr_{claims.name_id}"

        return PrincipalContext(
            principal_id=PrincipalId(norm_name_id),
            tenant_id=tenant_id,
            roles=frozenset(mapped_roles),
            permissions=frozenset(),
            is_system=False,
        )
