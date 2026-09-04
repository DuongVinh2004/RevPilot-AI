"""
RevPilot AI — TC-P07-014: SAML Signature Verification & XML Signature Wrapping (XSW) Mitigation Test
Specification: docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §3
Conforms to NFR-SEC-001, INV-IAM-001, and INV-TEN-002.
"""

from datetime import timedelta
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.iam.saml import (
    SamlAcsValidator,
    SamlService,
    SamlTenantConfiguration,
    SamlSignatureInvalidError,
    SamlAssertionExpiredError,
    create_signed_saml_response,
)


def test_saml_signature_verification_and_xsw_mitigation():
    """
    TC-P07-014: SAML 2.0 assertions are cryptographically validated against trusted X.509 certs.
    XML Signature Wrapping (XSW) attacks, forged signatures, and expired assertions fail closed.
    Dual-certificate rotation verifies seamlessly on secondary cert.
    """
    validator = SamlAcsValidator()

    primary_cert = "-----BEGIN CERTIFICATE-----\nMIICvDCCAaQCCQD...PRIMARY...=\n-----END CERTIFICATE-----"
    secondary_cert = "-----BEGIN CERTIFICATE-----\nMIICvDCCAaQCCQD...SECONDARY...=\n-----END CERTIFICATE-----"

    tenant_id = TenantId.generate()
    issuer = "https://idp.saml-enterprise.com"
    acs_url = f"https://api.revpilot.ai/saml/{tenant_id}/acs"
    sp_entity_id = f"https://api.revpilot.ai/saml/{tenant_id}/sp"

    now = UtcDateTime.now()
    now_dt = now.value
    not_before = (now_dt - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    not_on_or_after = (now_dt + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # 1. Valid Assertion Signed by Primary Cert: PASS
    valid_b64 = create_signed_saml_response(
        name_id="usr_alice_saml",
        issuer=issuer,
        recipient=acs_url,
        audience=sp_entity_id,
        cert_pem=primary_cert,
        assertion_id="assert_valid_001",
        not_before_iso=not_before,
        not_on_or_after_iso=not_on_or_after,
        attributes={"Role": ["Financial_Analysts"]},
    )

    claims = validator.validate_saml_response(
        saml_response_b64=valid_b64,
        expected_recipient=acs_url,
        expected_audience=sp_entity_id,
        idp_cert_pem=primary_cert,
        as_of_time=now,
    )
    assert claims.name_id == "usr_alice_saml"
    assert claims.attributes["Role"] == ["Financial_Analysts"]

    # 2. Forged Signature: FAILS CLOSED (401 SAML_SIGNATURE_INVALID)
    forged_b64 = create_signed_saml_response(
        name_id="usr_attacker",
        issuer=issuer,
        recipient=acs_url,
        audience=sp_entity_id,
        cert_pem=primary_cert,
        assertion_id="assert_forged_002",
        not_before_iso=not_before,
        not_on_or_after_iso=not_on_or_after,
        simulate_forged_sig=True,
    )

    with pytest.raises(SamlSignatureInvalidError) as exc_info:
        validator.validate_saml_response(
            saml_response_b64=forged_b64,
            expected_recipient=acs_url,
            expected_audience=sp_entity_id,
            idp_cert_pem=primary_cert,
            as_of_time=now,
        )
    assert exc_info.value.code == "SAML_SIGNATURE_INVALID"
    assert "Invalid SAML digital signature" in exc_info.value.message

    # 3. XML Signature Wrapping (XSW) Attack: FAILS CLOSED (401 SAML_SIGNATURE_INVALID)
    xsw_b64 = create_signed_saml_response(
        name_id="usr_victim",
        issuer=issuer,
        recipient=acs_url,
        audience=sp_entity_id,
        cert_pem=primary_cert,
        assertion_id="assert_xsw_003",
        not_before_iso=not_before,
        not_on_or_after_iso=not_on_or_after,
        simulate_xsw_attack=True,
    )

    with pytest.raises(SamlSignatureInvalidError) as exc_info:
        validator.validate_saml_response(
            saml_response_b64=xsw_b64,
            expected_recipient=acs_url,
            expected_audience=sp_entity_id,
            idp_cert_pem=primary_cert,
            as_of_time=now,
        )
    assert exc_info.value.code == "SAML_SIGNATURE_INVALID"
    assert "Wrapping (XSW)" in exc_info.value.message

    # 4. Expired Assertion Timestamp: FAILS CLOSED (401 SAML_ASSERTION_EXPIRED)
    expired_not_on_or_after = (now_dt - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    expired_b64 = create_signed_saml_response(
        name_id="usr_alice_saml",
        issuer=issuer,
        recipient=acs_url,
        audience=sp_entity_id,
        cert_pem=primary_cert,
        assertion_id="assert_expired_004",
        not_before_iso=(now_dt - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        not_on_or_after_iso=expired_not_on_or_after,
    )

    with pytest.raises(SamlAssertionExpiredError) as exc_info:
        validator.validate_saml_response(
            saml_response_b64=expired_b64,
            expected_recipient=acs_url,
            expected_audience=sp_entity_id,
            idp_cert_pem=primary_cert,
            as_of_time=now,
        )
    assert exc_info.value.code == "SAML_ASSERTION_EXPIRED"
    assert "expired" in exc_info.value.message.lower()

    # 5. Dual Certificate Rotation: Verification on Secondary Certificate without Downtime
    saml_service = SamlService(validator=validator)
    saml_config = SamlTenantConfiguration(
        tenant_id=tenant_id,
        idp_entity_id=issuer,
        sp_entity_id=sp_entity_id,
        acs_url=acs_url,
        primary_cert_pem=primary_cert,
        secondary_cert_pem=secondary_cert,
        group_to_role={"Financial_Analysts": "analyst"},
    )
    saml_service.register_configuration(saml_config)

    # Token signed by newly rotated secondary certificate
    rotated_b64 = create_signed_saml_response(
        name_id="usr_bob_rotated",
        issuer=issuer,
        recipient=acs_url,
        audience=sp_entity_id,
        cert_pem=secondary_cert,  # Signed by secondary cert
        assertion_id="assert_rotated_005",
        not_before_iso=not_before,
        not_on_or_after_iso=not_on_or_after,
        attributes={"Role": ["Financial_Analysts"]},
    )

    principal_ctx = saml_service.process_acs_response(
        tenant_id=tenant_id,
        saml_response_b64=rotated_b64,
        as_of_time=now,
    )
    assert str(principal_ctx.principal_id) == "usr_bob_rotated"
    assert "analyst" in principal_ctx.roles
